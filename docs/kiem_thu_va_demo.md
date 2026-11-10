# Bước 12 — Kiểm thử và demo

Kết quả ngày 03/11/2026: **96 tests đạt**, coverage `--cov=.` **80,97%**;
Python lint/format và frontend lint/typecheck/build đều đạt. Demo tích hợp
**26/26 ca đạt**. Backend đầy đủ chạy trên Linux vì Windows Application Control
chặn Python/thư viện ChromaDB. Docker Linux là môi trường chạy được trên máy này;
việc chặn Python Windows không ngăn demo bằng Docker.

> **Cập nhật 09/11/2026:** KB hiện tại (146 đoạn) đã được nạp lại và demo `--require-neo4j` đạt 16/16 ca (178 nút, 181 quan hệ); xem [neo4j_verification.json](neo4j_verification.json) và [đánh giá truy xuất](danh_gia_truy_xuat_va_do_tre.md). Phần dưới là lần xác minh ngày 03/11 trên bản KB cũ.

## Xác minh lại với Neo4j thật ngày 03/11/2026

Đã chạy Neo4j `2026.10.1` trong container riêng và nạp KB bằng
`scripts/collect_corpus.py`: **46 nút, 56 quan hệ** (35 quan hệ nghiệp vụ và 21
quan hệ bằng chứng → nguồn). Truy vấn được 21 bằng chứng và các liên kết hỗ trợ
yếu tố nguy cơ có URL nguồn.

Demo `--require-neo4j --with-web` đạt **26/26 ca**, với
`kb_source=KnowledgeGraph`; chế độ này dừng khi hệ thống rơi về KB file.
Các ca gồm dự đoán thật, thiếu dữ liệu, cảnh báo, thiếu bằng chứng, lỗi thành phần,
memory, Next.js → FastAPI và lỗi backend. Bộ kiểm thử backend vừa chạy lại
trong Docker với mã nguồn hiện tại: **96 passed**, 3 cảnh báo deprecation.
Coverage 80,97% ở phần trên thuộc lần đo trước, không đo lại trong lượt này.

Kết quả rút gọn được lưu trong [neo4j_verification.json](neo4j_verification.json);
kết quả đầy đủ tại `logs/neo4j-live-demo.json` (thư mục logs không đưa vào Git).
Docker image dùng để kiểm tra là `healthcare-step12:vi`, chứa dependencies và
frontend đã build; mã nguồn backend khi chạy pytest được mount từ workspace.

Với Neo4j đang chạy và đã nạp KB, có thể kiểm tra lại bằng môi trường Python
Linux/Docker đã cài dependencies, đặt `NEO4J_URI`, `NEO4J_USER`,
`NEO4J_PASSWORD`, rồi chạy:

```bash
python scripts/collect_corpus.py
python scripts/demo_step12.py --require-neo4j --with-web --output logs/neo4j-live-demo.json
```

Neo4j dùng trong lần xác minh là database riêng phục vụ kiểm tra; không dùng
database chứa dữ liệu khác để chạy script nạp có prune mặc định.

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

Lần demo ban đầu dùng KB file và text fallback. Lần xác minh bổ sung ở trên đã
dùng Neo4j thật; cả hai dùng text fallback, chưa gọi OpenAI thật. Demo web kiểm
tra bằng HTTP, chưa tự động thao tác trình duyệt. Báo cáo dependency audit cũ
ở `logs/step12-npm-audit.json`; không dùng số cảnh báo của lần đó làm kết luận
về phiên bản dependencies hiện tại khi chưa chạy audit lại.
