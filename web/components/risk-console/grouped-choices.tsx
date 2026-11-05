import type { PatientInput } from "@/types/healthcare";

import { Chip } from "./inputs";
import type { PatientFieldChange } from "./types";

type TriKey = "high_chol" | "stroke" | "heart_disease_or_attack" | "diff_walk" | "smoker" | "heavy_alcohol_consump" | "phys_activity" | "fruits" | "veggies";
export type GroupItem = { key: TriKey; label: string; good?: boolean };

export const HISTORY: GroupItem[] = [
  { key: "high_chol", label: "Cholesterol cao" },
  { key: "stroke", label: "Từng bị đột quỵ" },
  { key: "heart_disease_or_attack", label: "Bệnh tim hoặc nhồi máu" },
  { key: "diff_walk", label: "Khó đi lại, leo cầu thang" },
];

export const HABITS: GroupItem[] = [
  { key: "smoker", label: "Hút thuốc" },
  { key: "heavy_alcohol_consump", label: "Uống nhiều rượu bia" },
  { key: "phys_activity", label: "Vận động thường xuyên", good: true },
  { key: "fruits", label: "Ăn trái cây hằng ngày", good: true },
  { key: "veggies", label: "Ăn rau hằng ngày", good: true },
];

/**
 * Một lần chọn nhiều ô cho cả nhóm. Chưa chạm gì thì cả nhóm là "Chưa rõ";
 * lần chạm đầu tiên coi như bạn đã trả lời cả nhóm, các ô còn lại thành "Không".
 */
export function ChipGroup({ items, form, set, noneLabel, onChange }: { items: GroupItem[]; form: PatientInput; set: PatientFieldChange; noneLabel: string; onChange: (next: PatientInput) => void }) {
  const touched = items.some((i) => form[i.key] !== null);
  const allFalse = touched && items.every((i) => form[i.key] === false);
  const apply = (patch: Partial<Record<TriKey, boolean | null>>) => {
    const next = { ...form } as PatientInput;
    for (const [key, value] of Object.entries(patch) as Array<[TriKey, boolean | null]>) {
      set(key, value);
      (next as Record<string, unknown>)[key] = value;
    }
    if (patch.high_chol !== undefined && patch.high_chol !== null) set("chol_check", true);
    onChange(next);
  };
  const toggle = (key: TriKey) => {
    if (!touched) {
      apply(Object.fromEntries(items.map((i) => [i.key, i.key === key])) as Record<TriKey, boolean>);
    } else {
      apply({ [key]: !form[key] } as Partial<Record<TriKey, boolean>>);
    }
  };
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <Chip key={item.key} active={form[item.key] === true} onClick={() => toggle(item.key)}>
            {item.label}
          </Chip>
        ))}
      </div>
      <div className="flex flex-wrap gap-2 border-t border-borderSoft pt-4">
        <Chip active={allFalse} onClick={() => apply(Object.fromEntries(items.map((i) => [i.key, false])) as Record<TriKey, boolean>)}>
          {noneLabel}
        </Chip>
        <Chip active={!touched} onClick={() => apply(Object.fromEntries(items.map((i) => [i.key, null])) as Record<TriKey, null>)}>
          Chưa rõ
        </Chip>
      </div>
    </div>
  );
}

