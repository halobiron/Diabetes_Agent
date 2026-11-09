# Policy Reinforcement Learning: chọn bước hỗ trợ tiếp theo

Mã nguồn: [rl/environment.py](../rl/environment.py), [rl/policy.py](../rl/policy.py), huấn luyện bằng [scripts/train_support_policy.py](../scripts/train_support_policy.py), tích hợp tại `Orchestrator._choose_next_step`. Kiểm thử: [tests/test_rl.py](../tests/test_rl.py).

## Phản hồi là mô phỏng

Dự án không có phản hồi thật từ bệnh nhân hay bác sĩ. Môi trường, tỉ lệ bệnh nhân cung cấp glucose, khả năng tìm kiếm mở rộng cải thiện bằng chứng và các giá trị reward đều là giả định do nhóm đặt ra, ghi trong `rl/environment.py`. Kết quả dưới đây chỉ cho biết các chiến lược khác nhau ra sao dưới các giả định đó, không phải hiệu quả trên bệnh nhân thật.

## State, action, reward

- **State** (Orchestrator quan sát được): mức rủi ro (Low/Medium/High); glucose (chưa đo / bình thường / ≥ 200 mg/dL); `evidence_status` (none/limited/sufficient); đã hỏi glucose chưa; đã tìm mở rộng chưa. Tổng cộng 108 trạng thái.
- **Action**: `request_glucose`, `retrieve_more_evidence` (hai bước thu thập, mỗi bước tối đa một lần), và ba bước kết thúc `recommend_routine`, `recommend_followup`, `escalate_to_clinician`.
- **Reward**: bước thu thập −0,05, cộng thêm `0,3 ×` mức giảm entropy (bit) của niềm tin "bệnh nhân có cần chuyển tuyến không". Hỏi glucose mà bệnh nhân cung cấp thì xóa được độ bất định này (nhiều nhất với nhóm Medium chưa đo glucose); với nhóm High độ bất định đã bằng 0 nên không được thưởng. Tìm thêm bằng chứng không đổi niềm tin nên không có thưởng entropy. Ý tưởng reward theo entropy reduction mượn từ các agent chẩn đoán phân cấp, ở đây áp dụng trên một bệnh. Bước kết thúc: +1 nếu đúng mức cần (cần chuyển tuyến nếu glucose thật ≥ 200 hoặc rủi ro High; theo dõi nếu Medium; thường quy nếu Low); sai mức thì phạt, phạt nặng nhất khi bỏ sót ca cần chuyển tuyến (−2), nhẹ khi chuyển tuyến thừa (−0,4 đến −0,8). Lời khuyên không chuyển tuyến được +0,2 nếu bằng chứng đủ, −0,2 nếu không có bằng chứng.
- **Thuật toán**: Q-learning dạng bảng, 60.000 episode, ε giảm dần, không cần thư viện RL thêm. Policy lưu ở `artifacts/support_policy.json`.

## State Tracker

`rl/state_tracker.py` gom trạng thái policy quan sát được (mức rủi ro, glucose, bằng chứng, các bước đã làm) và tính entropy còn lại. Orchestrator dùng nó thay cho đoạn tự ghép trạng thái; ảnh chụp của tracker trả về trong `policy.state_tracker`.

## So sánh (20.000 episode đánh giá, mô phỏng)

| Chiến lược | Reward TB (±95% CI) | Số bước TB | Bỏ sót ca cần chuyển tuyến | Chuyển tuyến thừa |
|---|---|---|---|---|
| Q-learning | 1,005 ± 0,006 | 1,69 | 0,95% | 2,83% |
| Bảng kiểm cố định (luôn hỏi glucose, tìm thêm, rồi theo mức rủi ro) | 0,997 ± 0,007 | 2,10 | 2,34% | 0% |
| Chỉ theo mức rủi ro (quy trình hiện tại) | 0,803 ± 0,011 | 1,00 | 7,42% | 0% |
| Ngẫu nhiên | −0,354 ± 0,016 | 1,28 | 26,5% | 20,1% |

Q-learning và bảng kiểm cố định chênh nhau trong khoảng sai số, nên không thể nói RL tốt hơn bảng kiểm. Cả hai vượt rõ quy trình chỉ theo rủi ro. Policy học được dùng ít bước hơn và bỏ sót ít hơn, đổi lại chuyển tuyến thừa nhiều hơn. Kết quả này phụ thuộc vào ma trận reward.

## Tích hợp vào Orchestrator

Sau lượt xử lý đầu, Orchestrator dựng state và hỏi policy (tối đa 3 bước):

- `retrieve_more_evidence`: thực sự chạy lại RetrievalAgent với `broaden=True` (thêm một truy vấn hướng dẫn chung, lấy điểm tốt nhất của mỗi đoạn, tối đa 5 đoạn), rồi tính lại bằng chứng, luật an toàn và khuyến nghị. Khả năng việc này nâng `evidence_status` trong thực tế chưa được đo; mô phỏng giả định 60%.
- `request_glucose`: một lời gọi API không hỏi lại được bệnh nhân nên chỉ trả về làm `policy.next_step`.
- Bước kết thúc: trả về làm `policy.next_step`; nội dung khuyến nghị vẫn do luật và RecommendationAgent tạo.
- **Luật có quyền ưu tiên**: nếu policy chọn mức thấp hơn mà luật đã chuyển tuyến, `next_step` bị thay bằng `escalate_to_clinician` và `overridden_by_rules = true`. Policy không thay đổi `safety`.

Khối `policy` trong kết quả gồm `next_step`, `steps`, `q_values`, `version`, `feedback` ("simulated"). Không có file policy thì Orchestrator chạy như trước và `policy` là `null`.

Huấn luyện lại: `python scripts/train_support_policy.py`.
