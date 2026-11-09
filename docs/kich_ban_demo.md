# Kịch bản demo (khoảng 10 phút)

Thứ tự: **1. KB Neo4j → 2. Chat RAG → 3. Hệ đa Agent**. Mỗi phần có cách chạy trên giao diện và phương án dự phòng trên terminal.

## Chuẩn bị trước buổi demo (làm một lần)

PowerShell, tại thư mục dự án:

```powershell
# 1. Bật Neo4j (dữ liệu đã nằm trong volume; chỉ cần nạp lại nếu xóa volume)
docker compose up -d neo4j

# 2. Nạp biến môi trường từ .env (Python không tự đọc .env)
Get-Content .env | ForEach-Object { if ($_ -match '^\s*([^#=\s]+)\s*=\s*(.*)$') { Set-Item "env:$($Matches[1])" $Matches[2] } }

# 3. (Chỉ khi cần nạp lại KB)
.\.venv\Scripts\python.exe scripts\load_neo4j_kb.py

# 4. Chạy backend (cửa sổ này); giao diện chạy ở cửa sổ khác
.\.venv\Scripts\python.exe -m uvicorn api.app:app --host 127.0.0.1 --port 8010
# Cửa sổ 2: cd web; $env:API_BASE_URL="http://127.0.0.1:8010"; npm run dev
```

Mở sẵn hai cửa sổ trình duyệt: http://localhost:7474 (Neo4j Browser, đăng nhập `neo4j` + mật khẩu trong `.env`) và http://localhost:3000 (giao diện). Lần đầu mở giao diện mất vài chục giây để tải mô hình nhúng.

Phương án dự phòng nếu giao diện lỗi: `.\.venv\Scripts\python.exe scripts\demo.py` chạy cả ba phần trên terminal (`--part 1|2|3` để chạy riêng một phần).

## Phần 1 - Show KB Neo4j (2-3 phút)

**Trên giao diện web:** nhập một hồ sơ rồi xem phần "Cơ sở tri thức Neo4j đã dùng cho hồ sơ này" ở cuối trang kết quả. Huy hiệu cho biết đang đọc từ Neo4j hay file dự phòng, kèm số thực thể, quan hệ, đoạn bằng chứng và nguồn. Các thực thể viền vàng là phần hệ thống đã dùng cho hồ sơ đó; bấm một thực thể để xem quan hệ và các đoạn tài liệu làm căn cứ (đoạn đã dùng được đánh dấu). Phần Hỏi đáp ngay bên dưới dùng cùng đồ thị này khi truy xuất.

**Nói:** KB được xây từ 12 tài liệu y khoa tiếng Việt (Bộ Y tế, WHO, Vinmec). Từ đó trích ra 20 thực thể, 35 quan hệ và 146 đoạn bằng chứng, sinh file `data/kb/kb_diabet.cypher` rồi nạp vào Neo4j.

Trong Neo4j Browser chạy lần lượt:

```cypher
// Toàn bộ đồ thị tri thức: bệnh, yếu tố nguy cơ, xét nghiệm, can thiệp
MATCH (a:Entity)-[r]->(b:Entity) RETURN a, r, b
```

```cypher
// Mỗi quan hệ đều truy được về đoạn văn và nguồn gốc
MATCH (f:RiskFactor {id:'high_bmi'})-[r]->(x:Entity)
UNWIND r.evidence_ids AS eid
MATCH (e:Evidence {id: eid})-[:FROM]->(s:Source)
RETURN f.name AS yeu_to, type(r) AS quan_he, x.name AS dich, e.id AS bang_chung, s.publisher AS nguon
```

```cypher
// Đọc nguyên văn một đoạn bằng chứng
MATCH (e:Evidence {id:'ev-moh-qt-2017-017'}) RETURN e.text
```

**Điểm cần nhấn:** mọi quan hệ đều có trích dẫn. Ngưỡng BMI ≥ 23 lấy từ văn bản Bộ Y tế; các bài Vinmec còn nêu 25 và 35 cho mục đích khác nên đồ thị không dùng làm bằng chứng cho ngưỡng này.

## Phần 2 - Chat RAG (3 phút)

Trên giao diện Next.js, ngay ở màn nhập hồ sơ, kéo xuống và mở panel "Hỏi đáp về đái tháo đường". Hỏi lần lượt:

