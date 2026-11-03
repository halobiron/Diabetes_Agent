import { Activity, ExternalLink } from "lucide-react";

import type { MeasurementBand, MeasurementScale } from "@/types/healthcare";

const tones: Record<MeasurementBand["tone"], string> = {
  neutral: "#9aa4b2", success: "#2f9b6a", warning: "#d49a35", danger: "#d05245",
};

function position(value: number, scale: MeasurementScale) {
  return Math.max(0, Math.min(100, (value - scale.display_min) / (scale.display_max - scale.display_min) * 100));
}

export function MeasurementScales({ scales }: { scales: MeasurementScale[] }) {
  if (!scales.length) return null;
  return (
    <section aria-labelledby="measurement-heading" className="console-panel min-w-0 rounded-lg p-5">
      <h2 id="measurement-heading" className="flex items-center gap-2 text-sm font-semibold">
        <Activity aria-hidden="true" className="h-4 w-4 text-info" /> Chỉ số của bạn trên thang tham khảo
      </h2>
      <p className="mt-2 text-sm leading-6 text-muted">Vị trí của số đo hiện tại, tách biệt với xác suất mô hình. Chọn một vùng để xem mốc cụ thể.</p>
      <div className="mt-5 grid min-w-0 gap-6 lg:grid-cols-3">
        {scales.map((scale) => <Scale key={scale.key} scale={scale} />)}
      </div>
    </section>
  );
}

function Scale({ scale }: { scale: MeasurementScale }) {
  const outside = scale.value !== null && (scale.value < scale.display_min || scale.value > scale.display_max);
  return (
    <article className="min-w-0" aria-label={scale.title}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold">{scale.title}</h3>
        <span className="text-sm tabular-nums">{scale.value ?? "Chưa đo"} <span className="text-xs text-muted">{scale.value !== null ? scale.unit : ""}</span></span>
      </div>
      <p className="mt-1 min-h-10 text-xs leading-5 text-muted">{scale.status}</p>
      <div
        role="img"
        aria-label={`${scale.title}: ${scale.value === null ? "chưa đo" : `${scale.value} ${scale.unit}`}. ${scale.status}. ${outside ? "Giá trị nằm ngoài khoảng hiển thị." : ""}`}
        className="relative mt-3 h-5 rounded-sm bg-panelMuted"
      >
        <div className="absolute inset-0 flex overflow-hidden rounded-sm" aria-hidden="true">
          {scale.bands.map((band) => {
            const left = position(band.min ?? scale.display_min, scale);
            const right = position(band.max ?? scale.display_max, scale);
            return <span key={band.label} style={{ width: `${right - left}%`, background: tones[band.tone] }} className="h-full border-r border-canvas/60 last:border-r-0" />;
          })}
        </div>
        {scale.value !== null ? <span aria-hidden="true" style={{ left: `${position(scale.value, scale)}%` }} className="absolute -top-1 h-7 w-1 -translate-x-1/2 rounded-sm border border-canvas bg-ink" /> : null}
      </div>
      <div className="mt-2 flex justify-between text-xs tabular-nums text-muted"><span>{scale.display_min}</span><span>{scale.display_max} {scale.unit}</span></div>
      {outside ? <p className="mt-2 text-xs text-ink">{scale.value} {scale.unit} nằm ngoài khoảng hiển thị; dấu đánh dấu được giữ ở mép thang.</p> : null}
      <div className="mt-3 space-y-1">
        {scale.bands.map((band) => (
          <details key={band.label} className="text-xs text-muted">
            <summary className="cursor-pointer rounded py-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-info">
              <span aria-hidden="true" className="mr-2 inline-block h-2 w-2 rounded-sm" style={{ background: tones[band.tone] }} />{band.label}
              {scale.key === "bmi" ? <span className="ml-2 inline-block tabular-nums text-ink">{band.min === null ? `< ${band.max}` : band.max === null ? `≥ ${band.min}` : `${band.min} – < ${band.max}`}</span> : null}
            </summary>
            <p className="pb-2 pl-4 leading-5">{band.min === null ? `Dưới ${band.max}` : band.max === null ? `Từ ${band.min} trở lên` : `Từ ${band.min} đến dưới ${band.max}`} {scale.unit}. Đây là mốc tham khảo, không phải kết luận chẩn đoán.</p>
          </details>
        ))}
      </div>
      <p className="mt-3 text-xs leading-5 text-muted">{scale.note}</p>
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-2">
        {scale.sources.map((source) => <a key={source.url} href={source.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-info underline underline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-info">{source.title}<ExternalLink aria-hidden="true" className="h-3 w-3" /><span className="sr-only"> (mở tab mới)</span></a>)}
      </div>
    </article>
  );
}
