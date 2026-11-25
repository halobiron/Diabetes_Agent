"use client";

import clsx from "clsx";
import { AlertTriangle, ArrowDown, ArrowRight, ArrowUp, Check, Copy } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { RISK_COLORS, RISK_LABELS } from "@/lib/labels";
import type { AssessmentChange, ChangeDirection, ChangeGroup, PredictionResult } from "@/types/healthcare";

import { CAST } from "./agents";

const GROUPS: { id: ChangeGroup; title: string; steady: string }[] = [
  { id: "habit", title: "Thói quen sinh hoạt", steady: "Thói quen giữ nguyên qua các lần" },
  { id: "body", title: "Chỉ số cơ thể", steady: "" },
  { id: "medical", title: "Sức khỏe & tiền sử", steady: "" },
  { id: "profile", title: "Thông tin chung", steady: "" },
];

const TONE: Record<ChangeDirection, { label: string; chip: string; text: string; Icon: typeof Check }> = {
  better: { label: "Tốt hơn", chip: "bg-[#dff1e6] text-[#146338] ring-1 ring-success/30", text: "text-success", Icon: Check },
  worse: { label: "Cần chú ý", chip: "bg-[#fbecd2] text-[#85500a] ring-1 ring-warning/35", text: "text-warning", Icon: AlertTriangle },
  neutral: { label: "Thay đổi", chip: "bg-canvas text-ink ring-1 ring-borderSoft", text: "text-ink", Icon: ArrowRight },
};

const TIME_ZONE = "Asia/Ho_Chi_Minh";
const NHO = CAST.nho;

function shortDate(iso: string) {
  return new Date(iso).toLocaleDateString("vi-VN", { timeZone: TIME_ZONE, day: "numeric", month: "numeric" });
}

function clock(iso: string) {
  return new Date(iso).toLocaleTimeString("vi-VN", { timeZone: TIME_ZONE, hour: "2-digit", minute: "2-digit" });
}

function fullDate(iso: string) {
  return new Date(iso).toLocaleString("vi-VN", { timeZone: TIME_ZONE, day: "numeric", month: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function gap(iso: string) {
  const days = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 86_400_000));
  return days === 0 ? "hôm nay" : `${days} ngày trước`;
}

function percent(value: number) {
  return `${new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 1, minimumFractionDigits: 1 }).format(value * 100)}%`;
}

function number(value: string | number) {
  return typeof value === "number" ? new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 2 }).format(value) : value;
}

type Cell = string | number | undefined;
type Column = {
  id: string;
  current: boolean;
  label: string;
  sub: string;
  title: string;
  risk: string;
  changes: AssessmentChange[] | null | undefined;
};
type Row = {
  field: string;
  label: string;
  unit: string | null;
  group: ChangeGroup;
  kind: "bool" | "number" | "text";
  values: Cell[];
  changes: (AssessmentChange | undefined)[];
  /** The yes/no answer that is favourable, inferred from the direction of any one change. */
  favourable?: string;
};

/** Rebuild each changed item's value for every assessment from the changes between neighbours. */
function buildRows(columns: Column[]): Row[] {
  const rows = new Map<string, Row>();
  columns.forEach((column, index) => {
    for (const change of column.changes ?? []) {
      let row = rows.get(change.field);
      if (!row) {
        row = {
          field: change.field,
          label: change.label ?? change.field,
          unit: change.unit,
          group: change.group ?? "profile",
          kind: typeof change.current === "number" ? "number" : change.current === "Có" || change.current === "Không" ? "bool" : "text",
          values: Array(columns.length).fill(undefined),
          changes: Array(columns.length).fill(undefined),
        };
        rows.set(change.field, row);
      }
      row.values[index] = change.current;
      row.values[index - 1] = change.previous;
      row.changes[index] = change;
      if (row.kind === "bool" && change.direction && change.direction !== "neutral") {
        row.favourable = change.direction === "better" ? String(change.current) : String(change.previous);
      }
    }
  });
  for (const row of rows.values()) {
    const first = row.values.findIndex((v) => v !== undefined);
    for (let i = 0; i < row.values.length; i += 1) {
      if (row.values[i] === undefined) row.values[i] = i < first ? row.values[first] : row.values[i - 1];
    }
  }
  return GROUPS.flatMap((group) => [...rows.values()].filter((row) => row.group === group.id));
}