| Câu hỏi | Để cho thấy |
|---|---|
| Béo phì có làm tăng nguy cơ tiểu đường không? | Đồ thị nhận ra yếu tố BMI, đoạn "BMI ≥ 23" của Bộ Y tế được cộng điểm |
| Chẩn đoán đái tháo đường bằng xét nghiệm nào? | Thuần ngữ nghĩa, không có yếu tố đồ thị, vẫn trích đúng đoạn về glucose lúc đói và A1C |
| Hút thuốc lá ảnh hưởng thế nào đến bệnh tiểu đường? | Đoạn "ngừng hút thuốc" lên đầu (điểm 0,91) |
| Cách nấu phở bò ngon | Hệ thống từ chối vì không đoạn nào đạt ngưỡng 0,4 của chat (điểm cao nhất 0,304) |

Sau mỗi câu, mở mục **"Cách hệ thống truy xuất (vết RAG)"** và đọc 4 bước: nhúng câu hỏi → so cosine với 146 đoạn → đồ thị cộng 0,15 điểm cho đoạn liên kết → xếp hạng và trích dẫn. Giải thích đầy đủ ở [rag_giai_thich.md](rag_giai_thich.md).

**Câu trả lời mẫu cho "RAG liên quan KB thế nào?":** KB là nguồn duy nhất của RAG. Neo4j giữ cấu trúc (yếu tố nguy cơ → can thiệp → đoạn bằng chứng) và Chroma giữ vector của cùng 146 đoạn đó. Câu hỏi được tìm bằng vector, rồi đồ thị quyết định đoạn nào được ưu tiên. Mọi câu trả lời đều trích được về nguồn.

## Phần 3 - Hệ đa Agent (3-4 phút)

Ở thanh bên nhập **hồ sơ nguy cơ cao** rồi bấm "Phân tích hồ sơ": tuổi 62, chiều cao/cân nặng cho BMI 34, huyết áp 150, đường huyết 135, có cholesterol cao, hút thuốc, ít vận động, sức khỏe tổng quát 4, khó đi lại, từng có bệnh tim. Kết quả mong đợi: xác suất khoảng 56%, mức Cao, bước tiếp theo "chuyển bác sĩ".

**Chỉ ra 3 vai trò** (trong `trace.steps` mỗi bước có trường `agent`; `scripts/demo.py` in sẵn bảng này):

| Agent | Việc làm trong lần chạy |
|---|---|
| **Agent chẩn đoán** | `risk_model`: MLP cho xác suất 56%; `feature_explainer`: đặc trưng nào đẩy nguy cơ lên |
| **Agent tư vấn** | `retriever`: lấy 3 đoạn từ KB Neo4j; `recommender`: khuyến nghị có trích dẫn; `explainer`: giải thích kết quả |
| **Agent điều phối** | `safety_guard`: bộ luật an toàn; `support_policy`: Q-learning chọn bước tiếp theo; `what_if`: mô phỏng đổi lối sống; điều phối thứ tự và ghi lỗi |

Sau đó chạy **hồ sơ nguy cơ thấp** (tuổi 28, BMI 21, huyết áp 112, đường huyết 88, vận động, ăn rau và trái cây): xác suất gần 0, bước tiếp theo "tư vấn định kỳ", cho thấy hệ thống không chuyển bác sĩ không cần thiết.

## Câu hỏi giảng viên có thể hỏi

- **Mô hình DL là gì, độ chính xác ra sao?** MLP PyTorch hai lớp ẩn (128, 64), huấn luyện trên BRFSS2015 (253.680 mẫu, 21 đặc trưng), xác suất đã hiệu chuẩn. Trên tập test: ROC-AUC 0,826, recall 0,60, precision 0,38 ở ngưỡng 0,239. Chi tiết trong [model card](../artifacts/model_card.md).
- **Đây có phải chẩn đoán y khoa không?** Không. Dữ liệu là khảo sát tự khai, mô hình chỉ ước lượng nguy cơ; kết quả luôn kèm khuyến nghị gặp bác sĩ.
- **Nếu Neo4j hỏng?** `RetrievalAgent` tự chuyển sang đọc `data/kb/diabetes_kb.json`, vết RAG ghi rõ nguồn KB đang dùng.
- **Nếu một agent lỗi?** Lỗi mô hình không trả xác suất giả. Lỗi tư vấn dùng nội dung dự phòng và được ghi vào `degraded`. Lỗi bộ luật chuyển sang "cần bác sĩ đánh giá".
- **Chat có dùng LLM không?** Không. Câu trả lời ghép từ các đoạn tài liệu truy xuất được, nên không bịa nội dung ngoài KB. Đổi lại văn phong là trích đoạn, không mượt như LLM.
- **Hạn chế đã biết:** KB nhỏ (12 nguồn); chưa có bộ câu hỏi đánh giá chính thức cho RAG; Q-learning huấn luyện trên phản hồi mô phỏng.
