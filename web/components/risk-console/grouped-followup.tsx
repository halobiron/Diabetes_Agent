import { Loader2 } from "lucide-react";
import { useState, type FormEvent } from "react";

import type { PatientInput, PredictionResult } from "@/types/healthcare";

import { Avatar } from "./agents";
import { missingFollowupFields } from "./followup-fields";
import { InputScoreDetails } from "./input-review";
import { ChipGroup, HABITS, HISTORY } from "./grouped-choices";

export function GroupedFollowup({ result, input, skipped, pending, error, onAnswer }: {
  result: PredictionResult;
  input: PatientInput;
  skipped: string[];
  pending: boolean;
  error: Error | null;
  onAnswer: (answer: Partial<PatientInput>) => void;
}) {
  const fields = missingFollowupFields(result);
  const active = fields.filter(({ field }) => !skipped.includes(field));
  const [answers, setAnswers] = useState<PatientInput>(input);
  const hasAnswer = active.some(({ field }) => typeof answers[field] === "boolean");
  const groups = [...new Set(active.map(({ group }) => group))];

  function submit(event: FormEvent) {
    event.preventDefault();
    const patch: Partial<PatientInput> = {};
    const unknown: string[] = [];
    for (const { field } of active) {
      const value = answers[field];
      if (typeof value === "boolean") patch[field] = value;
      else unknown.push(field);
    }
    onAnswer({ ...patch, skipped_fields: unknown });
  }

  return (
    <section aria-labelledby="grouped-followup-title" className="rounded-2xl border border-borderSoft bg-panel p-4 sm:p-5">
      <div className="flex items-start gap-3">
        <Avatar id="goi" size={40} mood={pending ? "think" : "talk"} />
        <div className="min-w-0">
          <h2 id="grouped-followup-title" className="text-base font-bold">Bạn Gợi · Bổ sung thông tin trong một lượt</h2>
          <p className="mt-1 max-w-prose text-sm leading-relaxed text-muted">
            {active.length ? "Chọn tất cả những điều đúng với bạn, giống lúc điền hồ sơ, rồi cập nhật một lần." : "Bạn đã chọn chưa rõ hoặc bỏ qua các mục còn thiếu. Mình sẽ không hỏi lại các mục đó trong hồ sơ này."}
          </p>
          <p className="mt-1 max-w-prose text-sm leading-relaxed text-muted">Mục “Chưa rõ” vẫn dùng giá trị mặc định và không được hỏi lại sau khi bạn gửi. Bạn có thể bổ sung sau trong hồ sơ.</p>
        </div>
      </div>

      {active.length > 0 ? (
        <form onSubmit={submit} className="mt-4">
          <fieldset disabled={pending} className="min-w-0 space-y-5 disabled:opacity-60">
            <legend className="sr-only">Thông tin tiền sử và thói quen còn thiếu</legend>
            <p className="text-sm leading-relaxed text-muted">Trong nhóm đã trả lời, mục được chọn là Có, mục không chọn là Không. Chọn “Chưa rõ” nếu chưa thể trả lời cả nhóm.</p>
            {groups.map((group) => {
              const items = (group === "Tiền sử bệnh" ? HISTORY : HABITS)
                .filter(({ key }) => active.some(({ field }) => field === key));
              return (
                <fieldset key={group} className="min-w-0 border-t border-borderSoft pt-4">
                  <legend className="pr-3 text-sm font-bold">{group}</legend>
                  <ChipGroup
                    items={items}
                    form={answers}
                    set={(key, value) => setAnswers((current) => ({ ...current, [key]: value }))}
                    noneLabel="Không có điều nào"
                    onChange={setAnswers}
                  />
                </fieldset>
              );
            })}
            <div className="flex flex-wrap items-center gap-3">
              <button type="submit" disabled={!hasAnswer} className="btn-primary">
                {pending ? <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> : null} Cập nhật các câu trả lời
              </button>
              <button type="button" className="btn-secondary" onClick={() => onAnswer({ skipped_fields: active.map(({ field }) => field) })}>Bỏ qua các mục này</button>
              {pending ? <span role="status" className="text-sm text-muted">Đang tính lại kết quả…</span> : null}
            </div>
          </fieldset>
          {error ? <p role="alert" className="mt-3 text-sm text-danger">{error.message} Các lựa chọn của bạn vẫn được giữ để thử lại.</p> : null}
        </form>
      ) : <p role="status" className="mt-3 text-sm text-muted">Còn {fields.length} mục đang dùng giá trị mặc định.</p>}
      <InputScoreDetails result={result} />
    </section>
  );
}
