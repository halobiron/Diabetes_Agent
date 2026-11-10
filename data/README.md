# Vòng đời dữ liệu

| Vị trí | Mục đích | Khi nào được đọc |
|---|---|---|
| `corpus/sources.json` | URL và cấu hình thu thập nguồn | Khi chạy `scripts/collect_corpus.py` |
| `corpus/graph.json` | Thực thể, quan hệ tuyển chọn và ID bằng chứng | Khi chạy `scripts/collect_corpus.py` |
| `corpus/.cache/` | HTML/PDF tải về, không đưa vào Git | Khi thu thập tài liệu |
| `train/` | CSV BRFSS tải về, không đưa vào Git | Khi huấn luyện và tạo báo cáo |
| `chroma/` | Chỉ mục vector và bộ nhớ ca, không đưa vào Git | Khi ứng dụng chạy |
| `eval/rag_retrieval_questions.json` | Bộ câu hỏi có nhãn đánh giá RAG | Khi chạy `scripts/evaluate_retrieval.py` |
| Neo4j | Cơ sở tri thức dùng khi chạy hệ thống | Ứng dụng, đánh giá RAG, kiểm thử tích hợp và báo cáo |
| `../artifacts/` | Mô hình, policy và chỉ số đánh giá | Ứng dụng nạp mô hình/policy; báo cáo dùng chỉ số |
| `../artifacts/kb_diabet.cypher` | Script dựng hoặc nạp lại KB vào Neo4j | Khi triển khai hoặc khôi phục cơ sở dữ liệu |

Luồng xây dựng KB: nguồn web/PDF → trích và chia đoạn trong bộ nhớ → ghép đồ thị tuyển chọn → kiểm tra → Neo4j. Pipeline không ghi `passages.jsonl` hay một tệp KB trung gian.

Ứng dụng truy vấn Neo4j và ChromaDB; không đọc bộ câu hỏi đánh giá hoặc CSV huấn luyện. Khởi tạo nạp mô hình đã huấn luyện tại `MODEL_ARTIFACT_PATH` (mặc định `artifacts/risk_model.joblib`). ChromaDB là chỉ mục tìm kiếm và bộ nhớ ca; tri thức nguồn được đọc từ Neo4j.

Chạy từ thư mục gốc dự án:

```powershell
# Chuẩn bị dữ liệu huấn luyện và artifact
.\.venv\Scripts\python.exe scripts/download_training_data.py
.\.venv\Scripts\python.exe scripts/train_diabetes_model.py

# Xây dựng/cập nhật Neo4j (nạp biến môi trường Neo4j trước)
.\.venv\Scripts\python.exe scripts/collect_corpus.py

# Đánh giá RAG từ Neo4j
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py

# Xuất script nạp dữ liệu vào artifacts/kb_diabet.cypher
.\.venv\Scripts\python.exe scripts/export_kb_cypher.py

# Nạp KB có sẵn từ Cypher vào Neo4j
Get-Content -Encoding utf8 artifacts/kb_diabet.cypher | docker compose exec -T neo4j cypher-shell -u neo4j -p $env:NEO4J_PASSWORD
```

Các công cụ cần cấu hình `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` và `NEO4J_DATABASE`. Kiểm thử tích hợp và notebook báo cáo cũng cần Neo4j đã có dữ liệu. Có thể nạp KB từ `artifacts/kb_diabet.cypher` mà không cần tải lại nguồn. Khi cần cập nhật tri thức từ web/PDF, chạy `collect_corpus.py`, rồi xuất lại Cypher để đồng bộ script triển khai. Ứng dụng truy vấn dữ liệu trong Neo4j sau khi nạp.

Các đường dẫn nằm trong metadata hoặc kết quả đánh giá đã lưu phản ánh thời điểm tạo artifact, không phải cấu hình đường dẫn hiện tại.
