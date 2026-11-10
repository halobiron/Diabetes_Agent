"use client";

import clsx from "clsx";
import { AlertTriangle, Check, ChevronDown, ListChecks, ShieldCheck } from "lucide-react";
import { useMemo, useState, type KeyboardEvent, type ReactNode } from "react";

import { ESCALATION_LABELS, featureLabel, formatFeatureValue, METHOD_LABELS } from "@/lib/labels";
import type { EvidenceTrailItem, MeasurementScale, PredictionResult } from "@/types/healthcare";

import { AgentTrace } from "./agent-trace";
import { Avatar, Bubble, CAST, useInView, type CastId } from "./agents";
import { ChatPanel } from "./chat";
import { CitationLink } from "./citation";
import { InputScoreDetails } from "./input-review";
import { KbPanel } from "./kb-explorer";
import { MeasurementScales } from "./measurement-scales";
import { ModelStrip } from "./model-strip";
import { WhatIf } from "./what-if";

const SENTENCE_SPLIT = /(?<=[.!?])\s+(?=[A-ZÀ-Ỹ])/;

const ESCALATION_TITLE = {
  routine_followup: "Cần lưu ý",
  prompt_clinician_followup: "Nên đi khám sớm",
  urgent_clinician_review: "Cần được khám khẩn",
} as const;

const RULE_SCALE: Record<string, string> = { BP: "bp" };

type EvidenceItem = { text: string; n: number; source?: { title: string; url?: string } };

/**
 * The backend writes: actions, "Bằng chứng hướng dẫn:" then "<passage> [n]" pairs
 * (the marker FOLLOWS its passage), then a "[n] Title - url" source list.
 */
