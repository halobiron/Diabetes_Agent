"use client";

import { EMPTY_SYMPTOMS, SYMPTOM_QUESTIONS } from "@/lib/symptoms";
import type { PatientInput } from "@/types/healthcare";

import { Choice } from "./inputs";
import type { PatientFieldChange } from "./types";

export function SymptomQuestions({ form, set, second = false }: {
  form: PatientInput; set: PatientFieldChange; second?: boolean;
}) {
  const enabled = form.screening_mode === "symptoms";
  const questions = second ? SYMPTOM_QUESTIONS.slice(7) : SYMPTOM_QUESTIONS.slice(0, 7);
  return (
    <div className="space-y-5">
      {!second ? (
        <fieldset>
          <legend className="mb-2 text-sm font-semibold">Thông tin dùng để đánh giá</legend>
          <div className="grid gap-2 sm:grid-cols-2">
            <Choice active={enabled} onClick={() => set("screening_mode", "symptoms")}>Bổ sung triệu chứng</Choice>
            <Choice active={!enabled} onClick={() => set("screening_mode", "lifestyle")}>Chỉ dùng hồ sơ lối sống</Choice>
          </div>
        </fieldset>
      ) : null}
      {enabled ? (
        <>
          <p className="text-sm leading-relaxed text-muted">Chọn Có hoặc Không cho từng mục theo thông tin bạn biết. Nếu chưa rõ, hãy giữ Chưa rõ; hệ thống sẽ không tự coi đó là Không.</p>
          <div className="divide-y divide-borderSoft">
            {questions.map(([key, label]) => (
              <fieldset key={key} className="py-4 first:pt-0 last:pb-0">
                <legend className="mb-2 text-base font-semibold">{label}</legend>
                <div className="grid grid-cols-3 gap-2">
                  {([[true, "Có"], [false, "Không"], [null, "Chưa rõ"]] as const).map(([value, text]) => (
                    <Choice key={text} active={(form.symptoms?.[key] ?? null) === value} onClick={() => set("symptoms", { ...EMPTY_SYMPTOMS, ...form.symptoms, [key]: value })}>{text}</Choice>
                  ))}
                </div>
              </fieldset>
            ))}
          </div>
        </>
      ) : <p className="text-sm leading-relaxed text-muted">Bạn đang chọn hồ sơ lối sống. Nhánh này chỉ dùng thông tin sức khỏe và lối sống, không dùng các câu trả lời triệu chứng để tính điểm.</p>}
    </div>
  );
}
