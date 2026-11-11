# Đánh giá truy xuất RAG, ngưỡng liên quan và độ trễ

Kết quả đo ngày 09/11/2026 trên máy phát triển (Windows, CPU, không GPU), KB `corpus-2026-11-08` nạp trong Neo4j 5.26.32 (Docker). Số liệu thô: [retrieval_eval.json](retrieval_eval.json) (chạy lại ngày 11/11/2026 với bge-m3 và 28 câu, khớp mục 3c), [latency.json](latency.json). **Từ ngày 11/11/2026 model nhúng mặc định là `BAAI/bge-m3`** (mục 3c); số đo ở mục 3, 3b và 4 là của model cũ `paraphrase-multilingual-MiniLM-L12-v2`. Chạy lại bằng hai lệnh ở cuối tài liệu.

## 1. Nạp lại KB vào Neo4j

Lần đo ngày 09/11/2026, Neo4j chứa 20 thực thể, 146 đoạn bằng chứng, 35 quan hệ, 12 nguồn: **178 nút, 181 quan hệ**. Demo tích hợp `scripts/demo_step12.py --require-neo4j` (không gồm phần web) đạt **16/16 ca** với `kb_source=KnowledgeGraph`. Kết quả rút gọn: [neo4j_verification.json](neo4j_verification.json). Số liệu này thay cho lần xác minh ngày 03/11 trên bản KB cũ (21 đoạn).

## 2. Bộ câu hỏi đánh giá và cách gán nhãn

Bộ câu hỏi: [data/eval/rag_retrieval_questions.json](../data/eval/rag_retrieval_questions.json), gồm 28 câu trong phạm vi, 8 câu ngoài phạm vi và 3 câu hỏi liều thuốc. Số đo ở mục 3 (ngày 09/11) dùng 22 câu đầu (q01–q22); 6 câu q23–q28 về yếu tố nguy cơ được thêm ngày 11/11/2026, xem mục 3b.

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

## 3b. Cập nhật 11/11/2026: định tuyến đồ thị theo ý định câu hỏi

**Lỗi phát hiện.** Câu "Béo phì ảnh hưởng đến nguy cơ tiểu đường thế nào?" được trả lời bằng đoạn *điều trị* ("Quản lý bệnh tiểu đường type 2 bao gồm: giảm cân…") và đoạn *xét nghiệm*, còn đoạn giải thích "càng có nhiều mô mỡ… tế bào càng trở nên đề kháng với insulin" có trong KB nhưng không lên top 3. Có ba nguyên nhân:

1. Chat chỉ đi theo quan hệ `ADDRESSES`/`SHOULD_TEST_WITH` (can thiệp, xét nghiệm) và bỏ qua `INCREASES_RISK_OF`, đúng loại quan hệ mà câu hỏi "ảnh hưởng thế nào" cần.
2. Mức cộng 0.15 lớn hơn khoảng cách điểm cosine giữa 10 đoạn đầu (khoảng 0.05), nên mọi đoạn có liên kết đồ thị đều vượt lên trên đoạn khớp nghĩa nhất.
3. Đoạn trích lấy 320 ký tự đầu, nên phần trả lời nằm giữa đoạn bị cắt mất.

**Thay đổi** (`agents/retriever.py`, chỉ áp dụng cho chat; luồng bệnh nhân giữ nguyên):

- Nhận ý định bằng từ khóa: câu hỏi nguy cơ đi theo `INCREASES_RISK_OF`, câu hỏi hành động đi theo can thiệp/xét nghiệm, không rõ thì dùng cả hai.
- Mức cộng của chat là `ASK_GRAPH_BOOST = 0.05`.
- Đoạn trích chọn các câu gần câu hỏi nhất. Với câu hỏi nguy cơ, câu trả lời mở đầu bằng quan hệ đồ thị, ví dụ "Thừa cân hoặc béo phì làm tăng nguy cơ tiền đái tháo đường [1]". Câu này chỉ xuất hiện khi đoạn bằng chứng của quan hệ nằm trong các đoạn được hiển thị, và đoạn trích đó được chấm điểm theo cả mệnh đề này nên luôn hiện câu chứng minh.

