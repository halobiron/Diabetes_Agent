# Vòng đời dữ liệu

| Vị trí | Mục đích | Khi nào được đọc |
|---|---|---|
| `corpus/sources.json` | URL và cấu hình thu thập nguồn | Khi chạy `scripts/collect_corpus.py` |
| `corpus/graph.json` | Thực thể, quan hệ tuyển chọn và ID bằng chứng | Khi chạy `scripts/collect_corpus.py` |
| `corpus/.cache/` | HTML/PDF tải về, không đưa vào Git | Khi thu thập tài liệu |
| `training/` | CSV BRFSS tải về, không đưa vào Git | Khi huấn luyện và tạo báo cáo |
| `chroma/` | Chỉ mục vector và bộ nhớ ca, không đưa vào Git | Khi ứng dụng chạy |
| `../evaluation/retrieval_questions.json` | Bộ câu hỏi có nhãn đánh giá RAG | Khi chạy `scripts/evaluate_retrieval.py` |
| `../tests/fixtures/diabetes_kb.json` | Một bản chụp KB cố định dùng chung | Kiểm thử, đánh giá offline, báo cáo, khôi phục tùy chọn |
| `../tests/fixtures/patients.csv` | CSV mẫu cho mô hình demo cũ | Khi chạy `scripts/evaluate_model.py` |
| `../artifacts/` | Mô hình, policy, chỉ số và bản xuất Cypher | Ứng dụng nạp mô hình/policy; công cụ và báo cáo dùng các tệp còn lại |

Luồng xây dựng KB: nguồn web/PDF → trích và chia đoạn trong bộ nhớ → ghép đồ thị tuyển chọn → kiểm tra → Neo4j. Pipeline không ghi `passages.jsonl` hay một tệp KB trung gian.

Ứng dụng truy vấn Neo4j và ChromaDB; không đọc bản chụp KB hoặc CSV huấn luyện/demo. Khởi tạo nạp mô hình đã huấn luyện tại `MODEL_ARTIFACT_PATH` (mặc định `artifacts/risk_model.joblib`).

Chạy từ thư mục gốc dự án:

```powershell
# Chuẩn bị dữ liệu huấn luyện và artifact
.\.venv\Scripts\python.exe scripts/download_training_data.py
.\.venv\Scripts\python.exe scripts/train_diabetes_model.py

# Xây dựng/cập nhật Neo4j (nạp biến môi trường Neo4j trước)
.\.venv\Scripts\python.exe scripts/collect_corpus.py

# Đánh giá từ bản chụp hoặc từ Neo4j
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py --kb file
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py --kb neo4j

# Kiểm tra bản chụp; xuất Cypher vào artifacts/kb_diabet.cypher
.\.venv\Scripts\python.exe scripts/load_neo4j_kb.py --dry-run
.\.venv\Scripts\python.exe scripts/export_kb_cypher.py
```

`KB_PATH` cho phép chọn bản chụp khác cho kiểm thử và công cụ offline; không thay đổi nguồn tri thức của ứng dụng. Khi đánh giá Neo4j, công cụ không cần đọc bản chụp. Khi sửa nguồn hoặc đồ thị, cần chạy lại pipeline để cập nhật Neo4j; bản chụp kiểm thử không tự thay đổi theo dữ liệu đang chạy.

Các đường dẫn nằm trong metadata hoặc kết quả đánh giá đã lưu phản ánh thời điểm tạo artifact, không phải cấu hình đường dẫn hiện tại.
