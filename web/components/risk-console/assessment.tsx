import { AlertTriangle, BarChart3, Brain, CheckCircle2, Footprints } from "lucide-react";
import { useMemo } from "react";

import { featureLabel, formatFeatureValue, METHOD_LABELS } from "@/lib/labels";
import type { EvidenceTrailItem, MeasurementScale, PredictionResult } from "@/types/healthcare";

import { CitationLink } from "./citation";
import { MeasurementScales } from "./measurement-scales";
import { ChevronDown } from "lucide-react";
import { PanelHeading } from "./shared-ui";
import { WhatIf } from "./what-if";

const SENTENCE_SPLIT = /(?<=[.!?])\s+(?=[A-ZÀ-Ỹ])/;

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

  return (
    <section className="grid min-w-0 gap-5 lg:grid-cols-12">
      <div className="console-panel rounded-2xl p-6 lg:col-span-7 lg:self-start">
        <PanelHeading icon={<CheckCircle2 className="h-5 w-5" />} title="Bạn nên làm gì" />
        <ol className="mt-5 space-y-3">
          {actions.map((step, i) => <Step key={step} n={i + 1} text={step} />)}
        </ol>
        {evidence.length > 0 ? (
          <details className="mt-6 border-t border-borderSoft pt-4">
            <summary className="cursor-pointer text-base font-semibold text-info">Bằng chứng hướng dẫn y khoa ({evidence.length})</summary>
            <ul className="mt-4 space-y-3">
              {evidence.map((item) => (
                <li key={item.n} className="rounded-xl bg-canvas p-4">
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
            {note ? <p className="mt-3 text-xs leading-5 text-muted">{note}</p> : null}
          </details>
        ) : null}
      </div>

      <div className="flex flex-col gap-5 lg:col-span-5">
        {alerts.length > 0 ? (
          <div role="alert" className="rounded-2xl border border-danger/30 bg-danger/10 p-6 text-danger">
            <div className="mb-3 flex items-center gap-2 text-lg font-bold">
              <AlertTriangle aria-hidden="true" className="h-5 w-5" /> Cần lưu ý
            </div>
            <ul className="space-y-2 text-base leading-7">
              {alerts.map((alert) => (
                <li key={alert} className="[overflow-wrap:anywhere]">{alert}</li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="rounded-2xl bg-infoSoft p-6">
            <div className="flex items-center gap-2 text-lg font-bold text-info">
              <Footprints aria-hidden="true" className="h-5 w-5" /> Không có cảnh báo
            </div>
            <p className="mt-2 text-base leading-7 text-ink">Các luật an toàn không phát hiện số đo nào cần xử trí gấp.</p>
          </div>
        )}
        <div className="console-panel flex-1 rounded-2xl p-6">
          <PanelHeading icon={<Brain className="h-5 w-5" />} title="Vì sao có kết quả này" />
          <p className="mt-4 whitespace-pre-line text-base leading-7 text-muted [overflow-wrap:anywhere]">{result.explanation}</p>
        </div>
      </div>

      <div className="lg:col-span-12">
        <MeasurementScales scales={scales} />
      </div>

      <div className="console-panel min-w-0 rounded-2xl p-6 lg:col-span-7">
        <PanelHeading icon={<BarChart3 className="h-5 w-5" />} title="Nguy cơ của bạn đến từ đâu" />
        <Drivers features={features} trail={result.evidence_trail ?? []} />
        <p className="mt-4 text-xs text-muted">Phương pháp: {METHOD_LABELS[result.feature_explanation.method] ?? result.feature_explanation.method}</p>
      </div>

      <div className="min-w-0 lg:col-span-5">
        {result.what_if ? <WhatIf whatIf={result.what_if} /> : null}
      </div>

    </section>
  );
}

/** Two-sided bars: left of the axis lowers risk, right raises it. Rows with evidence expand. */
function Drivers({ features, trail }: { features: PredictionResult["feature_explanation"]["features"]; trail: EvidenceTrailItem[] }) {
  const max = Math.max(...features.map((f) => Math.abs(f.impact)), 0.0001);
  const evidenceByFeature = new Map(trail.map((item) => [item.feature, item.evidence]));
  return (
    <div className="mt-5">
      <div className="mb-1 grid grid-cols-[minmax(0,9rem)_1fr_1rem] gap-3 text-xs font-semibold text-muted">
        <span />
        <span className="flex justify-between">
          <span className="text-success">← Giảm nguy cơ</span>
          <span className="text-danger">Tăng nguy cơ →</span>
        </span>
        <span />
      </div>
      <ul className="divide-y divide-borderSoft">
        {features.map((f) => {
          const width = (Math.abs(f.impact) / max) * 50;
          const up = f.impact >= 0;
          const evidence = evidenceByFeature.get(f.feature) ?? [];
          const row = (
            <div className="grid grid-cols-[minmax(0,9rem)_1fr_1rem] items-center gap-3 py-3">
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold">{featureLabel(f.feature)}</div>
                <div className="text-xs text-muted">{formatFeatureValue(f.feature, f.value)}</div>
              </div>
              <div className="relative h-6" role="img" aria-label={`${featureLabel(f.feature)}: ${up ? "tăng" : "giảm"} nguy cơ ${Math.abs(f.impact).toFixed(3)}`}>
                <span className="absolute inset-y-0 left-1/2 w-px bg-borderSoft" />
                <span
                  className="absolute top-1 h-4 rounded-sm"
                  style={{ [up ? "left" : "right"]: "50%", width: `${Math.max(1, width)}%`, backgroundColor: up ? "#c4452f" : "#1b7a4b" }}
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

function Step({ n, text }: { n: number; text: string }) {
  return (
    <li className="flex gap-3">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-infoSoft text-sm font-bold text-info">{n}</span>
      <span className="text-base leading-7 [overflow-wrap:anywhere]">{text}</span>
    </li>
  );
}