**Chọn mức cộng.** Đã quét 0; 0,02; 0,03; 0,05; 0,08 và 0,15. Từ 0,05 trở lên, precision trên các câu nguy cơ tăng rõ. Ở 0,15, đoạn "Lười vận động: càng ít vận động, nguy cơ… càng cao" bị đẩy khỏi top 3 của câu hỏi về ít vận động, vì các đoạn có liên kết nhưng kém liên quan hơn chiếm chỗ; 0,05 giữ được đoạn này.

**Kết quả (28 câu, top 3, cùng bộ câu hỏi, chạy `scripts/evaluate_retrieval.py` trên mã cũ và mã mới):**

| Ngưỡng | hit@3 | precision@3 | recall@3 | MRR | Trả lời nhầm câu ngoài phạm vi |
|---|---|---|---|---|---|
| **0,40 (chat)** trước | 0,750 | 0,333 | 0,369 | 0,589 | 25% (2/8) |
| **0,40 (chat)** sau | **0,786** | **0,429** | **0,464** | **0,655** | 25% (2/8) |
| 0,50 trước | 0,714 | 0,298 | 0,333 | 0,554 | 0% |
| 0,50 sau | 0,750 | 0,405 | 0,440 | 0,619 | 0% |

- **Theo từng câu ở ngưỡng 0,40:** 7 câu tốt hơn (q01, q03, q15, q23, q24, q25, q28), 20 câu không đổi. Riêng q07 có đoạn khớp nhãn tụt từ hạng 1 xuống hạng 2; đoạn mới lên hạng 1 ("Giảm từ 5–10% lượng chất béo trong cơ thể…") cũng trả lời đúng nhưng không chứa từ "cân nặng" mà nhãn yêu cầu.
- Ngưỡng từ chối và việc chặn liều thuốc không đổi: 0/17 đoạn có liều bị lọt.
- **Độ trễ của `ask()`** (đo trực tiếp, không qua HTTP): khoảng 13 ms khi đã cache, bằng mức cũ. Lần đầu một đoạn được hiển thị mất thêm 15–50 ms để nhúng các câu của đoạn đó; kết quả được cache theo đoạn trong suốt vòng đời tiến trình.
- **Hạn chế còn lại.** Mô hình nhúng vẫn xếp một số đoạn chung chung ("Đái tháo đường là bệnh rối loạn chuyển hóa…") vào top 3. `Tiền sử gia đình` không có `key` trong KB (mô hình rủi ro không có đặc trưng này), nên câu hỏi về gia đình chỉ dùng tìm kiếm ngữ nghĩa. Nhận ý định bằng từ khóa có thể nhận sai câu hỏi diễn đạt lạ.

## 3c. Cập nhật 11/11/2026: mô hình bge-m3 và alias trong KB

**Câu hỏi.** Sau mục 3b, chat nhận ra yếu tố nguy cơ bằng danh sách từ khóa viết cứng trong code (`QUESTION_FACTORS`), nên các cách nói như "mập", "bố mẹ tôi bị tiểu đường", "ngồi một chỗ" bị bỏ sót, và "tiền sử gia đình" không bao giờ được nhận ra vì yếu tố này không có `key`. Đã thử hai hướng thay thế và chấm cả hai trên cùng thước đo.

**Bộ kiểm tra độc lập.** [data/eval/chat_heldout_questions.json](../data/eval/chat_heldout_questions.json) gồm 40 câu (30 câu nhắc một trong 7 yếu tố nguy cơ, 10 câu không nhắc). Bộ này do một agent riêng viết mà không đọc mã nguồn, KB hay alias. Danh sách alias được viết **trước** khi đọc bộ này và không được chỉnh theo nó.

**1. Nhận ra yếu tố nguy cơ trong câu hỏi (40 câu độc lập):**

