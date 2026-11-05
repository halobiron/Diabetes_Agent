"use client";

import clsx from "clsx";
import { AlertTriangle, BarChart3, Brain, Check, Info, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";

import { featureLabel, formatFeatureValue, METHOD_LABELS } from "@/lib/labels";
import type { EvidenceTrailItem, MeasurementScale, PredictionResult } from "@/types/healthcare";

import { CitationLink } from "./citation";
import { MeasurementScales } from "./measurement-scales";
import { ChevronDown } from "lucide-react";
import { Act, CastRail, type ActMeta } from "./acts";
import { Bubble, Seal, useInView, type Mood } from "./agents";
import { PanelHeading } from "./shared-ui";
import { WhatIf } from "./what-if";

const SENTENCE_SPLIT = /(?<=[.!?])\s+(?=[A-ZÀ-Ỹ])/;

const ESCALATION_TITLE = {
  routine_followup: "Cần lưu ý",
  prompt_clinician_followup: "Nên đi khám sớm",
  urgent_clinician_review: "Cần được khám khẩn",
} as const;

const RULE_SCALE: Record<string, string> = { GLU: "glucose", BP: "bp" };

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

export function Assessment({ result, scales }: { result: PredictionResult; scales: MeasurementScale[] }) {
  const features = useMemo(
    () =>
      result.feature_explanation.features
        .slice()
        .sort((a, b) => b.magnitude - a.magnitude)
        .slice(0, 8),
    [result.feature_explanation.features],
  );
  const { actions, evidence, note } = parseRecommendation(result.recommendation);
  const alerts = result.safety.alerts;

  const urgent = alerts.length > 0;
  const riskMood: Mood = result.risk === "High" ? "worried" : result.risk === "Low" ? "happy" : "think";

  const safety = (
    <Act
      key="luat"
      id="luat"
      title="Kiểm tra an toàn"
      line={urgent ? "Khoan, bạn xem phần này trước nhé. Mình thấy có số đo cần chú ý." : "Mình đã kiểm tra các số đo thực tế của bạn với luật an toàn. Mọi thứ khá ổn!"}
      mood={urgent ? "worried" : "happy"}
    >
      {urgent ? (
        <div role="alert" className="paper relative rounded-2xl border-2 p-5" style={{ borderColor: "#b3261e66" }}>
          <div className="flex flex-wrap items-center gap-3 pr-2">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-danger text-onAccent">
              <AlertTriangle aria-hidden="true" className="h-5 w-5" />
            </span>
            <p className="text-xl font-bold leading-7 text-danger">{ESCALATION_TITLE[result.safety.escalation]}</p>
            <span className="stamp-in ml-auto" style={{ ["--tilt" as string]: "-6deg", ["--delay" as string]: "0.4s" }}>
              <Seal id="luat" tilt={0}>Chú Luật xác nhận</Seal>
            </span>
          </div>
          <ul className="mt-4 divide-y divide-danger/15 [overflow-wrap:anywhere]">
            {result.safety.rules.map((rule) => {
              const scale = scales.find((s) => s.key === RULE_SCALE[rule.code.split("-")[0]]);
              return (
                <li key={rule.code} className="grid gap-x-5 gap-y-1 py-3 first:pt-0 last:pb-0 sm:grid-cols-[9.5rem_1fr] sm:items-center">
                  {scale?.value != null ? (
                    <div>
                      <p className="text-sm font-medium text-muted">{scale.title}</p>
                      <p className="tabular-nums text-danger">
                        <span className="text-3xl font-bold leading-9">{scale.value}</span>
                        <span className="ml-1 text-sm font-medium">{scale.unit}</span>
                      </p>
                    </div>
                  ) : null}
                  <p className="text-base leading-7 text-ink sm:col-start-2">{rule.message}</p>
                </li>
              );
            })}
          </ul>
          {result.safety.conflicts.length > 0 ? (
            <p className="mt-4 flex gap-2 border-t border-danger/15 pt-4 text-sm leading-6 text-muted">
              <Info aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
              Điểm nguy cơ tổng thể của hệ thống đang thấp, nhưng hãy tin số đo thực tế của bạn hơn.
            </p>
          ) : null}
        </div>
      ) : (
        <p className="flex items-center gap-2 rounded-xl bg-infoSoft px-4 py-3 text-sm font-semibold text-info">
          <ShieldCheck aria-hidden="true" className="h-5 w-5 shrink-0" /> Luật an toàn không phát hiện số đo nào cần xử trí gấp.
        </p>
      )}
      <MeasurementScales scales={scales} />
    </Act>
  );

  const why = (
    <Act key="mo" id="mo" title="Vì sao có kết quả này" line="Để tôi giải thích vì sao mô hình ra kết quả này nhé." mood={riskMood}>
      <div className="space-y-3">
        <PanelHeading icon={<Brain className="h-5 w-5" />} title="Ông Mô giải thích" />
        {result.explanation
          .split(/\n+/)
          .map((part) => part.trim())
          .filter(Boolean)
          .map((part) => (
            <Bubble key={part} id="mo">{part}</Bubble>
          ))}
      </div>
      <div className="min-w-0">
        <PanelHeading icon={<BarChart3 className="h-5 w-5" />} title="Nguy cơ của bạn đến từ đâu" />
        <Drivers features={features} trail={result.evidence_trail ?? []} />
        <p className="mt-4 text-xs text-muted">Phương pháp: {METHOD_LABELS[result.feature_explanation.method] ?? result.feature_explanation.method}</p>
      </div>
    </Act>
  );

  const proof =
    evidence.length > 0 ? (
      <Act key="chung" id="chung" title="Bằng chứng y khoa" line={`Mình đã tìm được ${evidence.length} đoạn hướng dẫn y khoa liên quan đến hồ sơ của bạn.`} mood="happy">
        <ul className="space-y-4">
          {evidence.map((item, i) => (
            <li key={item.n} className="paper relative rounded-xl border-2 p-4 pr-24" style={{ borderColor: "#1b6b4d44", transform: `rotate(${i % 2 ? 0.5 : -0.5}deg)` }}>
              <span className="absolute right-3 top-3"><Seal id="chung" tilt={5} className="!px-2 !py-0 !text-xs">Nguồn [{item.n}]</Seal></span>
              <p className="text-sm leading-6 [overflow-wrap:anywhere]">{item.text}</p>
              {item.source ? (
                <p className="mt-2 text-xs leading-5 text-muted [overflow-wrap:anywhere]">
                  [{item.n}]{" "}
                  {item.source.url ? (
                    <a href={item.source.url} target="_blank" rel="noreferrer" className="text-info underline underline-offset-2">{item.source.title}</a>
                  ) : (
                    item.source.title
                  )}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
        {note ? <p className="text-xs leading-5 text-muted">{note}</p> : null}
      </Act>
    ) : null;

  const advice = (
    <Act key="goi" id="goi" title="Bạn nên làm gì" line="Cuối cùng là phần của mình: những việc bạn có thể làm ngay từ hôm nay!" mood="happy">
      <Checklist actions={actions} />
      {result.what_if ? <WhatIf whatIf={result.what_if} /> : null}
    </Act>
  );

  const acts: ActMeta[] = [
    ...(urgent ? [{ id: "luat" as const, title: "An toàn" }] : []),
    { id: "mo", title: "Giải thích" },
    ...(proof ? [{ id: "chung" as const, title: "Bằng chứng" }] : []),
    ...(!urgent ? [{ id: "luat" as const, title: "An toàn" }] : []),
    { id: "goi", title: "Lời khuyên" },
  ];

  return (
    <section className="min-w-0 space-y-10" aria-label="Phần trình bày của cả đội">
      <CastRail acts={acts} />
      {urgent ? safety : null}
      {why}
      {proof}
      {!urgent ? safety : null}
      {advice}
    </section>
  );
}

/** Two-sided bars: left of the axis lowers risk, right raises it. Rows with evidence expand. */
function Drivers({ features, trail }: { features: PredictionResult["feature_explanation"]["features"]; trail: EvidenceTrailItem[] }) {
  const max = Math.max(...features.map((f) => Math.abs(f.impact)), 0.0001);
  const evidenceByFeature = new Map(trail.map((item) => [item.feature, item.evidence]));
  const [ref, seen] = useInView<HTMLDivElement>();
  return (
    <div ref={ref} className="mt-5">
      <div className="mb-1 grid grid-cols-[minmax(0,9rem)_1fr_1rem] gap-3 text-xs font-semibold text-muted">
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
            <div className="grid grid-cols-[minmax(0,9rem)_1fr_1rem] items-center gap-3 py-3">
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold">{featureLabel(f.feature)}</div>
                <div className="flex items-center gap-2 text-xs text-muted">
                  {formatFeatureValue(f.feature, f.value)}
                  <span className={clsx("rounded border px-1 text-[10px] font-bold uppercase", up ? "border-danger text-danger" : "border-success text-success")}>{up ? "Tăng" : "Giảm"}</span>
                </div>
              </div>
              <div className="relative h-6" role="img" aria-label={`${featureLabel(f.feature)}: ${up ? "tăng" : "giảm"} nguy cơ ${Math.abs(f.impact).toFixed(3)}`}>
                <span className="absolute inset-y-0 left-1/2 w-px bg-borderSoft" />
                <span
                  className="absolute top-1 h-4 rounded-sm"
                  style={{
                    [up ? "left" : "right"]: "50%",
                    width: seen ? `${Math.max(1, width)}%` : "0%",
                    backgroundColor: up ? "#c4452f" : "#1b7a4b",
                    transition: `width 0.7s cubic-bezier(0.16,1,0.3,1) ${index * 0.08}s`,
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
                <div className="space-y-3 pb-4 pl-1">
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
      <p className="mt-3 text-xs text-muted">Bấm vào dòng có mũi tên để xem đoạn hướng dẫn y khoa liên quan.</p>
    </div>
  );
}

/** Việc Bạn Gợi giao: bấm để tích "đã làm", Bạn Gợi đếm giúp. */
function Checklist({ actions }: { actions: string[] }) {
  const [done, setDone] = useState<Set<number>>(new Set());
  const toggle = (i: number) =>
    setDone((current) => {
      const next = new Set(current);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  const all = actions.length > 0 && done.size === actions.length;

  return (
    <div>
      <ol className="space-y-3">
        {actions.map((text, i) => {
          const on = done.has(i);
          return (
            <li key={text}>
              <button
                type="button"
                aria-pressed={on}
                onClick={() => toggle(i)}
                className={clsx(
                  "choice flex w-full items-start gap-3 rounded-2xl border-2 p-4 text-left",
                  on ? "border-success/60 bg-success/10" : "border-borderSoft bg-panel hover:border-info/50",
                )}
              >
                <span
                  aria-hidden="true"
                  className={clsx("mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 text-sm font-bold", on ? "border-success bg-success text-onAccent" : "border-info text-info")}
                >
                  {on ? <Check className="h-4 w-4" /> : i + 1}
                </span>
                <span className={clsx("text-base leading-7 [overflow-wrap:anywhere]", on && "text-muted line-through")}>{text}</span>
              </button>
            </li>
          );
        })}
      </ol>
      <p role="status" className="mt-3 text-sm font-semibold text-muted">
        {all ? "Bạn Gợi: Tuyệt vời, bạn đã làm hết rồi đó!" : `Đã làm ${done.size}/${actions.length} việc. Bấm vào việc để tích khi bạn làm xong.`}
      </p>
    </div>
  );
}