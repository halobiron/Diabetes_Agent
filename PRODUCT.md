# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Người dùng phổ thông và sinh viên/giảng viên xem demo: nhập hồ sơ sức khỏe cơ bản, đọc kết quả nguy cơ tiểu đường kèm giải thích. (Suy luận từ mã nguồn và README; chưa phỏng vấn.)

## Product Purpose
Nguyên mẫu học tập: mô hình MLP dự đoán nguy cơ tiểu đường (BRFSS), giải thích đặc trưng, truy xuất bằng chứng, luật an toàn, agent hỏi thêm. Không phải thiết bị y tế, không thay tư vấn y tế.

## Capabilities and Constraints
- Giao diện hoàn toàn tiếng Việt; giữ nguyên API /api/predict, /api/history, /api/health.
- Giữ mọi chức năng: nhập liệu (có "Chưa rõ"), đường huyết tùy chọn + bối cảnh, câu hỏi bổ sung, thang tham khảo, what-if, bằng chứng, vết agent.
- Stack: Next.js 15, React 19, Tailwind 3, Recharts, lucide-react.

## Brand Commitments
Người dùng chọn hướng: sáng, dịu, kiểu phòng khám; luồng từng bước (wizard) rồi kết quả toàn trang.

## Product Principles
- Rõ ràng trước, trang trí sau; mỗi màn hình một việc chính.
- Không bao giờ nói quá: luôn phân biệt xác suất mô hình với số đo thực tế.
- Dữ liệu thiếu là trạng thái bình thường ("Chưa rõ"), không phải lỗi.

## Accessibility & Inclusion
Tương phản WCAG AA, thao tác bằng bàn phím, cỡ chữ đủ lớn cho người lớn tuổi.
