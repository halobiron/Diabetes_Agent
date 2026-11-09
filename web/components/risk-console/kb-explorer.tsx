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
        <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> Đang đọc…
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
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted">
      <span className={clsx("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-semibold", live ? "border-success/40 bg-success/10 text-success" : "border-warning/40 bg-warning/10 text-warning")}>
        <Database aria-hidden="true" className="h-3.5 w-3.5" />
        {live ? "Neo4j" : "File KB dự phòng"}
      </span>
      <span className="tabular-nums">{graph.entities.length} thực thể · {graph.relations.length} quan hệ · {graph.evidence_count} đoạn · {graph.source_count} nguồn</span>
      {mine > 0 ? (
        <span className="flex items-center gap-1.5">
          <span aria-hidden="true" className="inline-block h-3.5 w-5 rounded border-2 border-warning bg-warning/10" />
          Viền vàng: đã dùng cho bạn ({mine})
        </span>
      ) : null}
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
    <section aria-labelledby="entity-title" className="border-t border-borderSoft pt-4">
      <div className="flex flex-wrap items-center gap-2">
        <h3 id="entity-title" className="text-lg font-bold">{entity.name}</h3>
        <span className="rounded-full bg-infoSoft px-2 py-0.5 text-xs font-semibold text-info">{column?.title ?? entity.label}</span>
      </div>
      {entity.description ? <p className="mt-2 max-w-prose text-sm leading-6 text-muted">{entity.description}</p> : null}

      <div className="mt-3">
        {detail.isPending ? (
          <p role="status" className="flex items-center gap-2 text-sm font-semibold text-info">
            <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> Đang đọc…
          </p>
        ) : detail.isError ? (
          <p role="alert" className="text-sm font-semibold text-danger">{detail.error.message}</p>
        ) : groups.length === 0 ? (
          <p className="text-sm text-muted">Chưa có quan hệ nào kèm bằng chứng.</p>
        ) : (
          <ul className="divide-y divide-borderSoft border-y border-borderSoft">
            {groups.map((group) => {
              const text = RELATION_TEXT[group.relation];
              const phrase = text ? (group.outgoing ? text.outgoing : text.incoming) : group.relation;
              const usedCount = group.rows.filter((r) => usedEvidence.has(r.evidence_id)).length;
              return (
                <li key={group.key} className="py-2.5">
                  <details>
                    <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-2 gap-y-1 text-sm [&::-webkit-details-marker]:hidden">
                      <span className={clsx("font-semibold", text?.tone)}>{phrase}</span>
                      <span className="font-semibold">{group.otherName}</span>
                      <span className="rounded-full bg-canvas px-2 py-0.5 text-xs tabular-nums text-muted">{group.rows.length} đoạn</span>
                      {usedCount > 0 ? <span className="rounded-full bg-warning/15 px-2 py-0.5 text-xs font-semibold text-warning">{usedCount} đã dùng</span> : null}
                    </summary>
                    <div className="mt-3 space-y-3">
                      <ul className="space-y-3">
                        {group.rows.map((row) => (
                          <li key={row.evidence_id}>
                            <blockquote className={clsx("rounded-lg p-3 text-sm leading-6", usedEvidence.has(row.evidence_id) ? "bg-warning/10" : "bg-canvas")}>
                              {usedEvidence.has(row.evidence_id) ? <p className="mb-1 text-xs font-semibold text-warning">Đã dùng cho bạn</p> : null}
                              {row.evidence}
                              <footer className="mt-1 text-xs text-muted">
                                <CitationLink citation={{ evidence_id: row.evidence_id, text: row.evidence, source_title: row.source_title, publisher: row.publisher, year: row.year, url: row.url }} />
                              </footer>
                            </blockquote>
                          </li>
                        ))}
                      </ul>
                      <button type="button" onClick={() => onSelect(group.otherId)} className="min-h-11 text-sm font-semibold text-info underline-offset-4 hover:underline">
                        Đi tới {group.otherName} →
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