function parseRecommendation(text: string) {
  const lines = text.split(/\n+/).map((line) => line.trim()).filter(Boolean);
  const sourceStart = lines.findIndex((l) => /^nguồn/i.test(l) || /^\[\d+\]\s.*https?:\/\//.test(l));
  const body = (sourceStart === -1 ? lines : lines.slice(0, sourceStart)).join(" ");
  const sourceMap = new Map<number, { title: string; url?: string }>();
  for (const line of sourceStart === -1 ? [] : lines.slice(sourceStart)) {
    const m = /^\[(\d+)\]\s*(.*?)(?:\s+-\s+(https?:\/\/\S+))?$/.exec(line);
    if (m) sourceMap.set(Number(m[1]), { title: m[2], url: m[3] });
  }

  const label = /bằng chứng hướng dẫn\s*:/i.exec(body);
  const before = label ? body.slice(0, label.index) : body;
  const after = label ? body.slice(label.index + label[0].length) : "";
  const actions = before.split(SENTENCE_SPLIT).map((x) => x.trim()).filter(Boolean);

  const evidence: EvidenceItem[] = [];
  let end = 0;
  for (const m of after.matchAll(/([\s\S]+?)\s*\[(\d+)\]/g)) {
    const n = Number(m[2]);
    evidence.push({ text: m[1].trim(), n, source: sourceMap.get(n) });
    end = (m.index ?? 0) + m[0].length;
  }
  const note = after.slice(end).trim();
  return { actions, evidence, note };
}

type TabId = "explain" | "evidence" | "kb" | "safety" | "whatif" | "ask" | "tech";
type TabMeta = { id: TabId; label: string; cast: CastId; count?: number; alert?: boolean; intro: string };

/**
 * Phần thân trang kết quả: cột chính có các tab (mỗi tab một chủ đề, không cuộn dài),
 * cột phụ luôn thấy "Việc nên làm". Cảnh báo an toàn chỉ hiện thành một dải khi có số đo nguy hiểm.
 */
export function Assessment({ result, scales }: { result: PredictionResult; scales: MeasurementScale[] }) {
  const { actions, evidence, note } = parseRecommendation(result.recommendation);
  const urgent = result.safety.alerts.length > 0;

  const tabs: TabMeta[] = [
    { id: "explain", label: "Vì sao", cast: "mo", intro: "Các yếu tố khiến mô hình ra kết quả này." },
    { id: "evidence", label: "Bằng chứng", cast: "chung", count: evidence.length || undefined, intro: "Hướng dẫn y khoa sát với hồ sơ của bạn." },
    { id: "kb", label: "Tri thức", cast: "nho", intro: "Phần tô nổi là phần đã dùng cho hồ sơ của bạn." },
    { id: "safety", label: "An toàn", cast: "luat", alert: urgent, intro: urgent ? "Có số đo cần chú ý, xem trước nhé." : "Số đo thực tế đối chiếu với luật an toàn." },
    ...(result.what_if ? [{ id: "whatif" as const, label: "Nếu thay đổi", cast: "goi" as const, intro: "Nếu đổi một thói quen, nguy cơ thay đổi ra sao?" }] : []),
    { id: "ask", label: "Hỏi đáp", cast: "tiep", intro: "Hỏi về bệnh, có dẫn nguồn." },
    { id: "tech", label: "Kỹ thuật", cast: "tiep", intro: "Mô hình đã chấm và cách cả đội làm việc." },
  ];
  const [selected, setSelected] = useState<TabId>(urgent ? "safety" : "explain");
  const [visited, setVisited] = useState<Set<TabId>>(new Set<TabId>([urgent ? "safety" : "explain"]));
  const current = tabs.some((t) => t.id === selected) ? selected : "explain";

  function select(id: TabId) {
    setSelected(id);
    setVisited((v) => (v.has(id) ? v : new Set(v).add(id)));
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const index = tabs.findIndex((t) => t.id === current);
    const next =
      event.key === "ArrowRight" ? (index + 1) % tabs.length
      : event.key === "ArrowLeft" ? (index - 1 + tabs.length) % tabs.length
      : event.key === "Home" ? 0
      : event.key === "End" ? tabs.length - 1
      : -1;
    if (next < 0) return;
    event.preventDefault();
    select(tabs[next].id);
    document.getElementById(`tab-${tabs[next].id}`)?.focus();
  }

  const panels: Record<TabId, ReactNode> = {
    explain: <ExplainTab result={result} />,
    evidence: <EvidenceTab evidence={evidence} note={note} />,
    kb: <KbPanel result={result} />,
    safety: <SafetyTab result={result} scales={scales} />,
    whatif: result.what_if ? <WhatIf whatIf={result.what_if} /> : null,
    ask: <ChatPanel bare />,
    tech: (
      <div className="space-y-6">
        <ModelStrip result={result} />
        <details className="group rounded-xl border border-borderSoft">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-semibold [&::-webkit-details-marker]:hidden">
            <span>
              Cả đội đã làm việc thế nào
              <span className="ml-2 font-normal text-muted">
                {result.trace ? `${result.trace.steps.length} bước · ${result.trace.total_ms.toFixed(0)} ms` : ""}
              </span>
            </span>
            <ChevronDown aria-hidden="true" className="h-4 w-4 text-muted transition group-open:rotate-180" />
          </summary>
          <div className="px-4 pb-4"><AgentTrace result={result} /></div>
        </details>
      </div>
    ),
  };

  return (
    <section className="min-w-0 space-y-5" aria-label="Chi tiết kết quả">
      {urgent ? <SafetyBanner result={result} scales={scales} onOpen={() => select("safety")} /> : null}

      <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1fr)_21rem] lg:items-start">
        {actions.length > 0 ? (
          <aside className="min-w-0 space-y-4 lg:sticky lg:top-4 lg:order-2">
            <ActionsCard actions={actions} />
          </aside>
        ) : null}

        <div className={clsx("min-w-0 rounded-2xl border border-borderSoft bg-panel shadow-console", actions.length === 0 && "lg:col-span-2")}>
          <div role="tablist" aria-label="Các phần của kết quả" onKeyDown={onKeyDown} className="flex gap-1.5 overflow-x-auto border-b border-borderSoft p-2">
            {tabs.map((tab) => {
              const on = tab.id === current;
              return (
                <button
                  key={tab.id}
                  id={`tab-${tab.id}`}
                  type="button"
                  role="tab"
                  aria-selected={on}
                  aria-controls={`panel-${tab.id}`}
                  tabIndex={on ? 0 : -1}
                  onClick={() => select(tab.id)}
                  className={clsx(
                    "choice flex min-h-11 shrink-0 items-center gap-2 rounded-full border-2 py-1 pl-1.5 pr-3.5 text-sm font-bold",
                    on ? "text-ink" : "border-transparent text-muted hover:bg-canvas hover:text-ink",
                  )}
                  style={on ? { borderColor: CAST[tab.cast].ink, background: CAST[tab.cast].tint } : undefined}
                >
                  <Avatar id={tab.cast} size={on ? 30 : 26} mood={on ? "happy" : "neutral"} />
                  {tab.label}
                  {tab.count ? <span className="rounded-full bg-infoSoft px-1.5 text-xs tabular-nums text-info">{tab.count}</span> : null}
                  {tab.alert ? <span className="h-2 w-2 rounded-full bg-danger" role="img" aria-label="có cảnh báo" /> : null}
                </button>
              );
            })}
          </div>
          {tabs.map((tab) =>
            visited.has(tab.id) || tab.id === current ? (
              <div
                key={tab.id}
                id={`panel-${tab.id}`}
                role="tabpanel"
                aria-labelledby={`tab-${tab.id}`}
                hidden={tab.id !== current}
                className="tab-panel min-w-0 space-y-4 p-4 md:p-6"
              >
                <div className="flex items-start gap-3">
                  <Avatar id={tab.cast} size={40} mood="talk" />
                  <Bubble id={tab.cast} className="py-2 text-sm leading-6">{tab.intro}</Bubble>
                </div>
                {panels[tab.id]}
              </div>
            ) : null,
          )}
        </div>
      </div>
    </section>
  );
}