| Cách | Tìm đúng yếu tố | Khớp hoàn toàn | Ghi chú |
|---|---|---|---|
| Từ khóa trong code (cũ) | 14/30 | 21/40 | |
| Embedding (so câu hỏi với tên + mô tả yếu tố), MiniLM / e5-small / e5-base / bge-m3 | | tốt nhất 22/40 | Kể cả khi chọn ngưỡng ngay trên bộ kiểm tra (lạc quan); yếu tố gần nhất chỉ đúng 14–16/30 câu, vì chủ đề chung "tiểu đường" lấn át |
| **Tên + `aliases` của RiskFactor trong Neo4j (mới)** | **22/30** | **25/40** | Đổi lại, 8/40 câu bị nhận thêm một yếu tố thừa (chủ yếu do nhắc tuổi, ví dụ "con tôi 15 tuổi") |

Chọn quan hệ đồ thị bằng embedding (so câu hỏi với mệnh đề như "Thừa cân làm tăng nguy cơ…", "Giảm cân giúp kiểm soát thừa cân") đạt 14/17 câu, còn từ khóa ý định trong code đạt 15/17, nên phần ý định giữ nguyên từ khóa.

**2. Model nhúng cho truy xuất đoạn** (28 câu có nhãn, chỉ xếp hạng ngữ nghĩa):

| Model | hit@3 | P@3 | MRR | Từ chối câu ngoài phạm vi khi vẫn trả lời đủ 28 câu | Khoảng cách (câu trong phạm vi thấp nhất − câu ngoài phạm vi cao nhất) |
|---|---|---|---|---|---|
| MiniLM (cũ) | 0,750 | 0,369 | 0,595 | 6/8 | −0,027 |
| multilingual-e5-small | 0,929 | 0,512 | 0,726 | 7/8 | −0,012 |
| multilingual-e5-base | 0,857 | 0,440 | 0,720 | 8/8 | 0,007 |
| **bge-m3** | 0,893 | **0,524** | 0,720 | **8/8** | **0,091** |

bge-m3 được chọn vì precision cao nhất và là model duy nhất có khoảng cách rõ giữa câu trong và ngoài phạm vi, nên ngưỡng từ chối không đặt sát mép.

**Hiệu chỉnh ngưỡng cho bge-m3** (hằng số đầu `agents/retriever.py`; mỗi ngưỡng giữ đúng vai trò của nó ở model cũ):

- Sàn chat **0,55**: câu ngoài phạm vi gần chủ đề cao nhất 0,522; câu trong phạm vi thấp nhất 0,613.
- Sàn luồng bệnh nhân **0,5**: câu không liên quan cao nhất 0,451; 129 truy vấn dựng từ hồ sơ có đoạn thứ 5 thấp nhất 0,699.
- Ngưỡng bằng chứng "mạnh" **0,6**, cộng điểm đồ thị cho chat **0,03**, chọn bằng cách quét 0; 0,02; 0,03; 0,05 và 0,08.

**Kết quả toàn hệ thống trên 28 câu** (`scripts/evaluate_retrieval.py`, ngưỡng chat):

| | hit@3 | P@3 | R@3 | MRR | Trả lời nhầm câu ngoài phạm vi |
|---|---|---|---|---|---|
| MiniLM + từ khóa, ngưỡng 0,40 (sau mục 3b) | 0,786 | 0,429 | 0,464 | 0,655 | 25% (2/8) |
| **bge-m3 + alias, ngưỡng 0,55** | **0,929** | **0,560** | **0,631** | **0,756** | **0%** |

Ngưỡng và mức cộng được chọn trên chính 28 câu này, nên số liệu có thể hơi lạc quan. Vì vậy đã chấm thêm trên bộ độc lập.

