# Bộ luật an toàn và xử lý xung đột

Mã nguồn: [tools/rules.py](../tools/rules.py); `SafetyGuard` ([tools/safety.py](../tools/safety.py)) gọi `RuleEngine`, Orchestrator chuyển kết quả cho RecommendationAgent. Kiểm thử: [tests/test_rules.py](../tests/test_rules.py).

Mỗi luật có mã, tên, nhóm, mức ưu tiên (số lớn hơn = quan trọng hơn, quyết định thứ tự cảnh báo), điều kiện, thông điệp, mức chuyển tuyến (`escalation`) và căn cứ. Các ngưỡng là ngưỡng của dự án, có đối chiếu với khuyến cáo ACC/AHA và ADA; chưa được bác sĩ thẩm định.

## Luật cơ sở

| Mã | Ưu tiên | Điều kiện | Chuyển tuyến |
|---|---|---|---|
| GLU-300 | 100 | Glucose đo được ≥ 300 mg/dL | urgent_clinician_review |
| BP-180 | 95 | Huyết áp tâm thu ≥ 180 | urgent_clinician_review |
| GLU-200 | 80 | Glucose đo được 200–299 | prompt_clinician_followup |
| BP-160 | 75 | Huyết áp tâm thu 160–179 | prompt_clinician_followup |
| PRED-VERYHIGH | 60 | Mức High và xác suất ≥ 0,85 | prompt_clinician_followup |
| DQ-GLU-MISSING | 45 | Không đo glucose | (chỉ cảnh báo) |

Luật glucose chỉ áp dụng cho giá trị đo thật, không dùng giá trị trung vị được điền thay thế.

## Luật xung đột

Chạy sau luật cơ sở, nhìn vào sự bất đồng giữa dự đoán, số đo và bằng chứng.

| Mã | Ưu tiên | Xung đột | Cách giải quyết |
|---|---|---|---|
| CF-PRED-LOW-MEASURED-HIGH | 85 | Mô hình Low nhưng có số đo nguy hiểm | `measurement_overrides_prediction`: số đo thắng; `effective_risk` = High |
| CF-PRED-HIGH-GLUCOSE-NORMAL | 55 | Mô hình High nhưng glucose đo bình thường (< 100) | `prediction_kept_confirm_with_a1c`: giữ High, đề nghị A1C |
| CF-PRED-LOW-GLUCOSE-MISSING | 50 | Mô hình Low nhưng không đo glucose | `prediction_unconfirmed_testing_advised`: không coi là yên tâm |
| CF-PRED-HIGH-LOW-QUALITY | 40 | Mô hình High nhưng dữ liệu đầu vào chất lượng thấp | `prediction_kept_marked_provisional` |
| CF-ESCALATION-NO-EVIDENCE | 30 | Có chuyển tuyến nhưng bằng chứng truy xuất `none`/`limited` | `escalation_kept_evidence_limited` |

## Chính sách giải quyết

1. Số đo lâm sàng (huyết áp, glucose) thắng dự đoán thống kê: khuyến nghị được viết theo `safety.effective_risk`, còn `risk` và `prediction` vẫn là kết quả gốc của mô hình.
2. `escalation` là mức nặng nhất trong các luật đã kích hoạt; không có gì hạ mức này, kể cả dự đoán thấp hay thiếu bằng chứng.
3. Mọi xung đột đều được báo cáo kèm cách giải quyết, không bị ẩn.

## Đầu ra

`safety` giữ các trường cũ (`alerts`, `escalation`, `confidence_*`, `disclaimers`) và thêm `rules` (luật cơ sở đã kích hoạt), `conflicts` (xung đột kèm `resolution`), `effective_risk`. `alerts` là thông điệp của mọi luật đã kích hoạt, xếp theo ưu tiên.
