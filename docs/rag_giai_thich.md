# RAG truy xuất cơ sở tri thức như thế nào

Tài liệu này dùng để trả lời câu hỏi "RAG và KB liên quan với nhau ra sao" khi demo.

## 1. KB chứa gì

KB được xây từ 12 tài liệu y khoa tiếng Việt (Quyết định 3798/QĐ-BYT của Bộ Y tế, bản tóm tắt của WHO, 10 bài của Vinmec).

| Thành phần | Số lượng | Lưu ở đâu | Vai trò |
|---|---|---|---|
| Đoạn bằng chứng (`Evidence`) | 146 | Neo4j (vector giữ trong bộ nhớ) | Văn bản gốc để trích dẫn |
| Thực thể (`Entity`) | 20 | Neo4j | Bệnh, yếu tố nguy cơ, xét nghiệm, can thiệp |
| Quan hệ | 35 | Neo4j | Nối thực thể với nhau, mỗi quan hệ trỏ về đoạn bằng chứng |
| Nguồn (`Source`) | 12 | Neo4j | Tên, nhà xuất bản, năm, đường dẫn |

Hai nơi lưu có hai việc khác nhau:
- **Chỉ mục vector trong bộ nhớ:** 146 vector bge-m3 dựng lúc khởi động (dưới 1 giây trên GPU), tìm đoạn văn có nghĩa gần với câu hỏi bằng một phép nhân ma trận.
- **Neo4j (đồ thị):** cho biết yếu tố nguy cơ nào dẫn tới can thiệp hay xét nghiệm nào, và đoạn bằng chứng nào chứng minh quan hệ đó.

## 2. Luồng truy xuất

```
Câu hỏi
  │ 1. nhúng bằng BAAI/bge-m3 (GPU: fp16, ~19 ms cả lượt hỏi)
  ▼
Ma trận vector: độ tương đồng cosine với 146 đoạn
  │ 2. bỏ đoạn có điểm < 0.55 (chat; luồng bệnh nhân 0.5)
  ▼
Đoạn còn lại ──────────────┐
  │                        │ 3. nhận ra yếu tố nguy cơ trong câu hỏi bằng
  │                        │    tên + `aliases` của RiskFactor trong Neo4j
  │                        │    ("mập", "bố mẹ", ...)
  │                        ▼
  │                  Neo4j: yếu tố -INCREASES_RISK_OF→ bệnh
  │                         yếu tố ← can thiệp/xét nghiệm
  │                         (dùng cả hai loại liên kết)
  ▼                        ▼
4. đoạn có liên kết đồ thị được cộng 0.03 điểm
  ▼
5. xếp theo điểm cuối, lấy tối đa 5 đoạn
  ▼
6. ghép câu trả lời từ 3 đoạn đầu, đánh số [1] [2] [3] kèm nguồn:
   mỗi đoạn chỉ trích các câu gần câu hỏi nhất (khoảng 320 ký tự),
   phần bị lược đánh dấu "…"
```

