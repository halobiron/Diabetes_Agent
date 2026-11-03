import { BarChart3, Database } from "lucide-react";
import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { RISK_COLORS, RISK_LABELS } from "@/lib/labels";
import type { MemoryRecord, PredictionResult } from "@/types/healthcare";

import { DataTable, PanelHeading } from "./shared-ui";
import { formatMemoryTimestamp, riskDistribution } from "./utils";

export function History({
  result,
  records,
  isLoading,
}: {
  result: PredictionResult;
  records: MemoryRecord[];
  isLoading: boolean;
}) {
  const fallbackRows = useMemo(
    () =>
      result.similar_cases.map((item, index) => ({
        id: index + 1,
        risk: item.metadata.risk ?? "Unknown",
        probability: item.metadata.probability ?? 0,
        timestamp: formatMemoryTimestamp(item.metadata.timestamp, "Hồ sơ đã lưu"),
      })),
    [result.similar_cases],
  );
  const rows = useMemo(
    () =>
      records.length > 0
        ? records.map((item, index) => ({
            id: index + 1,
            risk: item.metadata.risk ?? "Unknown",
            probability: item.metadata.probability ?? 0,
            timestamp: formatMemoryTimestamp(item.metadata.timestamp, "Không rõ thời gian"),
          }))
        : fallbackRows,
    [fallbackRows, records],
  );
  const distribution = useMemo(() => riskDistribution(rows), [rows]);

  return (
    <section className="grid min-w-0 grid-cols-1 gap-5 xl:grid-cols-[0.9fr_1.1fr]">
      <div className="console-panel min-w-0 rounded-lg p-5">
        <PanelHeading icon={<BarChart3 className="h-4 w-4" />} title="Phân bố mức nguy cơ" />
        <div className="mt-4 h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={distribution} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
              <XAxis dataKey="risk" tickFormatter={(value) => RISK_LABELS[value] ?? value} stroke="#9aa4b2" tickLine={false} axisLine={false} />
              <YAxis stroke="#9aa4b2" tickLine={false} axisLine={false} />
              <Tooltip
                labelFormatter={(value) => RISK_LABELS[String(value)] ?? value}
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
                contentStyle={{
                  background: "#101318",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 8,
                }}
              />
              <Bar name="Số hồ sơ" dataKey="count" radius={[4, 4, 0, 0]}>
                {distribution.map((entry) => (
                  <Cell key={entry.risk} fill={RISK_COLORS[entry.risk] ?? "#5aa3d9"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="console-panel min-w-0 rounded-lg p-5">
        <PanelHeading icon={<Database className="h-4 w-4" />} title="Lịch sử hồ sơ" />
        {isLoading ? <p className="mt-4 text-sm text-muted">Đang tải lịch sử hồ sơ...</p> : null}
        <DataTable
          rows={rows.map((row) => ({
            "Hồ sơ": row.id,
            "Nguy cơ": RISK_LABELS[row.risk] ?? "Chưa rõ",
            "Xác suất": `${(row.probability * 100).toFixed(1)}%`,
            "Thời gian": row.timestamp,
          }))}
        />
      </div>
    </section>
  );
}
