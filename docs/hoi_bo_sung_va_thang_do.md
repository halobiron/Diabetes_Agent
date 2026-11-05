# Hỏi bổ sung và thang tham khảo chỉ số

## Quyết định sau nghiên cứu

Chọn bổ sung câu hỏi tiếp theo và thang chỉ số vào trang Đánh giá. (Mô phỏng
"nếu thay đổi" được thêm sau, xem mục cuối.) Cách này giải quyết trực tiếp hai nhu cầu:
hiểu số đo đang nằm ở đâu và bổ sung thông tin còn thiếu. Đây là lựa chọn dựa
trên phạm vi dự án và nguồn tham khảo; chưa phải kết luận từ thử nghiệm so sánh
UX với người dùng thực.

Ba giới hạn chi phối thiết kế:

- NIDDK phân biệt glucose lúc đói, ngẫu nhiên và OGTT. Vì vậy thang glucose
  chỉ có các vùng tham khảo khi người dùng xác nhận lúc đói ít nhất 8 giờ;
  sau ăn thông thường không được coi là OGTT. Bối cảnh khác giữ thang trung tính.
- AHA cần xét cả tâm thu và tâm trương để phân loại huyết áp. Dự án chỉ nhận
  tâm thu, nên các vùng ghi số tâm thu, không kết luận huyết áp bình thường.
- CDC áp dụng BMI người lớn cho tuổi từ 20. Dưới 20 chỉ hiện giá trị, không
  phân vùng theo thang người lớn.

Thang tham khảo không phải mục tiêu điều trị cá nhân hoặc ngưỡng xác suất MLP.
Phạm vi glucose lúc đói ghi rõ người lớn không mang thai. Một số đo hoặc số đo
máy tại nhà không được dùng như kết luận chẩn đoán.

## Hành vi đã triển khai

1. API nhận thêm `glucose_context`: unspecified, fasting, random, after_meal,
   unknown; và `glucose_unavailable` để ghi nhận người dùng chưa có số đo.
2. Orchestrator trả `measurement_scales` gồm giá trị thật, vùng, đơn vị,
   giới hạn hiển thị, ghi chú phạm vi và nguồn. Glucose thiếu trả `value=null`.
3. Hệ thống trả tối đa một `followup`: hỏi số đo khi thiếu, hoặc một mục có/không còn thiếu (xem mục cuối).
   Bối cảnh đo do sidebar thu thập cùng giá trị, không hỏi lại sau khi gửi. Khi policy chọn request_glucose, nguồn là policy; khi câu hỏi đến
   từ kiểm tra thiếu dữ liệu, nguồn ghi data_quality. Không gán mọi câu hỏi cho RL.
4. Người dùng bổ sung ngay trong trang kết quả. Frontend gửi lại hồ sơ đã được
   đánh giá cùng câu trả lời, tránh vô tình trộn thay đổi chưa gửi ở sidebar.
   API chạy lại dự đoán, luật, RAG, khuyến nghị và memory.
5. Chọn chưa có số đo đặt glucose_unavailable=true; policy nhận asked_glucose=true,
   không chọn hỏi glucose lặp. Chọn không nhớ bối cảnh lưu unknown và giữ thang
   trung tính. Trạng thái này đi cùng hồ sơ hiện tại, không phải hồ sơ bệnh án lâu dài.
6. Khi luật yêu cầu bác sĩ đánh giá, không đưa câu hỏi nhập dữ liệu lên trước.
7. Sau cập nhật, giao diện cho xem xác suất trước/sau, số cảnh báo, số đoạn bằng
   chứng và hướng xử trí mới. Glucose không tham gia MLP BRFSS nên xác suất có
   thể giữ nguyên dù cảnh báo, bằng chứng và lời khuyên được tính lại.
8. Mỗi vùng có nhãn chữ, có thể mở bằng bàn phím để xem mốc. Giá trị ngoài miền
   hiển thị được ghi rõ và giữ marker ở mép, không sửa số đo. Bật ô nhập glucose
   không tự tạo số đo 110 như trước.

Mã chính: `tools/patient_guidance.py`, `agents/orchestrator.py`,
`web/components/risk-console/measurement-scales.tsx`,
`web/components/risk-console/next-question.tsx` và `web/components/risk-console.tsx`.
Các ngưỡng cảnh báo trong bộ luật hiện có không được thay bằng mốc tham khảo UI.
Policy vẫn là Q-learning huấn luyện trên môi trường mô phỏng; lần này bổ sung
luồng trả lời và cập nhật thực, không huấn luyện lại policy bằng dữ liệu người dùng.

