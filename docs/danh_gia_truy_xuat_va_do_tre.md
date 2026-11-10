# Đánh giá truy xuất RAG, ngưỡng liên quan và độ trễ

Kết quả đo ngày 09/11/2026 trên máy phát triển (Windows, CPU, không GPU), KB `corpus-2026-11-08` nạp trong Neo4j 5.26.32 (Docker). Số liệu thô: [retrieval_eval.json](retrieval_eval.json), [latency.json](latency.json). Chạy lại bằng hai lệnh ở cuối tài liệu.

## 1. Nạp lại KB vào Neo4j

`scripts/load_neo4j_kb.py` nạp 20 thực thể, 146 đoạn bằng chứng, 35 quan hệ, 12 nguồn: **178 nút, 181 quan hệ**. Demo tích hợp `scripts/demo_step12.py --require-neo4j` (không gồm phần web) đạt **16/16 ca** với `kb_source=KnowledgeGraph`; chế độ này dừng nếu hệ thống rơi về KB file. Kết quả rút gọn: [neo4j_verification.json](neo4j_verification.json). Số liệu này thay cho lần xác minh ngày 03/11 trên bản KB cũ (21 đoạn).

## 2. Bộ câu hỏi đánh giá và cách gán nhãn

Bộ câu hỏi: [data/eval/rag_retrieval_questions.json](../data/eval/rag_retrieval_questions.json), gồm 22 câu trong phạm vi, 8 câu ngoài phạm vi và 3 câu hỏi liều thuốc.

- **Căn cứ của nhãn.** Một đoạn KB được coi là liên quan khi văn bản của chính đoạn đó chứa dữ kiện trả lời (ví dụ "HbA1c ≥ 6,5%", "tuổi 45", "150 phút", "LDL < 100"), kiểm bằng biểu thức chính quy trên nội dung KB. Câu hỏi nào không có đoạn nào khớp thì script dừng, nên mọi câu đều có ít nhất một đoạn đáp án thật (từ 1 đến 21 đoạn mỗi câu). Hai câu hỏi (thận, hạ đường huyết) được viết lại vì KB không chứa đáp án đúng ý câu ban đầu (cách *phát hiện* bệnh thận; định nghĩa và nguyên nhân hạ đường huyết), và các biểu thức quá hẹp được nới sau khi đọc các đoạn bị xếp hạng đầu nhưng không khớp (ví dụ đoạn "bắt đầu ở tuổi 45" cho câu tầm soát).
- **Giới hạn.** Nhãn là xấp xỉ theo từ khóa: đoạn trả lời đúng nhưng không chứa từ khóa vẫn bị tính là không liên quan, nên **precision@3 là cận dưới**. Bộ câu hỏi nhỏ (30 câu) do nhóm tự soạn, chưa có chuyên gia y khoa duyệt; các con số dùng để so sánh ngưỡng và phát hiện điểm yếu, không phải đo chính xác chất lượng.
- 8 câu ngoài phạm vi gồm 6 câu hoàn toàn không liên quan và 2 câu gần chủ đề y khoa nhưng KB không có (cúm mùa, ung thư phổi).

## 3. Chất lượng truy xuất (22 câu trong phạm vi, top 3)

| Ngưỡng | hit@3 | precision@3 | recall@3 | MRR | Trả lời được câu trong phạm vi | Trả lời nhầm câu ngoài phạm vi |
|---|---|---|---|---|---|---|
| 0,30 (cũ) | 0,727 | 0,348 | 0,394 | 0,576 | 100% | 37,5% (3/8) |
| **0,40 (đã chọn cho chat)** | 0,727 | 0,348 | 0,394 | 0,576 | 100% | 25% (2/8) |
| 0,45 | 0,682 | 0,303 | 0,348 | 0,530 | 95,5% | 25% (2/8) |
| 0,50 | 0,682 | 0,303 | 0,348 | 0,530 | 95,5% | 0% |
| 0,55 | 0,682 | 0,303 | 0,348 | 0,530 | 86,4% | 0% |

`hit@3` là tỉ lệ câu có ít nhất một đoạn đáp án trong 3 đoạn đầu. Các ngưỡng 0,20 đến 0,35 cho kết quả giống 0,30 về chất lượng xếp hạng; khác biệt chỉ nằm ở việc có chịu trả lời câu ngoài phạm vi hay không.

**Điểm số cao nhất theo nhóm câu hỏi:**

- Câu ngoài phạm vi không liên quan: 0,09 đến 0,16, riêng "nấu phở bò" đạt **0,304**.
- Câu ngoài phạm vi gần chủ đề: cúm mùa 0,472, ung thư phổi 0,463.
- Câu trong phạm vi: thấp nhất là "tiểu đường type 1 khác type 2" 0,445; tiếp theo là câu về mắt 0,532 và bàn chân 0,533; còn lại từ 0,61 đến 0,85.