function CopyId({ id }: { id: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(id);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      /* Clipboard can be blocked; the code stays selectable on screen. */
    }
  }
  return (
    <button
      type="button"
      onClick={copy}
      className="inline-flex min-h-11 items-center gap-1.5 rounded-lg px-3 text-sm font-semibold text-info transition-colors hover:bg-infoSoft"
    >
      {copied ? <Check aria-hidden="true" className="h-4 w-4" /> : <Copy aria-hidden="true" className="h-4 w-4" />}
      <span role="status">{copied ? "Đã chép mã" : "Chép mã"}</span>
    </button>
  );
}

function RiskTag({ risk, quiet = false }: { risk: string; quiet?: boolean }) {
  const color = RISK_COLORS[risk] ?? "#55527a";
  return (
    <span className={clsx("inline-flex items-center gap-1.5 whitespace-nowrap text-xs font-bold", quiet && "opacity-90")} style={{ color }}>
      <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full" style={{ background: color }} />
      {RISK_LABELS[risk] ?? risk}
    </span>
  );
}

function ValueCell({ row, index }: { row: Row; index: number }) {
  const value = row.values[index];
  if (value === undefined) return <span className="text-muted">—</span>;
  const change = row.changes[index];
  const previous = row.values[index - 1];

  if (!change) return <span className="text-sm text-muted tabular-nums">{number(value)}</span>;

  const direction = change.direction ?? "neutral";
  const { chip, Icon, label } = TONE[direction];
  const rises = typeof value === "number" && typeof previous === "number" && value > previous;
  const falls = typeof value === "number" && typeof previous === "number" && value < previous;
  const Glyph = rises ? ArrowUp : falls ? ArrowDown : Icon;
  return (
    <span className={clsx("inline-flex min-h-8 items-center gap-1 rounded-lg px-2 py-1 text-sm font-bold tabular-nums", chip)}>
      <Glyph aria-hidden="true" className="h-3.5 w-3.5 shrink-0" />
      {number(value)}
      <span className="sr-only">
        , {label}, trước đó {previous === undefined ? "chưa rõ" : number(previous)}
        {row.unit ? ` ${row.unit}` : ""}
      </span>
    </span>
  );
}

