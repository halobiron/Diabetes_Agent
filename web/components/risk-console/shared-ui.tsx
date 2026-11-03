import clsx from "clsx";
import type { ReactNode } from "react";

import { RISK_COLORS, RISK_LABELS } from "@/lib/labels";
import type { RiskLevel } from "@/types/healthcare";

export function MetricTile({
  label,
  value,
  icon,
  accent = "#5aa3d9",
}: {
  label: string;
  value: string;
  icon?: ReactNode;
  accent?: string;
}) {
  return (
    <div className="rounded-md border border-borderSoft bg-canvas/50 p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="field-label">{label}</div>
        <span style={{ color: accent }}>{icon}</span>
      </div>
      <div className="mt-2 text-2xl font-semibold tracking-tight">{value}</div>
    </div>
  );
}

export function RiskBadge({ risk, muted = false }: { risk: RiskLevel; muted?: boolean }) {
  const color = muted ? "#9aa4b2" : RISK_COLORS[risk];

  return (
    <span
      className="rounded-full border px-3 py-1.5 text-xs font-bold uppercase"
      style={{
        borderColor: `${color}66`,
        backgroundColor: `${color}1f`,
        color,
      }}
    >
      {muted ? "Chưa đánh giá" : (RISK_LABELS[risk] ?? risk)}
    </span>
  );
}

export function ProbabilityGauge({
  value,
  color,
  muted = false,
}: {
  value: number;
  color: string;
  muted?: boolean;
}) {
  const safeValue = Math.max(0, Math.min(100, value));

  return (
    <div className="mt-4">
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="field-label">Xác suất nguy cơ</span>
        <span className="text-sm font-semibold text-ink">{muted ? "—" : `${safeValue.toFixed(1)}%`}</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full border border-borderSoft bg-canvas">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${muted ? 0 : safeValue}%`, backgroundColor: color }}
        />
      </div>
      <div className="mt-2 flex justify-between text-[11px] text-muted">
        <span>0%</span>
        <span>50%</span>
        <span>100%</span>
      </div>
    </div>
  );
}

export function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-borderSoft bg-canvas/50 p-3">
      <div className="field-label">{label}</div>
      <div className="mt-1 text-lg font-semibold text-ink">{value}</div>
    </div>
  );
}

export function ModelItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="field-label">{label}</div>
      <div className="mt-1 truncate text-sm font-semibold text-ink" title={value}>
        {value}
      </div>
    </div>
  );
}

export function NarrativePanel({
  title,
  icon,
  text,
}: {
  title: string;
  icon: ReactNode;
  text: string;
}) {
  return (
    <div className="console-panel rounded-lg p-5">
      <PanelHeading icon={icon} title={title} />
      <p className="mt-4 whitespace-pre-line break-words text-sm leading-7 text-ink/90 [overflow-wrap:anywhere]">{text}</p>
    </div>
  );
}

export function PanelHeading({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-2 text-lg font-semibold">
      <span className="text-info">{icon}</span>
      {title}
    </div>
  );
}

export function Pill({ children, tone }: { children: ReactNode; tone: "neutral" }) {
  return (
    <span
      className={clsx(
        "shrink-0 whitespace-nowrap rounded-full border px-3 py-1 text-xs font-semibold",
        tone === "neutral" && "border-borderSoft bg-canvas/70 text-muted",
      )}
    >
      {children}
    </span>
  );
}

export function DataTable({
  rows,
  compact = false,
}: {
  rows: Array<Record<string, string | number>>;
  compact?: boolean;
}) {
  const columns = rows[0] ? Object.keys(rows[0]) : [];

  if (!rows.length) {
    return <p className="mt-4 text-sm text-muted">Chưa có dữ liệu.</p>;
  }

  return (
    <div className={clsx("overflow-hidden rounded-md border border-borderSoft", compact ? "mt-4" : "mt-4")}>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] border-collapse text-left text-sm">
          <thead className="bg-panelMuted text-xs uppercase tracking-[0.08em] text-muted">
            <tr>
              {columns.map((column) => (
                <th key={column} className="border-b border-borderSoft px-3 py-2 font-semibold">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={index} className="border-b border-borderSoft last:border-b-0">
                {columns.map((column) => (
                  <td key={column} className="px-3 py-2 text-ink/90">
                    {row[column]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