**Chấm mù trên 40 câu độc lập.** Top 3 đoạn của cả hai hệ thống được trộn và xáo ngẫu nhiên (195 cặp câu–đoạn). Một agent riêng chấm 0/1/2 (0 = lạc đề, 1 = liên quan một phần, 2 = trả lời trực tiếp) mà không biết đoạn nào thuộc hệ thống nào:

| | Câu có đoạn trả lời trực tiếp trong top 3 | Điểm TB đoạn hạng 1 | Điểm TB mọi đoạn hiển thị |
|---|---|---|---|
| MiniLM + từ khóa | 16/40 | 0,90 | 0,67 |
| **bge-m3 + alias** | **28/40** | **1,40** | **1,11** |

So từng câu: 15 câu tốt hơn, 1 câu kém hơn, 24 câu hoà. Mỗi hệ thống từ chối nhầm 1 câu: câu về vị trí tiêm insulin, nội dung KB không có.

**Chi phí** (máy phát triển; sentence-transformers tự chạy trên GPU RTX 5060 Ti khi có CUDA, nên các số này là số đo trên GPU):

- RAM đỉnh khi nạp model: 1,7 GB → **3,4 GB**. Trọng số: 0,46 GB → 2,3 GB.
- Khởi động (nạp model + dựng chỉ mục): 10 s → 14 s.
- Độ trễ `ask()`: xem mục 3d. Số đo độ trễ dao động đáng kể giữa các lần chạy trên máy này, nên chỉ so sánh các phép đo chạy cùng lúc.

**Dữ liệu KB.** 7 thực thể `RiskFactor` có thêm thuộc tính `aliases` (artifacts/kb_diabet.cypher: 7 dòng đổi, số nút và quan hệ giữ nguyên 178/181). `scripts/collect_corpus.py` lấy lại thực thể từ Neo4j nên alias được giữ khi thu thập lại corpus.

## 3d. Cập nhật 11/11/2026: GPU, CUDA graph, bỏ Chroma ở truy xuất, thử reranker

**Reranker (không dùng).** Đã thử chấm lại 10 đoạn đầu bằng cross-encoder `BAAI/bge-reranker-v2-m3`:

- Trên 28 câu có nhãn, hit@3 tăng từ 0,929 lên 1,000 và MRR từ 0,756 lên 0,857.
- Trên 40 câu độc lập chấm mù, một người chấm chấm lại cả hai hệ thống trong cùng một lượt (160 cặp xáo ngẫu nhiên): số câu có đoạn trả lời trực tiếp trong top 3 là **26/40 ở cả hai**, điểm TB đoạn hạng 1 giảm từ 1,32 xuống 1,20–1,25, so từng câu tốt hơn 4 và kém hơn 5–6.
- Mức tăng trên bộ có nhãn vì vậy nhiều khả năng đến từ nhãn từ khóa, không phải chất lượng thật.
- Reranker còn thêm 40–80 ms trên GPU (fp16) và khoảng 4,9 s trên CPU cho 10 đoạn, nên không dùng được trên App Runner.

**Bỏ Chroma ở RetrievalAgent.** KB chỉ có 146 đoạn, nên chỉ mục giờ là một ma trận numpy dựng lúc khởi động; tìm kiếm mất 0,15 ms. Không còn tham số `chroma_path`, tên collection theo hash hay logic dựng lại chỉ mục. MemoryAgent vẫn dùng Chroma để lưu hồ sơ ca bệnh lâu dài.

**fp16 và CUDA graph** (`tools/semantic_embeddings.py`; CUDA graph đã gỡ sau đó, xem cuối mục):

