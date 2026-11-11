# Vòng đời dữ liệu

| Vị trí | Mục đích | Khi nào được đọc |
|---|---|---|
| `corpus/sources.json` | URL và cấu hình thu thập nguồn | Khi chạy `scripts/collect_corpus.py` |
| `corpus/.cache/` | HTML/PDF tải về, không đưa vào Git | Khi thu thập tài liệu |
| `train/` | CSV BRFSS tải về, không đưa vào Git | Khi huấn luyện và tạo báo cáo |
| `chroma/` | Chỉ mục vector và bộ nhớ ca, không đưa vào Git | Khi ứng dụng chạy |
| `eval/rag_retrieval_questions.json` | Bộ câu hỏi có nhãn đánh giá RAG | Khi chạy `scripts/evaluate_retrieval.py` |
| Neo4j | Nguồn sự thật của tri thức: nguồn, đoạn bằng chứng, thực thể và quan hệ tuyển chọn | Ứng dụng, đánh giá RAG, kiểm thử tích hợp, báo cáo và `collect_corpus.py` |
| `../artifacts/` | Mô hình, policy và chỉ số đánh giá | Ứng dụng nạp mô hình/policy; báo cáo dùng chỉ số |
| `../artifacts/kb_diabet.cypher` | Bản seed của KB trong Git, xuất từ Neo4j | Khi dựng môi trường mới, chạy CI hoặc khôi phục cơ sở dữ liệu |

Luồng xây dựng KB: nạp `kb_diabet.cypher` vào Neo4j → sửa thực thể/quan hệ trực tiếp trong Neo4j khi cần → làm mới bằng chứng từ web/PDF bằng `collect_corpus.py` → xuất lại `kb_diabet.cypher` và commit. Đoạn bằng chứng có ID ổn định theo nội dung (`ev-<nguồn>-<8 ký tự sha256>`), nên đoạn không đổi thì quan hệ vẫn trỏ đúng sau mỗi lần thu thập lại.

Ứng dụng truy vấn Neo4j và ChromaDB; không đọc bộ câu hỏi đánh giá hoặc CSV huấn luyện. Khởi tạo nạp mô hình đã huấn luyện tại `MODEL_ARTIFACT_PATH` (mặc định `artifacts/risk_model.joblib`). ChromaDB là chỉ mục tìm kiếm và bộ nhớ ca; tri thức nguồn được đọc từ Neo4j.

Chạy từ thư mục gốc dự án:

```powershell
# Chuẩn bị dữ liệu huấn luyện và artifact
.\.venv\Scripts\python.exe scripts/download_training_data.py
.\.venv\Scripts\python.exe scripts/train_diabetes_model.py

# Nạp KB có sẵn từ Cypher vào Neo4j (nạp biến môi trường Neo4j trước)
Get-Content -Encoding utf8 artifacts/kb_diabet.cypher | docker compose exec -T neo4j cypher-shell -u neo4j -p $env:NEO4J_PASSWORD

# Làm mới nguồn và đoạn bằng chứng từ web/PDF, giữ thực thể/quan hệ trong Neo4j
.\.venv\Scripts\python.exe scripts/collect_corpus.py

# Đánh giá RAG từ Neo4j
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py

# Xuất script nạp dữ liệu vào artifacts/kb_diabet.cypher
.\.venv\Scripts\python.exe scripts/export_kb_cypher.py
```

Các công cụ cần cấu hình `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` và `NEO4J_DATABASE`. Kiểm thử tích hợp và notebook báo cáo cũng cần Neo4j đã có dữ liệu. Môi trường mới nạp KB từ `artifacts/kb_diabet.cypher`; `collect_corpus.py` cần KB đã có trong Neo4j vì nó đọc thực thể và quan hệ từ đó. Sau mỗi lần sửa tri thức hoặc thu thập lại, chạy `export_kb_cypher.py` để đồng bộ bản seed. Ứng dụng truy vấn dữ liệu trong Neo4j sau khi nạp.

Các đường dẫn nằm trong metadata hoặc kết quả đánh giá đã lưu phản ánh thời điểm tạo artifact, không phải cấu hình đường dẫn hiện tại.
