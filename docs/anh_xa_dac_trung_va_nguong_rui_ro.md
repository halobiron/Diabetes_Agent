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
| Cờ nhị phân (dương tính) | `prob >= selected_threshold` | Precision cao nhất với recall validation ít nhất 80% (mục tiêu thử nghiệm) |
| Low | `prob < low_max` (= `selected_threshold`) | như trên |
| Medium | `low_max <= prob < high_min` | |
| High | `prob >= high_min` | Xác suất thấp nhất trên validation mà precision của các ca được cờ đạt ít nhất 0.5 |

Hệ quả: mọi ca bị cờ dương tính đều từ Medium trở lên, không bao giờ là Low. Các mốc lưu trong `risk_bands` của artifact và `metrics.json`. Artifact cũ không có `risk_bands` thì dùng lại mốc 0.4/0.7.

## 3. Lưu ý khi diễn giải

- Các mức Low/Medium/High là phân tầng để ưu tiên theo dõi, không phải chẩn đoán.
- `high_min` chọn theo precision nên phụ thuộc tỉ lệ mắc của tập dữ liệu; cần chọn lại khi áp dụng sang quần thể khác.

## 4. Tối ưu ngày 26/11/2026

Artifact mặc định hiện phối hợp 75% xác suất MLP cũ với 25% LightGBM mới.
Sáu cấu hình LightGBM và 18 tổ hợp được so sánh trên validation; không dùng test
để chọn mô hình hoặc ngưỡng. LightGBM được huấn luyện/hiệu chuẩn trong phần train
cũ (121.766 dòng fit, 30.442 dòng calibration). MLP cũ giữ nguyên trọng số.

- Ngưỡng nhị phân/Low: `0.14146671639492997`; ngưỡng High: `0.397420176322333`.
- Test cũ: recall 60,277% → 79,997%; FN 2.808 → 1.414; FP 6.980 → 12.956.
- Precision 37,906% → 30,385%; accuracy 80,708% → 71,677%; F1 0,46543 → 0,44042.
- AUC 0,82581 → 0,82663; AP 0,41441 → 0,41893. Cải thiện xếp hạng nhỏ.
- Nếu chỉ hạ ngưỡng MLP cũ: FN 1.420, FP 12.991; ensemble mới giảm thêm 6 FN và 35 FP.

Phần lớn giảm bỏ sót đến từ đổi điểm vận hành, kèm tăng báo động nhầm. Mục tiêu
80% chưa được thẩm định lâm sàng; Low không loại trừ bệnh. Đây là so sánh ghép
cặp trên test đã được xem trong báo cáo cũ, chưa phải external validation mới.
Xác suất/ngưỡng trong artifact giữ đủ độ chính xác, chỉ làm tròn khi trình bày.

Tái lập: `.\.venv\Scripts\python.exe scripts/optimize_screening.py` xuất kết quả vào
`artifacts/screening_optimization/`; thêm `--promote` để thay artifact mặc định
sau khi qua điều kiện cải thiện trên validation. Bản cũ được giữ trong thư mục
`baseline/`, kết quả và quyết định trước khi chấm test ở `comparison.json` và
`frozen_selection.json`. Lệnh huấn luyện đầy đủ cũng dùng chính sách recall này
qua `--minimum-recall` (mặc định 0,8).

## 5. Điều kiện chấp nhận bổ sung: precision ít nhất 50%

Yêu cầu hiện tại là đồng thời recall >=80% và precision >=50% trên validation.
Rà soát toàn bộ đường precision–recall của 25 cấu hình đã lưu cho thấy **0/25 đạt**.
Giữ recall >=80% thì precision tốt nhất 30,4025%; giữ precision >=50% thì recall
tốt nhất 31,7867%. Đây là số đo validation, không phải số đo trên test mới.
Kết quả theo từng ứng viên ở `artifacts/screening_optimization/precision_recall_feasibility.json`.