export function PatientHistory({ result }: { result: PredictionResult }) {
  const scroller = useRef<HTMLDivElement>(null);
  const memory = result.memory_context;
  const latestId = memory?.previous?.id;

  // On narrow screens the newest column ("Lần này") is the one that matters; start scrolled to it.
  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollLeft = el.scrollWidth;
  }, [latestId]);

  const previous = memory?.previous;
  const comparison = memory?.prediction_comparison;

  const header = (
    <section aria-labelledby="history-profile-title" className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
      <div className="min-w-0">
        <h3 id="history-profile-title" className="text-sm font-semibold text-muted">Mã hồ sơ</h3>
        <p className="break-all font-mono text-lg font-bold tracking-wide" style={{ color: NHO.ink }}>{result.patient_id}</p>
      </div>
      {result.patient_id ? <CopyId id={result.patient_id} /> : null}
    </section>
  );

  if (!memory || memory.status === "unavailable") {
    return (
      <div className="space-y-5">
        {header}
        <p role="status" className="rounded-xl bg-canvas px-4 py-3 text-sm leading-6 text-muted">
          Chưa tải được lịch sử. Thử lại sau để xem các lần đánh giá trước.
        </p>
      </div>
    );
  }

  const saveFailed = result.memory_saved === false;
  const alert = saveFailed ? (
    <p role="alert" className="rounded-xl bg-danger/5 p-3 text-sm text-danger">Chưa lưu được lượt này; lịch sử sẽ chưa có kết quả mới nhất.</p>
  ) : null;

  if (memory.status === "first_assessment" || !previous) {
    return (
      <div className="space-y-5">
        {header}
        {alert}
        <div className="rounded-2xl border border-dashed border-borderSoft p-5">
          <p className="text-base font-bold">Đây là lần đầu tiên của hồ sơ này.</p>
          <p className="mt-1 max-w-prose text-sm leading-6 text-muted">
            Lần sau, nhập lại bằng mã hồ sơ ở trên. Bà Nhớ sẽ chỉ ra thói quen và chỉ số nào bạn đã đổi, theo hướng tốt hơn hay cần chú ý.
          </p>
        </div>
      </div>
    );
  }

  const columns: Column[] = [
    ...memory.recent_assessments.slice().reverse().map((record): Column => ({
      id: record.id,
      current: false,
      label: shortDate(record.metadata.timestamp),
      sub: clock(record.metadata.timestamp),
      title: fullDate(record.metadata.timestamp),
      risk: record.metadata.risk,
      changes: record.changes,
    })),
    { id: "current", current: true, label: "Lần này", sub: "", title: "Lần đánh giá hiện tại", risk: result.risk, changes: memory.changes },
  ];
  const rows = buildRows(columns);
  const missingChanges = columns.slice(1, -1).some((column) => column.changes === undefined);

  const latest = memory.changes;
  const better = latest.filter((c) => c.direction === "better").length;
  const worse = latest.filter((c) => c.direction === "worse").length;
  const riskChanged = previous.metadata.risk !== result.risk;
  const habitRows = rows.filter((row) => row.group === "habit");

  return (
    <div className="space-y-6">
      {header}
      {alert}

      <section aria-labelledby="history-summary-title" className="space-y-2.5">
        <h3 id="history-summary-title" className="text-xl font-bold leading-snug text-balance">
          {latest.length
            ? `So với lần trước (${gap(previous.metadata.timestamp)}), bạn có ${latest.length} thay đổi`
            : `Không có gì thay đổi so với lần trước (${gap(previous.metadata.timestamp)})`}
        </h3>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
          {better ? <span className={clsx("inline-flex items-center gap-1 rounded-full px-2.5 py-1 font-semibold", TONE.better.chip)}><Check aria-hidden="true" className="h-3.5 w-3.5" />{better} tốt hơn</span> : null}
          {worse ? <span className={clsx("inline-flex items-center gap-1 rounded-full px-2.5 py-1 font-semibold", TONE.worse.chip)}><AlertTriangle aria-hidden="true" className="h-3.5 w-3.5" />{worse} cần chú ý</span> : null}
          <span className="inline-flex flex-wrap items-center gap-x-2 text-muted">
            Nguy cơ
            {riskChanged ? (
              <>
                <RiskTag risk={previous.metadata.risk} quiet />
                <ArrowRight aria-hidden="true" className="h-3.5 w-3.5" />
                <RiskTag risk={result.risk} />
              </>
            ) : (
              <>giữ ở mức <RiskTag risk={result.risk} /></>
            )}
          </span>
          {comparison?.probability_delta != null ? (
            <span className="tabular-nums text-muted">
              Xác suất {percent(comparison.previous_probability ?? 0)} <span aria-hidden="true">→</span><span className="sr-only">thành</span> <strong className="text-ink">{percent(comparison.current_probability)}</strong>
            </span>
          ) : null}
        </div>
      </section>

      <section aria-labelledby="history-table-title" className="space-y-2">
        <h3 id="history-table-title" className="text-base font-bold">Thói quen và chỉ số qua các lần</h3>
        {missingChanges ? (
          <p role="status" className="rounded-lg bg-warning/10 px-3 py-2 text-xs text-warning">
            Máy chủ chưa trả về thay đổi của các lần cũ. Hãy khởi động lại API để thấy đủ bảng.
          </p>
        ) : null}
        <div
          ref={scroller}
          role="region"
          aria-label="Bảng thay đổi qua các lần đánh giá; cuộn ngang nếu cần"
          tabIndex={0}
          className="overflow-x-auto rounded-2xl border border-borderSoft bg-panel"
        >
          <table className="w-full min-w-[34rem] border-separate border-spacing-0 text-left">
            <caption className="sr-only">
              Mỗi cột là một lần đánh giá từ cũ đến mới. Chỉ các mục từng thay đổi được liệt kê; ô được tô màu là lúc thay đổi xảy ra.
            </caption>
            <thead>
              <tr>
                <th scope="col" className="sticky left-0 z-10 min-w-[8.5rem] bg-panel px-3 py-3 text-xs font-semibold text-muted">Lần đánh giá</th>
                {columns.map((column) => (
                  <th
                    key={column.id}
                    scope="col"
                    title={column.title}
                    className={clsx("min-w-[4.75rem] px-2 py-3 text-center align-bottom", column.current && "bg-[#f6d8ea]/45")}
                  >
                    <span className={clsx("block text-sm font-bold tabular-nums", column.current && "text-[#8a2f6b]")}>{column.label}</span>
                    {column.sub ? <span className="block text-xs font-normal tabular-nums text-muted">{column.sub}</span> : null}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row" className="sticky left-0 z-10 border-t border-borderSoft bg-panel px-3 py-3 text-sm font-semibold">Mức nguy cơ</th>
                {columns.map((column) => (
                  <td key={column.id} className={clsx("border-t border-borderSoft px-2 py-3 text-center", column.current && "bg-[#f6d8ea]/45")}>
                    <RiskTag risk={column.risk} />
                  </td>
                ))}
              </tr>

              {GROUPS.map((group) => {
                const groupRows = rows.filter((row) => row.group === group.id);
                const showSteady = group.id === "habit" && habitRows.length === 0;
                if (!groupRows.length && !showSteady) return null;
                return (
                  <GroupRows key={group.id} title={group.title} colSpan={columns.length + 1}>
                    {showSteady ? (
                      <tr>
                        <td colSpan={columns.length + 1} className="px-3 py-3 text-sm text-muted">{group.steady}.</td>
                      </tr>
                    ) : null}
                    {groupRows.map((row) => (
                      <tr key={row.field}>
                        <th scope="row" className="sticky left-0 z-10 border-t border-borderSoft bg-panel px-3 py-2.5 text-sm font-medium">
                          {row.label}
                          {row.unit ? <span className="ml-1 text-xs font-normal text-muted">({row.unit})</span> : null}
                        </th>
                        {columns.map((column, index) => (
                          <td key={column.id} className={clsx("border-t border-borderSoft px-2 py-2.5 text-center", column.current && "bg-[#f6d8ea]/45")}>
                            <ValueCell row={row} index={index} />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </GroupRows>
                );
              })}
            </tbody>
          </table>
        </div>

        <ul className="flex flex-wrap gap-x-4 gap-y-1.5 pt-1 text-xs text-muted" aria-label="Chú giải">
          {(["better", "worse", "neutral"] as const).map((direction) => {
            const { Icon, label, chip } = TONE[direction];
            return (
              <li key={direction} className="inline-flex items-center gap-1.5">
                <span className={clsx("inline-flex h-5 w-5 items-center justify-center rounded-md", chip)}><Icon aria-hidden="true" className="h-3 w-3" /></span>
                {label}
              </li>
            );
          })}
          <li>Chữ mờ: giữ nguyên so với lần liền trước</li>
        </ul>
        <p className="text-xs leading-5 text-muted">
          “Tốt hơn” và “Cần chú ý” chỉ nói chiều thay đổi của yếu tố nguy cơ. Kết quả là ước tính của mô hình, chưa xác nhận chẩn đoán.
          {memory.assessment_count > memory.recent_assessments.length ? ` Bảng hiện ${memory.recent_assessments.length} lần gần nhất trong ${memory.assessment_count} lần.` : ""}
        </p>
      </section>
    </div>
  );
}

function GroupRows({ title, colSpan, children }: { title: string; colSpan: number; children: ReactNode }) {
  return (
    <>
      <tr>
        <th scope="colgroup" colSpan={colSpan} className="border-t border-borderSoft bg-canvas px-3 py-2 text-left text-sm font-bold">
          <span className="sticky left-3 inline-block">{title}</span>
        </th>
      </tr>
      {children}
    </>
  );
}
