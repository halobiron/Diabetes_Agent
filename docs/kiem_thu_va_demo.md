# Bước 12 — Kiểm thử và demo

Kết quả ngày 03/11/2026: **96 tests đạt**, coverage `--cov=.` **80,97%**;
Python lint/format và frontend lint/typecheck/build đều đạt. Demo tích hợp
**26/26 ca đạt**. Backend đầy đủ chạy trên Linux vì Windows Application Control
chặn Python/thư viện ChromaDB.

## Chạy lại

Dùng môi trường Python đã cài dependencies của dự án và torch cho test MLP:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
Push-Location web
npm run lint
npm run typecheck
npm run build
Pop-Location
.\.venv\Scripts\python.exe scripts/demo_step12.py --with-web
```

Script dùng artifact thật, tạo dữ liệu/memory tạm và tự dừng các dịch vụ nó tạo.
Bỏ `--with-web` để chỉ demo API. Kết quả lưu tại `logs/step12-demo.json`;
log kiểm thử đã chạy tại `logs/step12-pytest.txt`.

## Các ca demo

| Ca | Kết quả cần xem |
|---|---|
| Hồ sơ đủ / thiếu trường tùy chọn | Điểm chất lượng 1 / giảm; liệt kê trường tự điền, glucose thiếu không phải số đo thật |
| Thiếu BMI và chiều cao/cân nặng | HTTP 422 |
| BP 190, glucose 320 | Luật cảnh báo và chuyển bác sĩ khẩn, dù mô hình dự đoán thấp |
| Không có / ít bằng chứng | `evidence_status=none/limited`, lời khuyên nêu rõ giới hạn; giữ cảnh báo |
| Lỗi thành phần tùy chọn | `degraded`, nội dung dự phòng; lỗi policy không làm mất kết quả an toàn |
| Lỗi mô hình | HTTP 500, không tạo xác suất giả |
| Lặp hồ sơ / lịch sử | Có ca tương tự, `outcome_confirmed=false`, request ID đối chiếu audit |
| Backend ngừng | Ba proxy web trả HTTP 502 |

## Vai trò thành phần

Next.js/FastAPI nhận và kiểm tra hồ sơ; RiskModel chạy MLP; FeatureExplainer giải
thích đặc trưng; RetrievalAgent tìm bằng chứng có nguồn; SafetyGuard áp dụng luật;
QPolicy chọn bước tiếp theo; ExplanationAgent/RecommendationAgent tạo nội dung;
MemoryAgent lưu và tìm ca; Orchestrator điều phối và xử lý lỗi.

Demo dùng KB file và text fallback, chưa xác nhận Neo4j/OpenAI thật hoặc thao tác
trình duyệt tự động. `npm audit` còn 24 cảnh báo, gồm 1 critical ở Next.js;
báo cáo tại `logs/step12-npm-audit.json`.