- Khi có CUDA, model chạy fp16. Chỉ số trên 28 câu giữ nguyên (MRR 0,756 → 0,768), ngưỡng không cần đổi (câu ngoài phạm vi cao nhất 0,522, câu trong phạm vi thấp nhất 0,613).
- Phân tích một lần `ask()`: 35 trong 41 ms là bước nhúng câu hỏi; tìm kiếm 0,15 ms; mỗi truy vấn Neo4j 2–3 ms.
- Nhúng 1 câu là việc nhỏ, GPU gần như rảnh và thời gian nằm ở việc khởi chạy hàng trăm kernel (khoảng 30 ms trên Windows). CUDA graph phát lại toàn bộ kernel một lần: **35 ms → 6–8 ms** mỗi câu hỏi, vector khớp với encode thường (cosine thấp nhất 0,99977 trên 40 câu độc lập).
- Graph được kiểm tra với encode thường ngay khi capture. Câu dài hơn 128 token, máy không có GPU, hoặc capture lỗi thì dùng encode thường. Có khoá để các request đồng thời không ghi đè buffer của nhau (kiểm tra 8 luồng song song).

**Độ trễ `ask()`**, 40 câu độc lập, cache đã ấm. Bật/tắt graph xen kẽ trong cùng một khoảng thời gian:

| | Lần 1 | Lần 2 |
|---|---|---|
| Không graph | 39,7 ms (p95 57,9) | 17,9 ms (p95 27,0) |
| **Có graph** | **12,1 ms (p95 15,4)** | **11,1 ms (p95 14,1)** |

**Cập nhật: đã gỡ CUDA graph.** Đo lại sau khi code chat đã gọn (bỏ nhận ý định và câu mở đầu, mục 3e–3f), xen kẽ 2 lượt, 120 lần hỏi mỗi lượt:

| | Lượt 1 | Lượt 2 |
|---|---|---|
| Không graph | 19,2 ms (p90 23,4) | 19,0 ms (p90 21,5) |
| Có graph | 12,5 ms (p90 14,5) | 11,9 ms (p90 13,1) |

Graph chỉ nhanh hơn khoảng 7 ms mỗi câu. Người dùng không nhận ra mức đó, và bản deploy (CPU) không dùng tới graph. Đổi lại, nó cần khoảng 60 dòng code (capture, kiểm tra với encode, buffer cố định, khoá luồng) và một file test riêng. Vì vậy `tools/semantic_embeddings.py` giờ chỉ gọi `encode` (fp16 trên GPU). Lần đo đầu (39,7 ms) chậm hơn vì cache vector câu chưa đầy hết.

**Deploy.**

- App Runner không có GPU, nên bge-m3 chạy CPU, khoảng 70 ms mỗi câu hỏi.
- Instance API được đặt **2 vCPU / 4 GB** (`api_cpu`, `api_memory` trong `infra/aws/apprunner`); 2 GB mặc định không đủ.
- Model được tải sẵn vào image Docker (`HF_HOME=/opt/hf`), nên lúc khởi động không cần mạng để tải 2,3 GB.

## 3e. Cập nhật 11/11/2026: bỏ bước nhận ý định câu hỏi

**Câu hỏi.** Từ mục 3b, chat chọn loại liên kết đồ thị theo ý định câu hỏi: hỏi nguy cơ thì đi theo `INCREASES_RISK_OF`, hỏi nên làm gì thì đi theo can thiệp/xét nghiệm. Ý định được nhận ra bằng hai danh sách từ khóa viết cứng (`RISK_INTENT`, `ACTION_INTENT`). Phép so sánh ở mục 3c (15/17 so với 14/17) dùng model cũ và 17 câu do chính người viết từ khóa gán nhãn, nên không khách quan.

**Đo lại trên 30 câu độc lập có nhãn `intent`** (bge-m3):

| Cách nhận ý định | Đúng | Không quyết được (dùng cả hai) | Sai |
|---|---|---|---|
| Từ khóa | 19 | 10 | 1 |
| So câu hỏi với mệnh đề quan hệ trong đồ thị | 21 | 0 | 9 |
| So câu hỏi với 4 câu mẫu ý định (viết trước khi chấm) | **28** | 0 | 2 |

**Nhưng nhận ý định đúng hơn không làm câu trả lời tốt hơn.** Kết quả toàn hệ thống, với ba người chấm mù (mức đồng thuận trên các cặp đối chứng: 8/10 và 8/10):

