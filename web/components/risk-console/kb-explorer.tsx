"use client";

import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { Database, Loader2 } from "lucide-react";
import { useMemo, useState } from "react";

import { fetchKb, fetchKbEntity } from "@/lib/api";
import type { KbEntity, KbEvidenceRow, KbGraph as KbGraphData, PredictionResult } from "@/types/healthcare";

import { CitationLink } from "./citation";
import { KB_COLUMNS, KbGraph, RELATION_TEXT } from "./kb-graph";

const DEFAULT_ENTITY = "type2_diabetes";

/** Phần của đồ thị Neo4j mà hồ sơ này đã dùng, suy ra từ kết quả truy xuất. */
function usedByResult(result: PredictionResult) {
  const retrieved = result.retrieved_context ?? [];
  return {
    keys: new Set([...retrieved.flatMap((item) => item.factors ?? []), ...(result.evidence_trail ?? []).map((item) => item.feature)]),
    names: new Set(retrieved.flatMap((item) => item.supports ?? [])),
    evidence: new Set(retrieved.map((item) => item.evidence_id)),
  };
}

/** Đồ thị tri thức đọc từ Neo4j, làm nổi các yếu tố, can thiệp và đoạn bằng chứng đã dùng cho hồ sơ này. */
export function KbPanel({ result }: { result: PredictionResult }) {
  const kb = useQuery({ queryKey: ["kb"], queryFn: fetchKb });
  const [selected, setSelected] = useState<string | null>(null);
  const used = useMemo(() => usedByResult(result), [result]);

  const highlight = useMemo(
    () => new Set((kb.data?.entities ?? []).filter((e) => (e.key && used.keys.has(e.key)) || used.names.has(e.name)).map((e) => e.id)),
    [kb.data, used],
  );

  if (kb.isPending) {
    return (
      <p role="status" className="flex items-center gap-2 text-sm font-semibold text-info">
        <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> Đang đọc cơ sở tri thức…
      </p>
    );
  }
  if (kb.isError) return <p role="alert" className="text-sm font-semibold text-danger">{kb.error.message}</p>;

  const graph = kb.data;
  const firstMine = graph.entities.find((e) => highlight.has(e.id) && e.label === "RiskFactor")?.id;
  const fallback = firstMine ?? (graph.entities.some((e) => e.id === DEFAULT_ENTITY) ? DEFAULT_ENTITY : graph.entities[0]?.id ?? null);
  const current = selected ?? fallback;

  return (
    <div className="space-y-6">
      <SourceStatus graph={graph} mine={highlight.size} />
      <div>
        <div className="hidden lg:block">
          <KbGraph entities={graph.entities} relations={graph.relations} selected={current} highlight={highlight} onSelect={setSelected} />
        </div>
        <EntityList entities={graph.entities} selected={current} highlight={highlight} onSelect={setSelected} className="lg:hidden" />
      </div>
      {current ? <EntityDetail key={current} graph={graph} entityId={current} usedEvidence={used.evidence} onSelect={setSelected} /> : null}
    </div>
  );
}

function SourceStatus({ graph, mine }: { graph: KbGraphData; mine: number }) {
  const live = graph.source === "neo4j";
  return (
    <div className="space-y-2 text-sm">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className={clsx("inline-flex items-center gap-2 rounded-full border px-3 py-1.5 font-semibold", live ? "border-success/40 bg-success/10 text-success" : "border-warning/40 bg-warning/10 text-warning")}>
          <Database aria-hidden="true" className="h-4 w-4" />
          {live ? "Đang đọc trực tiếp từ Neo4j" : graph.neo4j_configured ? "Không kết nối được Neo4j, đang dùng file KB dự phòng" : "Chưa cấu hình Neo4j, đang dùng file KB"}
        </span>
        <span className="text-muted tabular-nums">
          {graph.entities.length} thực thể · {graph.relations.length} quan hệ · {graph.evidence_count} đoạn bằng chứng · {graph.source_count} nguồn
          {graph.version ? ` · phiên bản ${graph.version}` : ""}
        </span>
      </div>
      <p className="flex flex-wrap items-center gap-2 text-muted">
        <span aria-hidden="true" className="inline-block h-4 w-6 rounded-md border-2 border-warning bg-warning/10" />
        {mine > 0
          ? `${mine} thực thể được viền vàng là phần hệ thống đã dùng cho hồ sơ của bạn. Chọn một thực thể để xem bằng chứng làm căn cứ.`
          : "Hồ sơ này chưa dùng thực thể nào của đồ thị. Bạn vẫn có thể chọn một thực thể để xem các quan hệ của nó."}
      </p>
    </div>
  );
}

