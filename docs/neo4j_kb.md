# Knowledge graph Neo4j về tiểu đường

Nguồn dữ liệu: [data/kb/diabetes_kb.json](../data/kb/diabetes_kb.json) (version ghi trong file). Script nạp đọc file này, kiểm tra tính nhất quán rồi upsert vào Neo4j.

File KB được sinh ra bằng `python scripts/collect_corpus.py --install` từ: danh sách nguồn [data/corpus/sources.json](../data/corpus/sources.json) (web + PDF tiếng Việt: Bộ Y tế, Vinmec, WHO), các đoạn bằng chứng tự động trích và chia đoạn, và đồ thị thực thể/quan hệ viết tay trong [data/corpus/graph.json](../data/corpus/graph.json). Sửa nguồn hoặc đồ thị rồi chạy lại script; script kiểm tra mọi quan hệ đều trỏ tới đoạn bằng chứng còn tồn tại.

## Lược đồ

| Nút | Nhãn | Thuộc tính chính |
|-----|------|------------------|
| Thực thể | `:Entity` + `:Condition` / `:RiskFactor` / `:Test` / `:Intervention` | `id`, `name`, `description`, `key` (tên đặc trưng của mô hình: `BMI`, `HighBP`, `Age`…; riêng `glucose` không phải đầu vào của mô hình) |
| Bằng chứng | `:Evidence` | `id`, `text`, `section` |
| Nguồn | `:Source` | `id`, `title`, `publisher`, `year`, `url` |

Quan hệ giữa các thực thể: `INCREASES_RISK_OF`, `DIAGNOSES`, `REDUCES_RISK_OF`, `ADDRESSES` (can thiệp → yếu tố nguy cơ), `SHOULD_TEST_WITH`. Mỗi quan hệ mang `evidence_ids`; mỗi `Evidence` có `(:Evidence)-[:FROM]->(:Source)`. Nhờ vậy mọi khẳng định truy vấn ra đều đi kèm trích dẫn.

Nguồn gồm Quy trình lâm sàng ĐTĐ típ 2 của Bộ Y tế (QĐ 3798/QĐ-BYT, 2017), WHO Diabetes fact sheet và 10 bài của Vinmec. Văn bản Bộ Y tế 2017 đã được QĐ 5481/QĐ-BYT (2020) thay thế nên cần đối chiếu ngưỡng khi trích dẫn. Nội dung bằng chứng là văn bản trích nguyên từ các tài liệu này (đã lọc quảng cáo), riêng Vinmec là trang truyền thông bệnh viện và có chỗ chưa thống nhất ngưỡng (BMI 23/25/35); cần người có chuyên môn rà soát trước khi dùng ngoài mục đích học tập.

## Chạy

```powershell
Copy-Item .env.example .env          # đặt NEO4J_PASSWORD
docker compose up -d neo4j           # Browser: http://localhost:7474 (NEO4J_PASSWORD phải từ 8 ký tự trở lên, nếu không container thoát ngay)
.\.venv\Scripts\python.exe scripts/load_neo4j_kb.py --dry-run   # chỉ kiểm tra file
.\.venv\Scripts\python.exe scripts/load_neo4j_kb.py             # nạp / cập nhật
```

Nạp bằng file Cypher (không cần Python), ví dụ với container Compose:

```powershell
.\.venv\Scripts\python.exe scripts/export_kb_cypher.py        # sinh data/kb/kb_diabet.cypher từ diabetes_kb.json
Get-Content data/kb/kb_diabet.cypher | docker compose exec -T neo4j cypher-shell -u neo4j -p <mật khẩu>
```

File Cypher dùng `MERGE` nên chạy lại nhiều lần không nhân đôi dữ liệu, và dọn các mục thuộc phiên bản KB cũ. Đã kiểm tra trên Neo4j 5 thật: nạp cả hai cách (Cypher rồi Python) cho cùng 178 nút và 181 quan hệ.

Xem đồ thị trong Neo4j Browser, ví dụ `MATCH (n)-[r]->(m) RETURN n,r,m LIMIT 100`, hoặc gọi `KnowledgeGraph` từ code.

Cập nhật: sửa file JSON rồi chạy lại script. Nạp là idempotent (`MERGE`); mục không còn trong file bị xoá, trừ khi thêm `--no-prune`.

## Truy vấn từ code

Đã xác minh trên Neo4j thật `2026.10.1` trong Docker ngày 03/11/2026:
nạp được 46 nút, 56 quan hệ; truy xuất 21 bằng chứng; luồng API + web dùng
`KnowledgeGraph` đạt 26/26 ca demo. Xem [kết quả xác minh](neo4j_verification.json)
và [cách kiểm tra lại](kiem_thu_va_demo.md). Đây là kết quả trên phiên bản đã
chạy; cấu hình Compose vẫn khai báo `neo4j:5-community`.

`tools/neo4j_kb.py` → `KnowledgeGraph`:

- `relations_with_evidence(entity_id)`: mọi quan hệ của một thực thể cùng bằng chứng và nguồn.
- `support_for_risk_factors(["BMI", "HighBP"])`: can thiệp và xét nghiệm gắn với các yếu tố nguy cơ theo tên đặc trưng; dùng cho RetrievalAgent.
- `all_evidence()`: toàn bộ đoạn bằng chứng kèm nguồn, RetrievalAgent nhúng chúng để tìm ngữ nghĩa. `FileKnowledgeBase` có cùng API, đọc từ file JSON khi Neo4j không kết nối được (hoặc chưa đặt `NEO4J_PASSWORD`).
- `find_entities(text)`, `stats()`.
