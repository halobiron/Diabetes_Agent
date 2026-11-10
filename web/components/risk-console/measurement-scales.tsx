import { ExternalLink } from "lucide-react";

import type { MeasurementBand, MeasurementScale } from "@/types/healthcare";

const tones: Record<MeasurementBand["tone"], string> = {
  neutral: "#6f6c8f", success: "#1b7a4b", warning: "#c98a1a", danger: "#c4452f",
};

function position(value: number, scale: MeasurementScale) {
  return Math.max(0, Math.min(100, (value - scale.display_min) / (scale.display_max - scale.display_min) * 100));
}

function bandRange(band: MeasurementBand) {
  return band.min === null ? `< ${band.max}` : band.max === null ? `≥ ${band.min}` : `${band.min}–${band.max}`;
}

export function MeasurementScales({ scales }: { scales: MeasurementScale[] }) {
  const shown = scales;
  if (!shown.length) return null;
  return (
    <section aria-labelledby="measurement-heading" className="min-w-0">
      <h2 id="measurement-heading" className="text-sm font-bold">Chỉ số của bạn trên thang tham khảo</h2>
      <p className="mt-1 text-xs leading-5 text-muted">Vị trí số đo hiện tại, tách biệt với xác suất của mô hình. Mốc chỉ để tham khảo, không phải kết luận chẩn đoán.</p>
      <div className="mt-4 grid min-w-0 gap-6 md:grid-cols-2">
        {shown.map((scale) => <Scale key={scale.key} scale={scale} />)}
      </div>
    </section>
  );
}

function Scale({ scale }: { scale: MeasurementScale }) {
  const outside = scale.value !== null && (scale.value < scale.display_min || scale.value > scale.display_max);
  return (
    <article className="min-w-0" aria-label={scale.title}>
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold">{scale.title}</h3>
        <span className="text-lg font-bold tabular-nums">{scale.value ?? "Chưa đo"} <span className="text-xs font-normal text-muted">{scale.value !== null ? scale.unit : ""}</span></span>
      </div>
      <p className="mt-0.5 text-xs leading-5 text-muted">{scale.status}</p>
      <div
        role="img"
        aria-label={`${scale.title}: ${scale.value === null ? "chưa đo" : `${scale.value} ${scale.unit}`}. ${scale.status}. ${outside ? "Giá trị nằm ngoài khoảng hiển thị." : ""}`}
        className="relative mt-3 h-4 rounded-sm bg-panelMuted"
      >
        <div className="absolute inset-0 flex overflow-hidden rounded-sm" aria-hidden="true">
          {scale.bands.map((band) => {
            const left = position(band.min ?? scale.display_min, scale);
            const right = position(band.max ?? scale.display_max, scale);
            return <span key={band.label} style={{ width: `${right - left}%`, background: tones[band.tone] }} className="h-full border-r border-white/60 last:border-r-0" />;
          })}
        </div>
        {scale.value !== null ? <span aria-hidden="true" style={{ left: `${position(scale.value, scale)}%` }} className="absolute -top-1 h-6 w-1 -translate-x-1/2 rounded-sm border border-white bg-ink" /> : null}
      </div>
      <div className="mt-1 flex justify-between text-xs tabular-nums text-muted"><span>{scale.display_min}</span><span>{scale.display_max} {scale.unit}</span></div>
      {outside ? <p className="mt-1 text-xs text-ink">Ngoài khoảng hiển thị; dấu được giữ ở mép thang.</p> : null}
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        {scale.bands.map((band) => (
          <li key={band.label} className="flex items-center gap-1.5">
            <span aria-hidden="true" className="inline-block h-2 w-2 rounded-sm" style={{ background: tones[band.tone] }} />
            {band.label} <span className="tabular-nums text-ink">{bandRange(band)}</span>
          </li>
        ))}
      </ul>
      <details className="mt-2 text-xs text-muted">
        <summary className="w-fit cursor-pointer py-1 underline-offset-4 hover:underline">Ghi chú và nguồn</summary>
        <p className="mt-1 leading-5">{scale.note}</p>
        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
          {scale.sources.map((source) => <a key={source.url} href={source.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-info underline underline-offset-4">{source.title}<ExternalLink aria-hidden="true" className="h-3 w-3" /><span className="sr-only"> (mở tab mới)</span></a>)}
        </div>
      </details>
    </article>
  );
}