| | Câu có đoạn trả lời trực tiếp (40 câu độc lập) | Điểm TB mọi đoạn | hit@3 / P@3 / MRR (28 câu) |
|---|---|---|---|
| Từ khóa | 26/40 | 1,130 | 0,929 / 0,560 / 0,768 |
| 5 câu mẫu (thêm một câu kiểu chẩn đoán sau khi thấy q02–q04 sai) | 24/40 | 1,122 | 0,893 / 0,548 / 0,750 |
| **Không nhận ý định, luôn dùng cả hai loại liên kết** | 24/40 | **1,148** | **0,929** / 0,536 / **0,786** |

- Chênh lệch giữa ba cách chỉ 2 câu, trong khi hai người chấm khác nhau ở 2/10 cặp đối chứng, nên không phân định được cách nào tốt hơn.
- Khi từ khóa không chắc, nó dùng cả hai loại liên kết; hoá ra đây là lựa chọn an toàn. Chọn đúng một nhánh đôi khi bỏ mất liên kết hữu ích. Ví dụ câu chẩn đoán "Tiền đái tháo đường được xác định khi đường huyết đói ở mức nào?" có đáp án nằm trên liên kết *xét nghiệm*, nhưng được xếp vào nhóm "nguy cơ".
- Thiệt hại thật của cách mới: với câu "Người tăng huyết áp nên làm gì…", liên kết nguy cơ kéo một đoạn không liên quan lên thay cho đoạn về tập thể dục.

**Quyết định:** bỏ bước nhận ý định. Chất lượng ngang các cách khác, MRR cao nhất, và code không còn từ khóa hay câu mẫu nào viết cứng.

## 3f. Cập nhật 11/11/2026: chấm mù toàn văn câu trả lời

Các mục trên chỉ chấm việc chọn đoạn, không chấm phần chữ mà người dùng đọc. Phần này chấm thẳng phần chữ đó.

**Cách chấm.** Với 40 câu độc lập, sinh câu trả lời theo 3 phiên bản. Cả 3 dùng cùng các đoạn đã chọn, chỉ khác cách trình bày:

- **A:** trích câu gần câu hỏi + câu mở đầu nêu quan hệ nguy cơ, ví dụ "Thừa cân hoặc béo phì làm tăng nguy cơ… [1]".
- **B:** chỉ trích câu.
- **C:** cắt 320 ký tự đầu mỗi đoạn, như bản gốc.

Một agent chấm 0–3 cho từng câu trả lời. Agent không biết phiên bản nào là phiên bản nào: thứ tự X/Y/Z được xáo theo từng câu, và các câu trả lời giống hệt nhau đều được cho cùng điểm. Không gọi OpenAI hay LLM nào khác ở bước sinh câu trả lời.

| | Điểm TB | Câu được 3 điểm | Câu ≤ 1 điểm |
|---|---|---|---|
| A (trích câu + câu mở đầu) | 2,42 | 22 | 5 |
| **B (chỉ trích câu)** | **2,52** | **25** | **4** |
| C (cắt đầu đoạn, bản gốc) | 2,25 | 18 | 8 |

- Trích câu có ích: B tốt hơn C ở 11 câu, kém hơn ở 2 câu.
- Câu mở đầu gây hại: trên 16 câu có câu mở đầu, A kém hơn B ở 5 câu và tốt hơn ở 1 câu. Cả 5 câu bị hại đều là câu hỏi "nên làm gì" hoặc "có cần đi khám không", nhưng câu mở đầu lại nói về nguy cơ.

**Quyết định:** giữ trích câu, bỏ câu mở đầu và 4 hàm phục vụ nó. Liên kết "làm tăng nguy cơ" vẫn được dùng để xếp hạng đoạn.

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
# Cần Neo4j đang chạy, đã có dữ liệu và biến môi trường từ .env
python scripts/evaluate_retrieval.py --output logs/retrieval-eval.json
python scripts/measure_latency.py --repeats 10 --output logs/latency.json
```
