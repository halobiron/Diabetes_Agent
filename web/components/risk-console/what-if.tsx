import { FlaskConical } from "lucide-react";

import { RISK_LABELS } from "@/lib/labels";
import type { WhatIfResult, WhatIfScenario } from "@/types/healthcare";

import { CitationLink } from "./citation";
import { PanelHeading } from "./shared-ui";

const percent = (value: number) => `${(value * 100).toFixed(1)}%`;

export function WhatIf({ whatIf }: { whatIf: WhatIfResult }) {
  const rows = [...whatIf.scenarios, ...(whatIf.combined ? [whatIf.combined] : [])];

  return (
    <section aria-labelledby="what-if-title" className="console-panel min-w-0 rounded-lg p-5">
      <div id="what-if-title"><PanelHeading icon={<FlaskConical className="h-4 w-4" />} title="Nếu thay đổi thì sao?" /></div>
      <p className="mt-2 text-sm leading-6 text-muted">Mô hình tính lại nguy cơ khi chỉ đổi yếu tố được nêu, giữ nguyên các thông tin còn lại. Hiện tại: <span className="tabular-nums text-ink">{percent(whatIf.probability_before)}</span>.</p>
      {rows.length > 0 ? (
        <ul className="mt-4 space-y-3">
          {rows.map((row) => <ScenarioRow key={row.key} row={row} before={whatIf.probability_before} />)}
        </ul>
      ) : (
        <p className="mt-4 text-sm text-muted">Với thông tin đã nhập, chưa có thay đổi nào làm giảm nguy cơ đáng kể theo mô hình.</p>
      )}
      <p className="mt-4 text-xs leading-5 text-muted">Đây là mối liên quan thống kê từ dữ liệu khảo sát, không phải bảo đảm kết quả của riêng bạn. Hãy trao đổi với bác sĩ trước khi thay đổi điều trị.</p>
    </section>
  );
}

function ScenarioRow({ row, before }: { row: WhatIfScenario; before: number }) {
  const remaining = Math.min(100, (row.probability_after / before) * 100);
  return (
    <li className="rounded-md border border-borderSoft bg-canvas/40 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-semibold text-ink">{row.label}</span>
        <span className="text-sm tabular-nums text-ink">{percent(before)} → {percent(row.probability_after)} <span className="text-success">({(row.change * 100).toFixed(1)} điểm %)</span></span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-borderSoft" role="img" aria-label={`Nguy cơ còn ${remaining.toFixed(0)}% so với hiện tại`}>
        <div className="h-full rounded-full bg-success" style={{ width: `${remaining}%` }} />
      </div>
      <p className="mt-2 text-xs text-muted">Mức nguy cơ sau thay đổi: {RISK_LABELS[row.risk_after] ?? row.risk_after}</p>
      {row.evidence.length > 0 ? (
        <p className="mt-1 text-xs leading-5 text-muted">Cơ sở: {row.evidence.map((citation, index) => <span key={citation.evidence_id}>{index > 0 ? "; " : ""}<CitationLink citation={citation} /></span>)}</p>
      ) : null}
    </li>
  );
}