**Vì sao chỉ cộng 0.03 (luồng bệnh nhân vẫn cộng 0.15).** Điểm cosine của các đoạn đúng chủ đề nằm sát nhau (10 đoạn đầu của câu "Béo phì ảnh hưởng đến nguy cơ tiểu đường thế nào?" chỉ cách nhau khoảng 0.05). Với mức cộng 0.15, mọi đoạn có liên kết đồ thị đều vượt lên trên đoạn khớp nghĩa nhất. Trước bản sửa ngày 11/11/2026, chat còn chỉ đi theo quan hệ can thiệp/xét nghiệm, nên câu hỏi "béo phì ảnh hưởng thế nào" bị trả lời bằng đoạn *điều trị* ("Quản lý tiểu đường type 2: giảm cân…"), còn đoạn giải thích *mô mỡ làm tế bào đề kháng insulin* rơi khỏi top 3. Số đo trước và sau: xem [đánh giá truy xuất](danh_gia_truy_xuat_va_do_tre.md#3b-cập-nhật-11112026-định-tuyến-đồ-thị-theo-ý-định-câu-hỏi).

Nếu không có đoạn nào đạt ngưỡng, hệ thống từ chối trả lời thay vì bịa. Các ngưỡng là điểm cosine của bge-m3 và chỉ có nghĩa với model này: chat dùng **0.55**, luồng bệnh nhân dùng 0.5 (model cũ MiniLM dùng 0.4 và 0.3). Ở 0.55, cả 8 câu ngoài phạm vi đều bị từ chối, kể cả hai câu gần chủ đề (cúm mùa, ung thư phổi) mà MiniLM để lọt; cách chọn: xem [đánh giá truy xuất](danh_gia_truy_xuat_va_do_tre.md#3c-cập-nhật-11112026-mô-hình-bge-m3-và-alias-trong-kb).

## 3. Ví dụ đã chạy thật

| Câu hỏi | Điểm cao nhất | Yếu tố nhận ra | Kết quả |
|---|---|---|---|
| Béo phì có làm tăng nguy cơ tiểu đường không? | 0.83 | BMI | [1] là đoạn "càng nhiều mô mỡ… tế bào càng đề kháng insulin" (đo lại 11/11/2026) |
| Chẩn đoán đái tháo đường bằng xét nghiệm nào? | 0.83 | không | Trích đoạn về xét nghiệm đường huyết lúc đói, A1C |
| Hút thuốc lá ảnh hưởng thế nào? | 0.71 | Smoker | Đoạn "hút thuốc làm tăng nguy cơ kháng insulin" lên đầu |
| Cách nấu phở bò ngon | 0.24 | không | Từ chối |

## 4. Vì sao dùng cả vector lẫn đồ thị

- Chỉ dùng vector: tìm được đoạn "gần nghĩa" nhưng không biết đoạn nào là bằng chứng cho một quan hệ y khoa cụ thể.
- Thêm đồ thị: đoạn được chính quan hệ trong KB trích dẫn (ví dụ `Hút thuốc lá` → `Bỏ thuốc lá`) được ưu tiên, nên câu trả lời bám theo cấu trúc tri thức đã được kiểm duyệt.

## 5. Giới hạn cần nói thật khi bảo vệ

- Câu trả lời ghép từ các câu trích, không do LLM viết lại. Việc chọn câu theo câu hỏi giúp bớt phần lạc đề nhưng vẫn có thể còn câu chung chung.
- Hệ thống không phân biệt câu hỏi "ảnh hưởng thế nào" với câu hỏi "nên làm gì": nó dùng mọi liên kết đồ thị của yếu tố nguy cơ. Đã thử nhận ý định bằng từ khóa và bằng embedding, nhưng không cách nào cho câu trả lời tốt hơn (xem mục 3e của [đánh giá truy xuất](danh_gia_truy_xuat_va_do_tre.md)). Vì vậy, với câu hỏi "nên làm gì", đôi khi một đoạn nói về nguy cơ chen vào top 3.
- Yếu tố nguy cơ được nhận ra bằng alias trong KB, khớp nguyên từ. Trên bộ kiểm tra độc lập, alias nhận đúng 22/30 yếu tố; còn sót các cách nói như "cao máu", "70 ký", "150/95". Bổ sung alias là sửa dữ liệu KB, không phải sửa code.
- Độ liên quan chỉ do embedding quyết định. Chưa có bộ câu hỏi đánh giá chính thức.
- KB nhỏ (12 nguồn), không thay thế tư vấn y tế.
- Ngưỡng BMI trong KB là 23 kg/m² theo Bộ Y tế. Các bài Vinmec còn nêu 25 và 35 cho các mục đích khác.

## 6. Cách chạy

- API: `POST /v1/chat` với `{"question": "..."}`. Kết quả gồm `answer`, `citations`, `status` và `trace` (các bước ở mục 2 kèm số liệu).
- Giao diện: panel **Hỏi đáp** trong giao diện Next.js (`web/components/risk-console/chat.tsx`, gọi qua `web/app/api/chat/route.ts`), mục "Cách hệ thống truy xuất" hiện cùng vết này.
- Mã: `RetrievalAgent.ask` trong [agents/retriever.py](../agents/retriever.py).