## Câu hỏi theo mức ảnh hưởng, mô phỏng "nếu thay đổi" và chuỗi bằng chứng

- **Câu hỏi tiếp theo** (`tools/what_if.py`, `tools/patient_guidance.py`): thứ tự là
  glucose còn thiếu (chi phối bộ luật), rồi mục có/không còn thiếu mà câu trả lời
  làm xác suất MLP đổi nhiều nhất (chênh lệch tối thiểu 2 điểm %), 
  Mục đã trả lời hoặc đã bấm "Bỏ qua" (`skipped_fields`) không bị hỏi lại. Hồ sơ nguy
  cơ thấp mà không mục nào đạt ngưỡng thì không hỏi thêm.
- **Nếu thay đổi thì sao** (`what_if` trong kết quả): chạy lại mô hình cho từng thay đổi
  (giảm 5% cân nặng, vận động, bỏ thuốc, huyết áp dưới 130) và cho tất cả cùng lúc.
  Chỉ mô phỏng khi người dùng đã cung cấp giá trị hiện tại; không giả định thói quen
  bị bỏ trống. Thay đổi không làm giảm nguy cơ thì không hiển thị. Mỗi kịch bản kèm
  nguồn từ KB. Đây là liên quan thống kê, không phải hiệu quả nhân quả. Bị ẩn khi luật
  yêu cầu bác sĩ đánh giá.
- **Chuỗi bằng chứng** (`evidence_trail`): với mỗi yếu tố làm tăng nguy cơ do người dùng
  cung cấp, liệt kê các đoạn bằng chứng đã truy xuất mà đồ thị tri thức nối với yếu tố đó
  (`factors` trên từng đoạn, lấy từ `factor_key` của truy vấn đồ thị). Yếu tố không có
  đoạn liên kết được ghi rõ là chưa có bằng chứng.
- **Quan sát agent** (`trace`, tab "Quan sát agent"): mỗi bước của orchestrator ghi tên,
  thời gian (ms), kết quả (ok/dự phòng) và chi tiết (số đoạn bằng chứng, số luật kích
  hoạt...). Kèm tổng thời gian, số đoạn bằng chứng, và `disagreement` khi luật trên số đo
  thực tế nâng nguy cơ cao hơn mô hình. Bước lỗi hiển thị cơ chế dự phòng đã dùng.
- Giao diện: các mục có/không dùng ba trạng thái Chưa rõ / Không / Có; "Chưa rõ" không gửi
  giá trị để agent có thể hỏi sau.

## Nguồn đối chiếu ngày 03/11/2026

- [NIDDK — Diabetes Tests & Diagnosis](https://www.niddk.nih.gov/health-information/diabetes/overview/tests-diagnosis): bối cảnh đo, nhịn ăn và xét nghiệm xác nhận.
- [CDC — Adult BMI Calculator](https://www.cdc.gov/bmi/adult-calculator/index.html): các nhóm BMI và giới hạn từ 20 tuổi.
- [AHA — Understanding Blood Pressure Readings](https://www.heart.org/en/health-topics/high-blood-pressure/understanding-blood-pressure-readings): tâm thu/tâm trương và các mốc tham khảo.
- [CDC — Low Blood Sugar](https://www.cdc.gov/diabetes/about/low-blood-sugar-hypoglycemia.html): tránh tô vùng dưới 70 mg/dL thành bình thường.
- [W3C — Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html): truyền đạt thông tin bằng nhãn, không chỉ bằng màu.

## Kiểm tra

- Backend: 119 tests đạt, gồm mốc biên BMI/glucose, tuổi ngoài phạm vi, không vẽ
  số đo tự điền, từ chối không hỏi lặp, ưu tiên chuyển bác sĩ và bổ sung glucose
  không đổi xác suất MLP. Chạy bằng `python -m pytest -q` trong Docker Linux.
- Frontend: lint, typecheck và production build đạt trong image kiểm thử.
- Kiểm tra thiết kế tự động Impeccable trên các component thay đổi không có phát hiện.
- Trình duyệt thật trên desktop 1440px và mobile 390px: chọn bối cảnh, giữ thang
  trung tính khi không nhớ, hỏi số đo thiếu, cập nhật, lỗi mạng/thử lại, từ chối
  không hỏi lặp và không tự điền glucose đều đạt; không tràn ngang, không có lỗi
  JavaScript. Kết quả: [followup_verification.json](followup_verification.json).
- Ảnh phiên bản đã chạy: [desktop](media/screenshots/followup-assessment.png),
  [mobile](media/screenshots/followup-mobile.png). Bản demo cục bộ đã được cập nhật
  tại http://localhost:3000; API tại http://localhost:18000.
