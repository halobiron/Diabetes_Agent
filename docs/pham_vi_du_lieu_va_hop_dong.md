# Kết quả rà soát Bước 1

**Kết luận:** bài toán nhị phân và cấu trúc đa agent hiện có phù hợp để phát triển đồ án. Giữ các agent và Orchestrator; tiếp tục bổ sung những thành phần còn thiếu theo [kế hoạch](../KE_HOACH_HOAN_THIEN_DU_AN.md).

## Mục tiêu và dữ liệu

Hệ thống hỗ trợ đánh giá hồ sơ liên quan đến tiểu đường, giải thích dự đoán và đưa khuyến nghị có bằng chứng. Đối tượng là người dùng bản demo và người đánh giá đồ án; phạm vi là học tập, trình diễn.

Giữ bộ dữ liệu BRFSS với nhãn `Diabetes_binary`:

- `0`: nhóm không tiểu đường theo dữ liệu.
- `1`: nhóm tiền tiểu đường hoặc tiểu đường được gộp chung.

Nguồn định nghĩa: [Kaggle](https://www.kaggle.com/datasets/alexteboul/diabetes-health-indicators-dataset), [UCI](https://archive.ics.uci.edu/dataset/891/cdc+diabetes+health+indicators).

`probability` là xác suất ước tính cho nhóm `1`. Low/Medium/High là các khoảng điểm hiển thị, không phải ba giai đoạn bệnh. Nhãn hiện tại không xác định thời điểm phát bệnh tương lai.

## Đầu vào và phối hợp agent

- Đầu vào cần tuổi, huyết áp và BMI hoặc đủ chiều cao/cân nặng. Chiều cao tính bằng cm, cân nặng kg, huyết áp tâm thu mmHg và glucose mg/dL.
- Mô hình BRFSS dùng 21 đặc trưng; tuổi đổi thành nhóm, chiều cao/cân nặng dùng để tính BMI. Các trường tùy chọn còn thiếu đang được điền từ giá trị mặc định của mô hình.
- Glucose dùng cho cảnh báo/tư vấn và memory, không nằm trong 21 đặc trưng BRFSS. Luồng mô hình mẫu 12 dòng lại dùng glucose trực tiếp.

| Thành phần hiện có | Đầu vào chính → đầu ra |
| --- | --- |
| RetrievalAgent | Hồ sơ, mức nguy cơ, đặc trưng ảnh hưởng → kiến thức truy xuất. |
| ExplanationAgent | Hồ sơ, xác suất, đặc trưng ảnh hưởng, ca tương tự → giải thích. |
| RecommendationAgent | Hồ sơ, mức nguy cơ, kiến thức, ca tương tự, cảnh báo → khuyến nghị. |

Orchestrator gọi mô hình, điều phối các agent, áp dụng SafetyGuard và lưu kết quả qua MemoryAgent. Hiện ExplanationAgent chưa nhận kiến thức truy xuất; RecommendationAgent chưa nhận phần giải thích. Việc bổ sung các đường truyền này nằm ở Bước 10.

## Các vấn đề đã xác định

- Loader có thể chọn file nhãn không tương thích; mô hình/ngưỡng đang được chọn trên test; ánh xạ `bp → HighBP` cần đối chiếu dữ liệu nguồn.
- Bản đã kiểm tra thiếu artifact nên tự dùng mô hình mẫu 12 dòng.
- Chưa có mô hình dự đoán deep learning, KB Neo4j và policy RL; RAG và bộ luật cần hoàn thiện.
- Giải thích, điểm chất lượng dữ liệu và cách tìm ca tương tự cần chỉnh cho đúng ý nghĩa.

**Bước 1 đã hoàn thành phần rà soát.** Các việc sửa mã và kiểm thử được theo dõi trong kế hoạch.