**Ngưỡng cho chat: 0,3 → 0,4** (`CHAT_MIN_RELEVANCE` trong `agents/retriever.py`).

- Ở 0,3, câu "nấu phở bò" (0,304) vẫn vượt ngưỡng và được trả lời bằng đoạn y khoa không liên quan. Các tài liệu trước đây ghi câu này bị từ chối với điểm 0,24; số đo hiện tại không khớp con số đó.
- 0,4 loại câu đó mà vẫn giữ cả 22 câu trong phạm vi.
- 0,5 loại cả hai câu gần chủ đề nhưng làm mất câu "type 1 khác type 2", là một câu hỏi rất thường gặp, và sát ngưỡng với hai câu hợp lệ khác (0,532, 0,533). Với mẫu nhỏ này, nhóm ưu tiên không từ chối câu hợp lệ.
- Hai câu gần chủ đề (cúm, ung thư phổi) vẫn lọt qua ở 0,4. Muốn chặn được cần thêm cơ chế khác (phân loại chủ đề hoặc LLM kiểm tra), không chỉ chỉnh ngưỡng; đây là hạn chế đã biết.

**Luồng đánh giá bệnh nhân giữ ngưỡng 0,3.** Truy vấn dựng từ hồ sơ bệnh nhân (4 hồ sơ thử) luôn cho 5 đoạn đầu có điểm từ 0,60 đến 0,74, nên ngưỡng 0,3 không phải yếu tố hạn chế ở luồng này.

**Điểm yếu tìm được.** hit@3 chỉ 72,7%. Các câu về huyết áp mục tiêu, LDL, chăm sóc bàn chân, tổn thương mắt và biểu hiện hạ đường huyết có 3 đoạn đầu là các đoạn chẩn đoán hoặc tiền đái tháo đường chung chung, trong khi đoạn đáp án nằm trong đoạn dài lẫn nhiều chủ đề của quyết định Bộ Y tế. Hướng cải thiện (chưa thực hiện, chưa thử nên chưa biết hiệu quả): chia đoạn nhỏ hơn theo chủ đề, hoặc xếp hạng lại bằng mô hình cross-encoder.

**Chặn liều thuốc.** Cả 3 câu hỏi về liều (insulin, metformin) không trả về đoạn nào có liều: 0 đoạn bị lọt trong số 17 đoạn bị giữ lại.

## 4. Độ trễ (API chạy trong tiến trình, KB từ Neo4j)

Mỗi hồ sơ gửi 10 lần sau 1 lần khởi động (40 yêu cầu `/v1/predict`), mỗi câu hỏi gửi 10 lần (30 yêu cầu `/v1/chat`). Đo thời gian toàn bộ yêu cầu phía client, không gồm mạng.

| Đường | Trung bình | Trung vị | p95 | Lớn nhất |
|---|---|---|---|---|
| `/v1/predict` | 247,9 ms | 262,8 ms | 290,4 ms | 584,0 ms |
| `/v1/chat` | 22,3 ms | 22,1 ms | 25,8 ms | 27,1 ms |

- **Lần đầu sau khi khởi động:** yêu cầu `/v1/predict` đầu tiên mất **12,8 giây**, vì phải chờ agent khởi tạo xong (tải mô hình nhúng, nạp KB, đánh chỉ mục). Chỉ xảy ra một lần mỗi tiến trình.
- **Trung bình theo hồ sơ:** thiếu glucose 268 ms, nguy cơ thấp 260 ms, nguy cơ cao 308 ms, glucose cao 156 ms. Hồ sơ glucose cao nhanh hơn vì luồng chuyển bác sĩ bỏ qua mô phỏng what-if.
- **Theo thành phần** (`trace.steps`, trung bình): giải thích đặc trưng (độ nhạy) 107 ms, mô phỏng what-if 82 ms (chỉ ca khám định kỳ), truy xuất RAG 30 ms, lưu memory 14 ms, mô hình MLP 6 ms, tìm hồ sơ tương tự 3 ms; luật an toàn, policy, khuyến nghị và giải thích dưới 1 ms vì đang dùng văn bản dự phòng (không có khóa LLM).
- **Hạn chế.** Không có LLM nên chưa phản ánh độ trễ khi gọi OpenAI; chạy một tiến trình, một máy, tuần tự, không phải kiểm thử tải.

## 5. Chạy lại

```bash
# Cần Neo4j đang chạy và biến môi trường từ .env; thêm --kb file để dùng KB file
python scripts/evaluate_retrieval.py --kb neo4j --output logs/retrieval-eval.json
python scripts/measure_latency.py --repeats 10 --output logs/latency.json
```
