# RAG truy xuất cơ sở tri thức như thế nào

Tài liệu này dùng để trả lời câu hỏi "RAG và KB liên quan với nhau ra sao" khi demo.

## 1. KB chứa gì

KB được xây từ 12 tài liệu y khoa tiếng Việt (Quyết định 3798/QĐ-BYT của Bộ Y tế, bản tóm tắt của WHO, 10 bài của Vinmec).

| Thành phần | Số lượng | Lưu ở đâu | Vai trò |
|---|---|---|---|
| Đoạn bằng chứng (`Evidence`) | 146 | Neo4j và Chroma | Văn bản gốc để trích dẫn |
| Thực thể (`Entity`) | 20 | Neo4j | Bệnh, yếu tố nguy cơ, xét nghiệm, can thiệp |
| Quan hệ | 35 | Neo4j | Nối thực thể với nhau, mỗi quan hệ trỏ về đoạn bằng chứng |
| Nguồn (`Source`) | 12 | Neo4j | Tên, nhà xuất bản, năm, đường dẫn |

Hai nơi lưu có hai việc khác nhau:
- **Chroma (vector):** tìm đoạn văn có nghĩa gần với câu hỏi.
- **Neo4j (đồ thị):** cho biết yếu tố nguy cơ nào dẫn tới can thiệp hay xét nghiệm nào, và đoạn bằng chứng nào chứng minh quan hệ đó.

## 2. Luồng truy xuất

```
Câu hỏi
  │ 1. nhúng bằng paraphrase-multilingual-MiniLM-L12-v2
  ▼
Chroma: độ tương đồng cosine với 146 đoạn
  │ 2. bỏ đoạn có điểm < 0.3 (ngoài chủ đề)
  ▼
Đoạn còn lại ──────────────┐
  │                        │ 3. nhận ra yếu tố nguy cơ trong câu hỏi
  │                        ▼    (BMI, huyết áp, hút thuốc, ...)
  │                  Neo4j: yếu tố → can thiệp/xét nghiệm → đoạn bằng chứng
  │                        │
  ▼                        ▼
4. đoạn có liên kết đồ thị được cộng 0.15 điểm
  ▼
5. xếp theo điểm cuối, lấy tối đa 5 đoạn
  ▼
6. ghép câu trả lời từ 3 đoạn đầu, đánh số [1] [2] [3] kèm nguồn
```

Nếu không có đoạn nào đạt ngưỡng 0.3, hệ thống từ chối trả lời thay vì bịa. Ví dụ "Cách nấu phở bò ngon" có điểm cao nhất chỉ 0.24 nên bị từ chối.

## 3. Ví dụ đã chạy thật

| Câu hỏi | Điểm cao nhất | Yếu tố nhận ra | Kết quả |
|---|---|---|---|
| Béo phì có làm tăng nguy cơ tiểu đường không? | 0.83 | BMI | Có trích dẫn, trong đó có đoạn BMI ≥ 23 của Bộ Y tế |
| Chẩn đoán đái tháo đường bằng xét nghiệm nào? | 0.83 | không | Trích đoạn về xét nghiệm đường huyết lúc đói, A1C |
| Hút thuốc lá ảnh hưởng thế nào? | 0.71 | Smoker | Đoạn "hút thuốc làm tăng nguy cơ kháng insulin" lên đầu |
| Cách nấu phở bò ngon | 0.24 | không | Từ chối |

## 4. Vì sao dùng cả vector lẫn đồ thị

- Chỉ dùng vector: tìm được đoạn "gần nghĩa" nhưng không biết đoạn nào là bằng chứng cho một quan hệ y khoa cụ thể.
- Thêm đồ thị: đoạn được chính quan hệ trong KB trích dẫn (ví dụ `Hút thuốc lá` → `Bỏ thuốc lá`) được ưu tiên, nên câu trả lời bám theo cấu trúc tri thức đã được kiểm duyệt.

## 5. Giới hạn cần nói thật khi bảo vệ

- Câu trả lời ghép từ các đoạn trích, không do LLM viết lại, nên đôi khi đoạn dài hoặc lẫn nội dung.
- Độ liên quan chỉ do embedding quyết định. Chưa có bộ câu hỏi đánh giá chính thức.
- KB nhỏ (12 nguồn), không thay thế tư vấn y tế.
- Ngưỡng BMI trong KB là 23 kg/m² theo Bộ Y tế. Các bài Vinmec còn nêu 25 và 35 cho các mục đích khác.

## 6. Cách chạy

- API: `POST /v1/chat` với `{"question": "..."}`. Kết quả gồm `answer`, `citations`, `status` và `trace` (các bước ở mục 2 kèm số liệu).
- Giao diện: panel **Hỏi đáp** trong giao diện Next.js (`web/components/risk-console/chat.tsx`, gọi qua `web/app/api/chat/route.ts`), mục "Cách hệ thống truy xuất" hiện cùng vết này.
- Mã: `RetrievalAgent.ask` trong [agents/retriever.py](../agents/retriever.py).