Hai lệnh huấn luyện/tối ưu mặc định thêm `--minimum-precision 0.5` bên cạnh
`--minimum-recall 0.8`. Nếu không có ứng viên đạt cả hai, chúng dừng trước chấm test
và trước thay artifact; không tự hạ recall. Artifact hiện đang dùng của lần tối ưu
trước vẫn chưa đáp ứng yêu cầu precision mới. Lần rà soát này không đổi artifact
hoặc đổi ngưỡng để đánh đổi recall lấy precision.

## 6. Nhánh triệu chứng và đánh đổi được chấp nhận

Người dùng đã chấp thuận mở rộng đầu vào và dữ liệu. Nguồn mới là [UCI Early Stage
Diabetes Risk Prediction](https://archive.ics.uci.edu/dataset/529/early+stage+diabetes+risk+),
DOI `10.24432/C5VG8H`, CC BY 4.0. Đây là 520 dòng từ một bệnh viện ở Bangladesh;
sau loại hồ sơ trùng còn **251 hồ sơ khác nhau**. Chia cố định seed 42 thành
150 train / 50 validation / 51 holdout, không trùng đặc trưng giữa các tập, không
cân bằng lại lớp trong các tập đánh giá.

Nhánh mới dùng tuổi, giới tính và 14 triệu chứng/trạng thái được hỏi trực tiếp,
không ghép nhãn hoặc điểm số với BRFSS. `artifacts/symptom_model.joblib` là Random
Forest 400 cây, `min_samples_leaf=2`, hiệu chuẩn sigmoid CV 3 fold trong train.
Ngưỡng 0,5 được chọn theo yêu cầu đánh đổi của người dùng sau khi đã xem holdout;
vì vậy bảng sau là **so sánh hồi cứu**, không gọi là test độc lập mới:

| Ngưỡng RF | Precision | Recall | Accuracy | TP / FN / FP / TN |
|---|---:|---:|---:|---|
| 0,75734, bản đầu | 100% | 71,43% | 80,39% | 25 / 10 / 0 / 16 |
| **0,5, đang dùng** | **88,89%** | **91,43%** | **86,27%** | **32 / 3 / 4 / 12** |

Khoảng Wilson 95% của cấu hình đang dùng: precision 74,7–95,6%, recall 77,6–97,0%.
Tỉ lệ nhãn dương của holdout là 35/51 (68,6%): baseline đoán tất cả dương cũng
đạt precision 68,6%, recall 100% nhưng specificity 0%; RF đạt specificity 75%.
Không diễn giải điểm cao trên bộ nhỏ, giàu ca dương này thành hiệu quả sàng lọc
trên người Việt hoặc thành cải thiện AUC của BRFSS.

Đánh giá bổ sung ở `artifacts/symptom_nested_cv/evaluation.json` dùng 5 outer fold,
chọn mô hình/ngưỡng bằng 3 inner fold trong từng phần train. Toàn quy trình đạt
precision 88,24%, recall 95,38%, accuracy 88,05% trên 251 dự đoán outer-fold;
không phải phép đo riêng của artifact RF ngưỡng 0,5. Đây vẫn là đánh giá nội bộ,
chưa có xác nhận ngoài/quần thể Việt Nam. Lần RF ngưỡng cao không đạt recall
được giữ tại `artifacts/symptom_training/metrics.json`.

Tái lập artifact đang dùng:
`python scripts/train_symptom_model.py --standard-threshold`.
Tái lập kiểm tra lồng nhau: `python scripts/validate_symptom_model.py` (xuất vào
thư mục riêng, không thay mô hình đang dùng).

API `/v1/predict` nhận `screening_mode="symptoms"` và object `symptoms` đủ 14
boolean. Thiếu/chưa rõ bất kỳ mục nào, thiếu giới tính hoặc tuổi ngoài 16–90
trả 422; không tự điền. API cũ không có mode vẫn dùng nhánh lối sống. Form mới
hỏi triệu chứng theo hai nhóm và cho phép người dùng chọn nhánh lối sống.
Lịch sử giữ cả mode lẫn các câu trả lời, không so sánh xác suất khác phiên bản.