/** Dải cảnh báo gọn: mỗi luật một ô gồm số đo và lời nhắn. */
function SafetyBanner({ result, scales, onOpen }: { result: PredictionResult; scales: MeasurementScale[]; onOpen: () => void }) {
  return (
    <div role="alert" className="rise rounded-2xl border border-danger/30 bg-danger/5 p-4 md:p-5">
      <div className="flex items-center gap-3">
        <Avatar id="luat" size={36} mood="worried" />
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-danger text-onAccent">
          <AlertTriangle aria-hidden="true" className="h-4 w-4" />
        </span>
        <p className="text-lg font-bold text-danger">{ESCALATION_TITLE[result.safety.escalation]}</p>
        <button type="button" onClick={onOpen} className="ml-auto min-h-9 rounded-lg px-3 text-sm font-semibold text-danger underline-offset-4 hover:underline">Xem chi tiết luật</button>
      </div>
      <ul className="mt-3 grid gap-3 [overflow-wrap:anywhere] sm:grid-cols-2">
        {result.safety.rules.map((rule) => {
          const scale = scales.find((s) => s.key === RULE_SCALE[rule.code.split("-")[0]]);
          return (
            <li key={rule.code} className="flex items-start gap-3 rounded-xl bg-panel p-3">
              {scale?.value != null ? (
                <p className="shrink-0 tabular-nums text-danger">
                  <span className="text-2xl font-bold leading-8">{scale.value}</span>
                  <span className="ml-1 block text-xs font-medium text-muted">{scale.unit}</span>
                </p>
              ) : null}
              <p className="text-sm leading-6 text-ink">{rule.message}</p>
            </li>
          );
        })}
      </ul>
      {result.safety.conflicts.length > 0 ? (
        <p className="mt-3 text-xs leading-5 text-muted">Điểm nguy cơ của mô hình đang thấp, nhưng số đo thực tế được ưu tiên hơn.</p>
      ) : null}
    </div>
  );
}

function ExplainTab({ result }: { result: PredictionResult }) {
  const features = useMemo(
    () => result.feature_explanation.features.slice().sort((a, b) => b.magnitude - a.magnitude).slice(0, 8),
    [result.feature_explanation.features],
  );
  const paragraphs = result.explanation.split(/\n+/).map((p) => p.trim()).filter(Boolean);
  return (
    <div className="space-y-6">
      <div className="flex gap-3">
        <Avatar id="mo" size={40} mood={result.risk === "High" ? "worried" : result.risk === "Low" ? "happy" : "think"} />
        <div className="min-w-0 space-y-2 text-sm leading-6 [overflow-wrap:anywhere]">
          <p className="font-semibold" style={{ color: CAST.mo.ink }}>Ông Mô giải thích</p>
          {paragraphs.map((p) => <p key={p}>{p}</p>)}
        </div>
      </div>
      <div className="min-w-0">
        <h3 className="text-sm font-bold">Nguy cơ của bạn đến từ đâu</h3>
        <Drivers features={features} trail={result.evidence_trail ?? []} />
        <p className="mt-3 text-xs text-muted">
          Phương pháp: {METHOD_LABELS[result.feature_explanation.method] ?? result.feature_explanation.method}.
        </p>
      </div>
    </div>
  );
}

