# Ánh xạ đặc trưng và ngưỡng rủi ro

Tài liệu này giải thích hai quyết định trong Bước 3: `bp → HighBP` và cách tách ngưỡng nhị phân khỏi các mức Low/Medium/High.

## 1. `bp → HighBP`

- Mô hình huấn luyện trên BRFSS 2015, trong đó `HighBP` là câu trả lời "đã từng được nhân viên y tế cho biết bị huyết áp cao" (0/1). Đây là **chẩn đoán tự khai báo**, không phải số đo.
- API nhận huyết áp tâm thu `bp` (mmHg). Khi người dùng không cung cấp `high_bp`, hệ thống suy ra `HighBP = 1` nếu `bp >= 130`.
- Mốc 130 mmHg theo phân loại ACC/AHA (tăng huyết áp giai đoạn 1). Hằng số nằm ở `HIGH_BP_SYSTOLIC_CUTOFF` trong `models/risk_model.py`.
- Nếu người dùng gửi `high_bp` (hoặc `HighBP`) thì giá trị đó được ưu tiên, không suy ra từ `bp`.

**Hạn chế cần nêu trong báo cáo:**
- Một lần đo 130 mmHg không bằng chẩn đoán tăng huyết áp; ánh xạ này là xấp xỉ.
- Không có huyết áp tâm trương nên không áp dụng được điều kiện `>= 80` của ACC/AHA.
- `bp` còn được dùng ở nơi khác với mốc riêng (cảnh báo an toàn 160/180 trong `tools/safety.py`, giải thích 140 trong `agents/explainer.py`). Các mốc này phục vụ cảnh báo lâm sàng, không liên quan đến đặc trưng đưa vào mô hình.

## 2. Ngưỡng nhị phân và các mức Low/Medium/High

Trước đây `classify_risk` dùng mốc cố định 0.4/0.7, còn ngưỡng 0.26 chọn trên validation không được dùng khi dự đoán. Tỉ lệ mắc trong dữ liệu khoảng 14% nên xác suất hiệu chỉnh hiếm khi vượt 0.4, và một ca xác suất 0.30 vừa bị cờ "dương tính" theo ngưỡng 0.26 vừa bị gán "Low".

Hiện nay hai khái niệm tách riêng nhưng nhất quán, cả hai mốc đều chọn trên **validation**:

| Khái niệm | Quy tắc | Nguồn |
|---|---|---|
| Cờ nhị phân (dương tính) | `prob >= selected_threshold` | Ngưỡng cho F1 cao nhất trên validation |
| Low | `prob < low_max` (= `selected_threshold`) | như trên |
| Medium | `low_max <= prob < high_min` | |
| High | `prob >= high_min` | Xác suất thấp nhất trên validation mà precision của các ca được cờ đạt ít nhất 0.5 |

Hệ quả: mọi ca bị cờ dương tính đều từ Medium trở lên, không bao giờ là Low. Các mốc lưu trong `risk_bands` của artifact và `metrics.json`. Artifact cũ không có `risk_bands` thì dùng lại mốc 0.4/0.7.

## 3. Lưu ý khi diễn giải

- Các mức Low/Medium/High là phân tầng để ưu tiên theo dõi, không phải chẩn đoán.
- `high_min` chọn theo precision nên phụ thuộc tỉ lệ mắc của tập dữ liệu; cần chọn lại khi áp dụng sang quần thể khác.
