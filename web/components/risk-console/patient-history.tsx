"use client";

import type { PredictionResult } from "@/types/healthcare";

const LABELS: Record<string, string> = {
  age: "Tuổi", bmi: "BMI", bp: "Huyết áp tâm thu", height_cm: "Chiều cao", weight_kg: "Cân nặng",
};

function dateTime(value: string) {
  return new Date(value).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" });
}

export function PatientHistory({ result }: { result: PredictionResult }) {
  const memory = result.memory_context;
  const comparison = memory?.prediction_comparison;
  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-lg font-bold">Mã hồ sơ của bạn</h3>
        <p className="mt-2 break-all text-base font-semibold text-info">{result.patient_id}</p>
        <p className="mt-2 text-sm text-muted">Lưu lại mã này và nhập lại khi đánh giá lần sau. Chỉ những lần dùng cùng mã mới được so sánh.</p>
      </div>
      {result.memory_saved === false ? <p role="alert" className="text-sm font-semibold text-danger">Chưa lưu được lần đánh giá này. Bạn vẫn có thể xem kết quả; hãy thử lại khi dịch vụ lưu trữ hoạt động.</p> : null}
      {memory?.status === "unavailable" ? (
        <p role="status">Chưa đọc được lịch sử. Hãy thử lại sau; hiện chưa có dữ liệu để so sánh.</p>
      ) : memory?.status === "first_assessment" ? (
        <p>Đây là lần đánh giá đầu tiên được ghi nhận cho mã hồ sơ này. Khi đánh giá lại với cùng mã, bạn sẽ thấy thay đổi tại đây.</p>
      ) : memory?.previous ? (
        <>
          <div>
            <h3 className="text-lg font-bold">So với lần gần nhất</h3>
            <p className="mt-1 text-sm text-muted">{dateTime(memory.previous.metadata.timestamp)} · {memory.assessment_count} lần đánh giá trước</p>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-sm tabular-nums">
                <caption className="sr-only">Thay đổi số đo so với lần đánh giá gần nhất</caption>
                <thead><tr className="border-b border-borderSoft"><th scope="col" className="py-3 pr-3">Chỉ số</th><th scope="col" className="py-3 pr-3">Lần trước</th><th scope="col" className="py-3 pr-3">Hiện tại</th><th scope="col" className="py-3">Thay đổi</th></tr></thead>
                <tbody>{memory.changes.map((change) => (
                  <tr key={change.field} className="border-b border-borderSoft">
                    <th scope="row" className="py-3 pr-3 font-medium">{LABELS[change.field] ?? change.field}<span className="block text-xs font-normal text-muted">{change.unit}</span></th>
                    <td className="py-3 pr-3">{change.previous}</td><td className="py-3 pr-3">{change.current}</td>
                    <td className="py-3">{change.delta === 0 ? "Không đổi" : `${change.delta > 0 ? "+" : ""}${change.delta}`}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </div>
          {comparison ? <div className="space-y-2 text-sm">
            {comparison.probability_delta !== null ? <p className="font-semibold">Xác suất mô hình thay đổi {comparison.probability_delta > 0 ? "+" : ""}{(comparison.probability_delta * 100).toFixed(2)} điểm phần trăm.</p> : null}
            <p className="text-muted">{comparison.note}</p>
          </div> : null}
          <details>
            <summary className="min-h-11 cursor-pointer py-3 font-semibold text-info">{memory.recent_assessments.length} lần đánh giá trước gần nhất</summary>
            <ol className="divide-y divide-borderSoft">{memory.recent_assessments.map((record) => (
              <li key={record.id} className="py-3 text-sm"><time dateTime={record.metadata.timestamp} className="font-semibold">{dateTime(record.metadata.timestamp)}</time><p className="mt-1 text-muted">BMI {record.metadata.bmi} · Huyết áp tâm thu {record.metadata.bp} mmHg</p></li>
            ))}</ol>
          </details>
          <p className="text-sm text-muted">Kết quả lưu là dự đoán của mô hình, chưa phải kết quả bệnh được xác nhận. Chênh lệch số đo hoặc dự đoán không tự xác nhận bệnh cải thiện hay tiến triển.</p>
        </>
      ) : null}
    </div>
  );
}
