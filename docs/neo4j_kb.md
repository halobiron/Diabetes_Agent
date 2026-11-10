# Knowledge graph Neo4j về tiểu đường

Pipeline `python scripts/collect_corpus.py` thu thập web/PDF, chia đoạn, ghép đồ thị tuyển chọn và nạp trực tiếp vào Neo4j. Có thể dựng KB từ script có sẵn `artifacts/kb_diabet.cypher` mà không cần thu thập lại tài liệu. Ứng dụng, đánh giá RAG, kiểm thử tích hợp và báo cáo truy vấn dữ liệu trong Neo4j.

KB được xây từ: danh sách nguồn [data/corpus/sources.json](../data/corpus/sources.json) (web + PDF tiếng Việt: Bộ Y tế, Vinmec, WHO), các đoạn bằng chứng tự động trích và chia đoạn, và đồ thị thực thể/quan hệ viết tay trong [data/corpus/graph.json](../data/corpus/graph.json). Sửa nguồn hoặc đồ thị rồi chạy lại script; script kiểm tra mọi quan hệ đều trỏ tới đoạn bằng chứng còn tồn tại.

## Lược đồ

| Nút | Nhãn | Thuộc tính chính |
|-----|------|------------------|
| Thực thể | `:Entity` + `:Condition` / `:RiskFactor` / `:Test` / `:Intervention` | `id`, `name`, `description`, `key` (tên đặc trưng của mô hình: `BMI`, `HighBP`, `Age`…; riêng `glucose` không phải đầu vào của mô hình) |
| Bằng chứng | `:Evidence` | `id`, `text`, `section` |
| Nguồn | `:Source` | `id`, `title`, `publisher`, `year`, `url` |

Quan hệ giữa các thực thể: `INCREASES_RISK_OF`, `DIAGNOSES`, `REDUCES_RISK_OF`, `ADDRESSES` (can thiệp → yếu tố nguy cơ), `SHOULD_TEST_WITH`. Mỗi quan hệ mang `evidence_ids`; mỗi `Evidence` có `(:Evidence)-[:FROM]->(:Source)`. Nhờ vậy mọi khẳng định truy vấn ra đều đi kèm trích dẫn.

Nguồn gồm Quy trình lâm sàng ĐTĐ típ 2 của Bộ Y tế (QĐ 3798/QĐ-BYT, 2017), WHO Diabetes fact sheet và 10 bài của Vinmec. Văn bản Bộ Y tế 2017 đã được QĐ 5481/QĐ-BYT (2020) thay thế nên cần đối chiếu ngưỡng khi trích dẫn. Nội dung bằng chứng là văn bản trích nguyên từ các tài liệu này (đã lọc quảng cáo), riêng Vinmec là trang truyền thông bệnh viện; cần người có chuyên môn rà soát trước khi dùng ngoài mục đích học tập.

### Ngưỡng BMI đã chốt

Các con số 23 / 25 / 35 trong nguồn không mâu thuẫn, chúng nói về những việc khác nhau:

| Ngưỡng | Ý nghĩa | Nguồn |
|---|---|---|
| BMI ≥ 23 | Ngưỡng sàng lọc đái tháo đường típ 2 cho người Việt; dùng làm yếu tố nguy cơ trong KB | Bộ Y tế QĐ 3798/QĐ-BYT (2017); WHO Asia-Pacific (thừa cân 23–24,9) |
| BMI ≥ 25 | Béo phì độ I theo chuẩn châu Á; cũng là ngưỡng thừa cân theo CDC/WHO chung | WHO Asia-Pacific 2000; CDC |
| BMI ≥ 30 | Béo phì theo CDC/WHO chung; béo phì độ II theo chuẩn châu Á | CDC; WHO Asia-Pacific |
| BMI > 35 | Béo phì nặng (độ II/III quốc tế); Vinmec chỉ nói nguy cơ rất cao, không phải ngưỡng sàng lọc | Vinmec |

Quy ước của dự án: KB và phần giải thích bằng chứng dùng ngưỡng sàng lọc **23** của Bộ Y tế. Thang đo hiển thị trên giao diện ([patient_guidance.py](../tools/patient_guidance.py)) dùng phân nhóm CDC (25/30) vì mô hình được huấn luyện trên dữ liệu BRFSS của Mỹ; hai thang phục vụ hai mục đích và không dùng thay cho nhau.