function EvidenceTab({ evidence, note }: { evidence: EvidenceItem[]; note: string }) {
  return (
    <div className="space-y-5">
      {evidence.length > 0 ? (
        <ul className="space-y-3">
          {evidence.map((item) => (
            <li key={item.n} className="flex gap-3 rounded-xl border border-borderSoft p-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold text-onAccent" style={{ background: CAST.chung.ink }}>{item.n}</span>
              <div className="min-w-0 [overflow-wrap:anywhere]">
                <p className="text-sm leading-6">{item.text}</p>
                {item.source ? (
                  <p className="mt-1 text-xs leading-5 text-muted">
                    {item.source.url ? (
                      <a href={item.source.url} target="_blank" rel="noreferrer" className="text-info underline underline-offset-2">{item.source.title}</a>
                    ) : (
                      item.source.title
                    )}
                  </p>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted">Chưa tìm được đoạn hướng dẫn nào đủ liên quan đến hồ sơ này.</p>
      )}
      {note ? <p className="text-xs leading-5 text-muted">{note}</p> : null}
    </div>
  );
}

/** Two-sided bars: left of the axis lowers risk, right raises it. Rows with evidence expand. */
function Drivers({ features, trail }: { features: PredictionResult["feature_explanation"]["features"]; trail: EvidenceTrailItem[] }) {
  const max = Math.max(...features.map((f) => Math.abs(f.impact)), 0.0001);
  const evidenceByFeature = new Map(trail.map((item) => [item.feature, item.evidence]));
  const [ref, seen] = useInView<HTMLDivElement>();
  return (
    <div ref={ref} className="mt-3">
      <div className="mb-1 grid grid-cols-[minmax(0,8rem)_1fr_1rem] gap-3 text-xs font-semibold text-muted">
        <span />
        <span className="flex justify-between">
          <span className="text-success">← Giảm nguy cơ</span>
          <span className="text-danger">Tăng nguy cơ →</span>
        </span>
        <span />
      </div>
      <ul className="divide-y divide-borderSoft">
        {features.map((f, index) => {
          const width = (Math.abs(f.impact) / max) * 50;
          const up = f.impact >= 0;
          const evidence = evidenceByFeature.get(f.feature) ?? [];
          const row = (
            <div className="grid grid-cols-[minmax(0,8rem)_1fr_1rem] items-center gap-3 py-2">
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold">{featureLabel(f.feature)}</div>
                <div className="truncate text-xs text-muted">{formatFeatureValue(f.feature, f.value)}</div>
              </div>
              <div className="relative h-5" role="img" aria-label={`${featureLabel(f.feature)}: ${up ? "tăng" : "giảm"} nguy cơ ${Math.abs(f.impact).toFixed(3)}`}>
                <span className="absolute inset-y-0 left-1/2 w-px bg-borderSoft" />
                <span
                  className="absolute top-0.5 h-4 rounded-sm"
                  style={{
                    [up ? "left" : "right"]: "50%",
                    width: seen ? `${Math.max(1, width)}%` : "0%",
                    backgroundColor: up ? "#c4452f" : "#1b7a4b",
                    transition: `width 0.7s cubic-bezier(0.16,1,0.3,1) ${index * 0.06}s`,
                  }}
                />
              </div>
              {evidence.length > 0 ? <ChevronDown aria-hidden="true" className="h-4 w-4 text-muted transition group-open:rotate-180" /> : <span />}
            </div>
          );
          return evidence.length > 0 ? (
            <li key={f.feature}>
              <details className="group">
                <summary className="cursor-pointer list-none rounded-lg hover:bg-canvas [&::-webkit-details-marker]:hidden">{row}</summary>
                <div className="space-y-2 pb-3 pl-1">
                  {evidence.map((passage) => (
                    <blockquote key={passage.evidence_id} className="rounded-lg bg-canvas p-3 text-sm leading-6 text-muted">
                      {passage.text}
                      <footer className="mt-1 text-xs"><CitationLink citation={passage} /></footer>
                    </blockquote>
                  ))}
                </div>
              </details>
            </li>
          ) : (
            <li key={f.feature}>{row}</li>
          );
        })}
      </ul>
    </div>
  );
}

/** Việc nên làm: luôn hiện cạnh nội dung; bấm để tích "đã làm". */
function ActionsCard({ actions }: { actions: string[] }) {
  const [done, setDone] = useState<Set<number>>(new Set());
  const toggle = (i: number) =>
    setDone((current) => {
      const next = new Set(current);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  const all = done.size === actions.length;

  return (
    <section aria-labelledby="actions-title" className="relative overflow-hidden rounded-2xl border border-borderSoft bg-panel p-4 shadow-console">
      {all ? (
        <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 top-0 h-0">
          {Array.from({ length: 14 }, (_, i) => (
            <span key={i} className="confetti" style={{ left: `${6 + i * 6.5}%`, background: ["#c4452f", "#c98a1a", "#1b7a4b", "#4b3fa8", "#0b6b86"][i % 5], animationDelay: `${(i % 5) * 0.08}s` }} />
          ))}
        </div>
      ) : null}
      <div className="flex items-center gap-3">
        <Avatar id="goi" size={36} mood={all ? "happy" : "neutral"} />
        <div className="min-w-0 flex-1">
          <h2 id="actions-title" className="flex items-center gap-1.5 text-base font-bold" style={{ color: CAST.goi.ink }}>
            <ListChecks aria-hidden="true" className="h-4 w-4" /> Việc nên làm
          </h2>
          <p role="status" className="text-xs text-muted">{all ? "Tuyệt vời, bạn đã làm hết rồi!" : `Đã làm ${done.size}/${actions.length} · bấm để tích`}</p>
        </div>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-borderSoft" aria-hidden="true">
        <div className="h-full rounded-full bg-success transition-[width] duration-300" style={{ width: `${(done.size / actions.length) * 100}%` }} />
      </div>
      <ol className="mt-3 space-y-1.5">
        {actions.map((text, i) => {
          const on = done.has(i);
          return (
            <li key={text}>
              <button
                type="button"
                aria-pressed={on}
                onClick={() => toggle(i)}
                className={clsx(
                  "flex w-full items-start gap-3 rounded-xl p-2.5 text-left transition-colors",
                  on ? "bg-success/10" : "hover:bg-canvas",
                )}
              >
                <span
                  aria-hidden="true"
                  className={clsx("mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 text-xs font-bold", on ? "border-success bg-success text-onAccent" : "border-info text-info")}
                >
                  {on ? <Check className="h-3 w-3" /> : i + 1}
                </span>
                <span className={clsx("text-sm leading-6 [overflow-wrap:anywhere]", on && "text-muted line-through")}>{text}</span>
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function SafetyTab({ result, scales }: { result: PredictionResult; scales: MeasurementScale[] }) {
  const { safety } = result;
  const urgent = safety.alerts.length > 0;
  return (
    <div className="space-y-6">
      {urgent ? (
        <ul className="space-y-2">
          {safety.rules.map((rule) => (
            <li key={rule.code} className="rounded-xl border border-danger/25 bg-danger/5 p-3 [overflow-wrap:anywhere]">
              <p className="flex flex-wrap items-center gap-2 text-sm font-bold text-danger">
                <AlertTriangle aria-hidden="true" className="h-4 w-4 shrink-0" /> {rule.name}
                <span className="rounded bg-panel px-1.5 text-xs font-semibold tabular-nums text-muted">{rule.code}</span>
                {rule.escalation ? <span className="ml-auto text-xs font-semibold text-muted">{ESCALATION_LABELS[rule.escalation]}</span> : null}
              </p>
              <p className="mt-1 text-sm leading-6">{rule.message}</p>
              {rule.basis ? <p className="mt-1 text-xs leading-5 text-muted">Căn cứ: {rule.basis}</p> : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="flex items-center gap-2 rounded-xl bg-success/10 px-4 py-3 text-sm font-semibold text-success">
          <ShieldCheck aria-hidden="true" className="h-5 w-5 shrink-0" /> Luật an toàn không phát hiện số đo nào cần xử trí gấp.
        </p>
      )}
      {safety.conflicts.length > 0 ? (
        <div>
          <h3 className="text-sm font-bold">Khi mô hình và số đo bất đồng</h3>
          <ul className="mt-2 space-y-2">
            {safety.conflicts.map((conflict) => (
              <li key={conflict.code} className="rounded-xl bg-canvas p-3 text-sm leading-6 [overflow-wrap:anywhere]">
                {conflict.message}
                {conflict.resolution ? <span className="mt-1 block text-xs text-muted">Cách giải quyết: {conflict.resolution}</span> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <MeasurementScales scales={scales} />
      {safety.disclaimers.length > 0 ? (
        <ul className="list-disc space-y-1 pl-5 text-xs leading-5 text-muted">
          {safety.disclaimers.map((text) => <li key={text}>{text}</li>)}
        </ul>
      ) : null}
      <InputScoreDetails result={result} />
    </div>
  );
}
