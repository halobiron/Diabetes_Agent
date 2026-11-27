"use client";

import clsx from "clsx";

import { EMPTY_SYMPTOMS, SYMPTOM_QUESTIONS, type SymptomInput } from "@/lib/symptoms";
import type { PatientInput } from "@/types/healthcare";

import type { PatientFieldChange } from "./types";

const OPTIONS = [
  [true, "Có"],
  [false, "Không"],
  [null, "Chưa rõ"],
] as const;

export function SymptomQuestions({ form, set }: {
  form: PatientInput;
  set: PatientFieldChange;
}) {
  const enabled = form.screening_mode === "symptoms";
  const current: SymptomInput = { ...EMPTY_SYMPTOMS, ...form.symptoms };
  const answered = SYMPTOM_QUESTIONS.filter(([key]) => typeof current[key] === "boolean").length;
  const total = SYMPTOM_QUESTIONS.length;

  function fillRemainingFalse() {
    const next = { ...current };
    for (const [key] of SYMPTOM_QUESTIONS) {
      if (typeof next[key] !== "boolean") next[key] = false;
    }
    set("symptoms", next);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div role="group" aria-label="Chế độ đánh giá" className="inline-grid grid-cols-2 rounded-2xl border border-borderSoft bg-panelMuted p-1">
          <button
            type="button"
            aria-pressed={enabled}
            onClick={() => set("screening_mode", "symptoms")}
            className={clsx(
              "min-h-10 rounded-xl px-3.5 text-sm font-semibold transition-colors",
              enabled ? "bg-panel text-info shadow-sm" : "text-muted hover:text-ink",
            )}
          >
            Bổ sung triệu chứng
          </button>
          <button
            type="button"
            aria-pressed={!enabled}
            onClick={() => set("screening_mode", "lifestyle")}
            className={clsx(
              "min-h-10 rounded-xl px-3.5 text-sm font-semibold transition-colors",
              !enabled ? "bg-panel text-info shadow-sm" : "text-muted hover:text-ink",
            )}
          >
            Chỉ lối sống
          </button>
        </div>
        {enabled ? (
          <span className="text-sm font-semibold tabular-nums text-muted">
            {answered}/{total} đã trả lời
          </span>
        ) : null}
      </div>

      {enabled ? (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
            <span>Mặc định là Chưa rõ (hệ thống không tự đổi thành Không).</span>
            <div className="flex flex-wrap gap-2">
              {answered < total ? (
                <button
                  type="button"
                  onClick={fillRemainingFalse}
                  className="rounded-lg border border-borderSoft bg-panel px-2.5 py-1 font-semibold text-ink hover:border-info/50 hover:text-info"
                >
                  {answered === 0 ? "Không có triệu chứng nào" : "Còn lại: Không"}
                </button>
              ) : null}
              {answered > 0 ? (
                <button
                  type="button"
                  onClick={() => set("symptoms", { ...EMPTY_SYMPTOMS })}
                  className="rounded-lg px-2 py-1 font-semibold text-muted hover:bg-panelMuted hover:text-ink"
                >
                  Đặt lại Chưa rõ
                </button>
              ) : null}
            </div>
          </div>

          <div className="divide-y divide-borderSoft rounded-2xl border border-borderSoft bg-panel px-3.5">
            {SYMPTOM_QUESTIONS.map(([key, label]) => {
              const val = current[key] ?? null;
              return (
                <div key={key} role="group" aria-label={label} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
                  <span className="text-sm font-medium text-ink sm:text-base">{label}</span>
                  <div className="inline-grid shrink-0 grid-cols-3 rounded-xl border border-borderSoft bg-panelMuted p-0.5">
                    {OPTIONS.map(([value, text]) => (
                      <button
                        key={text}
                        type="button"
                        aria-pressed={val === value}
                        onClick={() => set("symptoms", { ...current, [key]: value })}
                        className={clsx(
                          "min-h-9 rounded-lg px-2.5 text-xs font-semibold transition-colors sm:px-3 sm:text-sm",
                          val === value ? "bg-infoSoft text-info" : "text-muted hover:text-ink",
                        )}
                      >
                        {text}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      ) : (
        <p className="text-sm text-muted">
          Chỉ dùng hồ sơ sức khỏe và lối sống để đánh giá (không tính điểm triệu chứng).
        </p>
      )}
    </div>
  );
}