/** Thay cho đồ thị trên màn hẹp: cùng các thực thể, nhóm theo loại. */
function EntityList({ entities, selected, highlight, onSelect, className }: { entities: KbEntity[]; selected: string | null; highlight: Set<string>; onSelect: (id: string) => void; className?: string }) {
  return (
    <div className={clsx("space-y-4", className)}>
      {KB_COLUMNS.map((column) => (
        <div key={column.label}>
          <h3 className="text-sm font-semibold text-muted">{column.title}</h3>
          <ul className="mt-2 flex flex-wrap gap-2">
            {entities.filter((e) => e.label === column.label).map((entity) => (
              <li key={entity.id}>
                <button
                  type="button"
                  aria-pressed={entity.id === selected}
                  onClick={() => onSelect(entity.id)}
                  className={clsx(
                    "min-h-11 rounded-xl border-2 px-3 py-1.5 text-left text-sm font-semibold",
                    entity.id === selected ? "border-info bg-infoSoft text-info" : highlight.has(entity.id) ? "border-warning bg-warning/10 text-ink" : "border-borderSoft bg-panel text-ink hover:border-info/50",
                  )}
                >
                  {entity.name}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

type Group = { key: string; relation: string; outgoing: boolean; otherId: string; otherName: string; rows: KbEvidenceRow[] };

function EntityDetail({ graph, entityId, usedEvidence, onSelect }: { graph: KbGraphData; entityId: string; usedEvidence: Set<string>; onSelect: (id: string) => void }) {
  const entity = graph.entities.find((e) => e.id === entityId);
  const detail = useQuery({ queryKey: ["kb-entity", entityId], queryFn: () => fetchKbEntity(entityId) });

  const groups = useMemo(() => {
    const map = new Map<string, Group>();
    for (const row of detail.data?.relations ?? []) {
      const key = `${row.relation}|${row.outgoing}|${row.other_id}`;
      const group = map.get(key) ?? { key, relation: row.relation, outgoing: row.outgoing, otherId: row.other_id, otherName: row.other_name, rows: [] };
      group.rows.push(row);
      map.set(key, group);
    }
    const list = [...map.values()];
    for (const group of list) group.rows.sort((a, b) => Number(usedEvidence.has(b.evidence_id)) - Number(usedEvidence.has(a.evidence_id)));
    // Quan hệ có đoạn bằng chứng đã dùng cho hồ sơ này lên trước.
    return list.sort((a, b) => Number(b.rows.some((r) => usedEvidence.has(r.evidence_id))) - Number(a.rows.some((r) => usedEvidence.has(r.evidence_id))));
  }, [detail.data, usedEvidence]);

  if (!entity) return null;
  const column = KB_COLUMNS.find((c) => c.label === entity.label);

  return (
    <section aria-labelledby="entity-title" className="border-t border-borderSoft pt-6">
      <h3 id="entity-title" className="text-xl font-bold">{entity.name}</h3>
      <p className="mt-1 text-sm text-muted">
        {column?.title ?? entity.label}
        {entity.key ? ` · khớp đặc trưng mô hình "${entity.key}"` : ""}
      </p>
      {entity.description ? <p className="mt-3 max-w-prose text-base leading-relaxed">{entity.description}</p> : null}

      <div className="mt-6">
        {detail.isPending ? (
          <p role="status" className="flex items-center gap-2 text-sm font-semibold text-info">
            <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> Đang đọc quan hệ và bằng chứng…
          </p>
        ) : detail.isError ? (
          <p role="alert" className="text-sm font-semibold text-danger">{detail.error.message}</p>
        ) : groups.length === 0 ? (
          <p className="text-sm text-muted">Thực thể này chưa có quan hệ nào kèm bằng chứng.</p>
        ) : (
          <ul className="divide-y divide-borderSoft border-y border-borderSoft">
            {groups.map((group) => {
              const text = RELATION_TEXT[group.relation];
              const phrase = text ? (group.outgoing ? text.outgoing : text.incoming) : group.relation;
              const usedCount = group.rows.filter((r) => usedEvidence.has(r.evidence_id)).length;
              return (
                <li key={group.key} className="py-3">
                  <details>
                    <summary className="cursor-pointer list-none text-base [&::-webkit-details-marker]:hidden">
                      <span className="text-muted">{entity.name} </span>
                      <span className={clsx("font-semibold", text?.tone)}>{phrase}</span>{" "}
                      <span className="font-semibold">{group.otherName}</span>
                      <span className="ml-2 text-sm text-muted">· {group.rows.length} đoạn bằng chứng</span>
                      {usedCount > 0 ? <span className="ml-2 text-sm font-semibold text-warning">· {usedCount} đoạn đã dùng cho hồ sơ của bạn</span> : null}
                    </summary>
                    <div className="mt-3 space-y-3">
                      <ul className="space-y-3">
                        {group.rows.map((row) => (
                          <li key={row.evidence_id}>
                            <blockquote className={clsx("rounded-lg p-3 text-sm leading-6", usedEvidence.has(row.evidence_id) ? "bg-warning/10" : "bg-canvas")}>
                              {usedEvidence.has(row.evidence_id) ? <p className="mb-1 text-xs font-semibold text-warning">Đã dùng cho hồ sơ của bạn</p> : null}
                              {row.evidence}
                              <footer className="mt-1 text-xs text-muted">
                                <CitationLink citation={{ evidence_id: row.evidence_id, text: row.evidence, source_title: row.source_title, publisher: row.publisher, year: row.year, url: row.url }} />
                              </footer>
                            </blockquote>
                          </li>
                        ))}
                      </ul>
                      <button type="button" onClick={() => onSelect(group.otherId)} className="min-h-11 text-sm font-semibold text-info underline-offset-4 hover:underline">
                        Xem {group.otherName}
                      </button>
                    </div>
                  </details>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}
