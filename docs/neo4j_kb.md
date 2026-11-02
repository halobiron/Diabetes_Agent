# Knowledge graph Neo4j về tiểu đường

Nguồn dữ liệu: [data/kb/diabetes_kb.json](../data/kb/diabetes_kb.json) (version ghi trong file). Script nạp đọc file này, kiểm tra tính nhất quán rồi upsert vào Neo4j.

## Lược đồ

| Nút | Nhãn | Thuộc tính chính |
|-----|------|------------------|
| Thực thể | `:Entity` + `:Condition` / `:RiskFactor` / `:Test` / `:Intervention` | `id`, `name`, `description`, `key` (tên đặc trưng của mô hình: `BMI`, `HighBP`, `Age`…; riêng `glucose` không phải đầu vào của mô hình) |
| Bằng chứng | `:Evidence` | `id`, `text`, `section` |
| Nguồn | `:Source` | `id`, `title`, `publisher`, `year`, `url` |

Quan hệ giữa các thực thể: `INCREASES_RISK_OF`, `DIAGNOSES`, `REDUCES_RISK_OF`, `ADDRESSES` (can thiệp → yếu tố nguy cơ), `SHOULD_TEST_WITH`. Mỗi quan hệ mang `evidence_ids`; mỗi `Evidence` có `(:Evidence)-[:FROM]->(:Source)`. Nhờ vậy mọi khẳng định truy vấn ra đều đi kèm trích dẫn.

Nguồn gồm ADA Standards of Care 2025, WHO, CDC, NIDDK và thử nghiệm DPP (NEJM 2002). Nội dung bằng chứng là diễn giải ngắn từ các tài liệu này, chưa đối chiếu lại từng URL tự động; cần người có chuyên môn rà soát trước khi dùng ngoài mục đích học tập.

## Chạy

```powershell
Copy-Item .env.example .env          # đặt NEO4J_PASSWORD
docker compose up -d neo4j           # Browser: http://localhost:7474
.\.venv\Scripts\python.exe scripts/load_neo4j_kb.py --dry-run   # chỉ kiểm tra file
.\.venv\Scripts\python.exe scripts/load_neo4j_kb.py             # nạp / cập nhật
```

Xem đồ thị trong Neo4j Browser, ví dụ `MATCH (n)-[r]->(m) RETURN n,r,m LIMIT 100`, hoặc gọi `KnowledgeGraph` từ code.

Cập nhật: sửa file JSON rồi chạy lại script. Nạp là idempotent (`MERGE`); mục không còn trong file bị xoá, trừ khi thêm `--no-prune`.

## Truy vấn từ code

`tools/neo4j_kb.py` → `KnowledgeGraph`:

- `relations_with_evidence(entity_id)`: mọi quan hệ của một thực thể cùng bằng chứng và nguồn.
- `support_for_risk_factors(["BMI", "HighBP"])`: can thiệp và xét nghiệm gắn với các yếu tố nguy cơ theo tên đặc trưng; dùng cho RetrievalAgent.
- `all_evidence()`: toàn bộ đoạn bằng chứng kèm nguồn, RetrievalAgent nhúng chúng để tìm ngữ nghĩa. `FileKnowledgeBase` có cùng API, đọc từ file JSON khi Neo4j không kết nối được (hoặc chưa đặt `NEO4J_PASSWORD`).
- `find_entities(text)`, `stats()`.
