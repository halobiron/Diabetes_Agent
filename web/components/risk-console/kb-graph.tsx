import clsx from "clsx";

import type { KbEntity, KbRelation } from "@/types/healthcare";

/** Thứ tự cột: can thiệp xử lý yếu tố nguy cơ, yếu tố nguy cơ dẫn tới bệnh, xét nghiệm chẩn đoán bệnh. */
export const KB_COLUMNS = [
  { label: "Intervention", title: "Can thiệp" },
  { label: "RiskFactor", title: "Yếu tố nguy cơ" },
  { label: "Condition", title: "Bệnh và tình trạng" },
  { label: "Test", title: "Xét nghiệm" },
] as const;

export const RELATION_TEXT: Record<string, { outgoing: string; incoming: string; short: string; tone: string }> = {
  INCREASES_RISK_OF: { outgoing: "làm tăng nguy cơ", incoming: "chịu nguy cơ tăng do", short: "tăng nguy cơ", tone: "text-danger" },
  REDUCES_RISK_OF: { outgoing: "giúp giảm nguy cơ", incoming: "được giảm nguy cơ nhờ", short: "giảm nguy cơ", tone: "text-success" },
  ADDRESSES: { outgoing: "giúp cải thiện", incoming: "được cải thiện nhờ", short: "cải thiện", tone: "text-success" },
  DIAGNOSES: { outgoing: "dùng để chẩn đoán", incoming: "được chẩn đoán bằng", short: "chẩn đoán", tone: "text-info" },
  SHOULD_TEST_WITH: { outgoing: "nên xét nghiệm bằng", incoming: "là lý do nên làm", short: "nên xét nghiệm", tone: "text-info" },
};

const NODE_W = 200;
const NODE_H = 46;
const ROW = 58;
const COL_X = [10, 270, 530, 790];
const TOP = 36;

type Placed = { entity: KbEntity; x: number; y: number; column: number };

function place(entities: KbEntity[]) {
  const rows = Math.max(...KB_COLUMNS.map((c) => entities.filter((e) => e.label === c.label).length), 1);
  const height = TOP + rows * ROW + 4;
  const placed = new Map<string, Placed>();
  KB_COLUMNS.forEach((column, index) => {
    const items = entities.filter((e) => e.label === column.label);
    const offset = TOP + ((rows - items.length) * ROW) / 2;
    items.forEach((entity, row) => placed.set(entity.id, { entity, x: COL_X[index], y: offset + row * ROW, column: index }));
  });
  return { placed, height };
}

function edgePath(a: Placed, b: Placed) {
  const ay = a.y + NODE_H / 2;
  const by = b.y + NODE_H / 2;
  if (a.column === b.column) {
    const x = a.x + NODE_W;
    return `M ${x} ${ay} C ${x + 70} ${ay}, ${x + 70} ${by}, ${x} ${by}`;
  }
  const forward = a.column < b.column;
  const ax = forward ? a.x + NODE_W : a.x;
  const bx = forward ? b.x : b.x + NODE_W;
  const bend = Math.abs(bx - ax) / 2;
  const dir = forward ? 1 : -1;
  return `M ${ax} ${ay} C ${ax + dir * bend} ${ay}, ${bx - dir * bend} ${by}, ${bx} ${by}`;
}

/** Đồ thị tri thức dạng bốn cột. Chọn một nút để làm nổi các quan hệ của nó. */
export function KbGraph({
  entities,
  relations,
  selected,
  highlight,
  onSelect,
}: {
  entities: KbEntity[];
  relations: KbRelation[];
  selected: string | null;
  highlight: Set<string>;
  onSelect: (id: string) => void;
}) {
  const { placed, height } = place(entities);
  const linked = new Set<string>();
  if (selected) {
    for (const r of relations) {
      if (r.from === selected) linked.add(r.to);
      if (r.to === selected) linked.add(r.from);
    }
  }

  return (
    <svg viewBox={`0 0 1000 ${height}`} className="w-full" role="group" aria-label="Đồ thị tri thức: thực thể và quan hệ">
      {KB_COLUMNS.map((column, index) => (
        <text key={column.label} x={COL_X[index] + NODE_W / 2} y={18} textAnchor="middle" className="fill-muted text-[13px] font-semibold">
          {column.title}
        </text>
      ))}

      <g fill="none">
        {relations.map((relation) => {
          const a = placed.get(relation.from);
          const b = placed.get(relation.to);
          if (!a || !b) return null;
          const active = selected !== null && (relation.from === selected || relation.to === selected);
          const tone = RELATION_TEXT[relation.type]?.tone ?? "text-muted";
          return (
            <path
              key={`${relation.from}-${relation.type}-${relation.to}`}
              d={edgePath(a, b)}
              stroke="currentColor"
              className={clsx(tone, active ? "opacity-90" : selected ? "opacity-10" : "opacity-35")}
              strokeWidth={active ? 2.5 : 1.5}
            />
          );
        })}
      </g>

      {[...placed.values()].map(({ entity, x, y }) => {
        const isSelected = entity.id === selected;
        const isLinked = linked.has(entity.id);
        const isMine = highlight.has(entity.id);
        return (
          <foreignObject key={entity.id} x={x} y={y} width={NODE_W} height={NODE_H}>
            <button
              type="button"
              onClick={() => onSelect(entity.id)}
              aria-pressed={isSelected}
              className={clsx(
                "flex h-full w-full items-center justify-center rounded-xl border-2 px-2 text-center text-[13px] font-semibold leading-tight focus-visible:outline focus-visible:outline-2 focus-visible:outline-info",
                isSelected ? "border-info bg-infoSoft text-info" : isMine ? "border-warning bg-warning/10 text-ink" : isLinked ? "border-info/50 bg-panel text-ink" : "border-borderSoft bg-panel text-ink hover:border-info/50",
              )}
            >
              {entity.name}
            </button>
          </foreignObject>
        );
      })}
    </svg>
  );
}