## Chạy

```powershell
Copy-Item .env.example .env          # đặt NEO4J_PASSWORD
docker compose up -d neo4j           # Browser: http://localhost:7474 (NEO4J_PASSWORD phải từ 8 ký tự trở lên, nếu không container thoát ngay)
.\.venv\Scripts\python.exe scripts/collect_corpus.py --dry-run # trích nội dung và kiểm tra
.\.venv\Scripts\python.exe scripts/collect_corpus.py           # nạp / cập nhật trực tiếp
```

Python không tự nạp `.env`; cần nạp các biến môi trường trước khi chạy script.

### Nạp KB từ Cypher

Với Neo4j đang chạy và `NEO4J_PASSWORD` đã được nạp vào môi trường:

```powershell
Get-Content -Encoding utf8 artifacts/kb_diabet.cypher | docker compose exec -T neo4j cypher-shell -u neo4j -p $env:NEO4J_PASSWORD
```

Script gồm ràng buộc, nguồn, thực thể, bằng chứng và quan hệ; dùng `MERGE` để nạp lại không nhân đôi dữ liệu. Script có bước dọn phiên bản KB cũ, nên chỉ nạp vào database dành cho KB của dự án.

### Cập nhật script Cypher từ Neo4j

```powershell
.\.venv\Scripts\python.exe scripts/export_kb_cypher.py
```

Công cụ đọc Neo4j và cập nhật `artifacts/kb_diabet.cypher` để dùng khi triển khai hoặc khôi phục KB.

Cập nhật KB: sửa `data/corpus/sources.json` hoặc `data/corpus/graph.json`, rồi chạy `collect_corpus.py`. Script chỉ nạp khi thu thập đủ nguồn và dữ liệu hợp lệ.

## Truy vấn từ code

Đã xác minh trên Neo4j thật `2026.10.1` trong Docker ngày 03/11/2026:
nạp được 46 nút, 56 quan hệ; truy xuất 21 bằng chứng; luồng API + web dùng
`KnowledgeGraph` đạt 26/26 ca demo. Xem [kết quả xác minh](neo4j_verification.json)
và [cách kiểm tra lại](kiem_thu_va_demo.md). Đây là kết quả trên phiên bản đã
chạy; cấu hình Compose vẫn khai báo `neo4j:5-community`.

**Lưu ý số liệu:** lần xác minh ngày 03/11/2026 (46 nút, 56 quan hệ, 21 bằng chứng) được thực hiện trên bản KB cũ. Bản KB hiện tại (corpus-2026-11-08) có 20 thực thể, 35 quan hệ, 146 đoạn bằng chứng và 12 nguồn, nên các con số trên không còn đúng với KB hiện tại. Ngày 09/11/2026 KB hiện tại đã được nạp lại vào Neo4j 5.26.32: **178 nút, 181 quan hệ, 146 đoạn bằng chứng**; demo `--require-neo4j` (không gồm web) đạt 16/16 ca. Xem [neo4j_verification.json](neo4j_verification.json) và [đánh giá truy xuất](danh_gia_truy_xuat_va_do_tre.md).

`tools/neo4j_kb.py` → `KnowledgeGraph`:

- `relations_with_evidence(entity_id)`: mọi quan hệ của một thực thể cùng bằng chứng và nguồn.
- `support_for_risk_factors(["BMI", "HighBP"])`: can thiệp và xét nghiệm gắn với các yếu tố nguy cơ theo tên đặc trưng; dùng cho RetrievalAgent.
- `all_evidence()`: toàn bộ đoạn bằng chứng kèm nguồn, RetrievalAgent nhúng chúng để tìm ngữ nghĩa. Khi chạy ứng dụng, Neo4j là bắt buộc: thiếu `NEO4J_PASSWORD` hoặc lỗi kết nối lúc khởi tạo sẽ báo lỗi. Ứng dụng, đánh giá và báo cáo đều đọc Neo4j.
- `export_kb()`: đọc toàn bộ tri thức hiện tại trong một truy vấn để tạo báo cáo và xuất Cypher.
- `stats()`.
