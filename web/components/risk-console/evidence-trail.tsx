import { Link2 } from "lucide-react";

import { featureLabel, formatFeatureValue } from "@/lib/labels";
import type { EvidenceTrailItem } from "@/types/healthcare";

import { CitationLink } from "./citation";
import { PanelHeading } from "./shared-ui";

export function EvidenceTrail({ trail }: { trail: EvidenceTrailItem[] }) {
  if (trail.length === 0) return null;

  return (
    <section aria-labelledby="evidence-trail-title" className="console-panel min-w-0 rounded-xl p-5 md:p-6">
      <div id="evidence-trail-title"><PanelHeading icon={<Link2 className="h-4 w-4" />} title="Vì sao các yếu tố này quan trọng" /></div>
      <p className="mt-2 text-sm leading-6 text-muted">Mỗi yếu tố làm tăng nguy cơ theo mô hình được nối, qua đồ thị tri thức, với đoạn hướng dẫn y khoa đã truy xuất.</p>
      <ul className="mt-4 space-y-3">
        {trail.map((item) => (
          <li key={item.feature} className="rounded-md border border-borderSoft bg-canvas/40 p-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="font-semibold text-ink">{featureLabel(item.feature)}{item.value !== null ? ` (${formatFeatureValue(item.feature, item.value)})` : ""}</span>
              <span className="text-xs tabular-nums text-danger">tăng nguy cơ +{item.impact.toFixed(3)}</span>
            </div>
            {item.evidence.length > 0 ? item.evidence.map((passage) => (
              <blockquote key={passage.evidence_id} className="mt-2 border-l-2 border-info/60 pl-3 text-sm leading-6 text-muted">
                {passage.text}
                <footer className="mt-1 text-xs"><CitationLink citation={passage} />{passage.supports.length > 0 ? ` · liên quan: ${passage.supports.join(", ")}` : ""}</footer>
              </blockquote>
            )) : <p className="mt-2 text-sm text-muted">Chưa có đoạn bằng chứng nào trong cơ sở tri thức liên kết với yếu tố này.</p>}
          </li>
        ))}
      </ul>
    </section>
  );
}
