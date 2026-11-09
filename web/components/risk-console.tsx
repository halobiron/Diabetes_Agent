"use client";

import { QueryClient, QueryClientProvider, useMutation } from "@tanstack/react-query";
import { ArrowLeft, Stethoscope } from "lucide-react";
import { useState } from "react";

import { createPrediction } from "@/lib/api";
import type { AskableField, PatientInput, PredictionResult } from "@/types/healthcare";

import { Avatar, CAST, type CastId } from "./risk-console/agents";
import { Assessment } from "./risk-console/assessment";
import { ChatPanel } from "./risk-console/chat";
import { DEFAULT_INPUT } from "./risk-console/constants";
import { Hero } from "./risk-console/hero";
import { InputReview } from "./risk-console/input-review";
import { missingFollowupFields } from "./risk-console/followup-fields";
import { GroupedFollowup } from "./risk-console/grouped-followup";
import { FollowupChange, NextQuestion } from "./risk-console/next-question";
import { calculateBmi } from "./risk-console/utils";
import { Intake } from "./risk-console/intake";

const queryClient = new QueryClient();

export function RiskConsole() {
  return (
    <QueryClientProvider client={queryClient}>
      <RiskConsoleInner />
    </QueryClientProvider>
  );
}

function RiskConsoleInner() {
  const [form, setForm] = useState<PatientInput>(DEFAULT_INPUT);
  const [view, setView] = useState<"form" | "result">("form");
  const [lastResult, setLastResult] = useState<PredictionResult | null>(null);
  const [lastInput, setLastInput] = useState<PatientInput | null>(null);
  const [updatedFrom, setUpdatedFrom] = useState<PredictionResult | null>(null);
  const [editStep, setEditStep] = useState<string | null>(null);
  const [confirmedMeasurements, setConfirmedMeasurements] = useState<string[]>([]);

  const mutation = useMutation({
    mutationFn: createPrediction,
    onSuccess: (result, input) => {
      setLastResult(result);
      setLastInput(input);
      setView("result");
      window.scrollTo({ top: 0 });
    },
  });

  const result = lastResult;
  const groupedFields = result ? missingFollowupFields(result) : [];
  const calculatedBmi = calculateBmi(form.height_cm, form.weight_kg);

  function updateField<K extends keyof PatientInput>(key: K, value: PatientInput[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function submit() {
    setUpdatedFrom(null);
    mutation.mutate(form);
  }

  function answerQuestion(answer: Partial<PatientInput>) {
    if (!lastInput || !result || mutation.isPending) return;
    const skipped = [...new Set([...(lastInput.skipped_fields ?? []), ...(answer.skipped_fields ?? [])])]
      .filter((field) => typeof answer[field as AskableField] !== "boolean");
    const input = { ...lastInput, ...answer, skipped_fields: skipped };
    setUpdatedFrom(result);
    setForm(input);
    mutation.mutate(input);
  }

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <div className="bg-info text-onAccent">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-5">
          <div className="flex items-center gap-2 text-lg font-bold">
            <Stethoscope aria-hidden="true" className="h-6 w-6" />
            Sức khỏe AI
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-[#e4e0fa] sm:inline">Nguyên mẫu học tập · không thay tư vấn y tế</span>
            <div aria-hidden="true" className="flex -space-x-2">
              {(["tiep", "mo", "nho", "chung", "luat", "goi"] as CastId[]).map((id) => (
                <Avatar key={id} id={id} size={30} className="rounded-full ring-2 ring-info" />
              ))}
            </div>
          </div>
        </div>
      </div>

      {mutation.isPending && view === "form" ? <WorkingOverlay /> : null}

      {view === "form" || !result ? (
        <div className="mx-auto grid w-full max-w-6xl lg:grid-cols-[minmax(0,40rem)_minmax(20rem,1fr)] lg:gap-10">
          <Intake
            initialStep={editStep}
            form={form}
            calculatedBmi={calculatedBmi}
            isPending={mutation.isPending}
            error={mutation.error}
            hasResult={result !== null}
            onSubmit={submit}
            onFieldChange={updateField}
            onCancel={() => setView("result")}
          />
          <aside className="mx-auto w-full max-w-2xl px-5 pb-16 lg:sticky lg:top-6 lg:max-w-none lg:self-start lg:pl-0 lg:pr-5 lg:pt-8">
            <ChatPanel dockOnWide />
          </aside>
        </div>
      ) : (
        <main className="mx-auto flex max-w-6xl flex-col gap-5 px-5 py-6" aria-busy={mutation.isPending}>
          <button type="button" onClick={() => { setEditStep(null); setView("form"); }} className="flex min-h-11 w-fit items-center gap-2 text-sm font-semibold text-info underline-offset-4 hover:underline">
            <ArrowLeft aria-hidden="true" className="h-4 w-4" /> Xem hồ sơ đã nhập
          </button>
          <Hero result={result} />
          <InputReview
            result={result}
            coveredFields={groupedFields.map(({ feature }) => feature)}
            confirmed={confirmedMeasurements}
            onConfirm={(signature) => setConfirmedMeasurements((current) => current.includes(signature) ? current : [...current, signature])}
            onEdit={(step) => { setEditStep(step); setView("form"); window.scrollTo({ top: 0 }); }}
          />
          {mutation.isPending ? (
            <p role="status" className="flex items-center gap-3 text-sm font-semibold text-info">
              <Avatar id="mo" size={32} working /> Ông Mô và cả đội đang tính lại kết quả…
            </p>
          ) : null}
          {updatedFrom && updatedFrom !== result ? <FollowupChange before={updatedFrom} after={result} /> : null}
          {groupedFields.length > 0 ? (
            <GroupedFollowup
              key={result.request_id ?? groupedFields.map(({ field }) => field).join(",")}
              result={result}
              input={lastInput ?? form}
              skipped={lastInput?.skipped_fields ?? []}
              pending={mutation.isPending}
              error={mutation.error}
              onAnswer={answerQuestion}
            />
          ) : result.followup ? (
            <NextQuestion
              key={`${result.request_id ?? "result"}:${result.followup.id}`}
              question={result.followup}
              pending={mutation.isPending}
              error={mutation.error}
              onAnswer={answerQuestion}
            />
          ) : null}
          <Assessment result={result} scales={result.measurement_scales ?? []} />
        </main>
      )}
    </div>
  );
}

const WORKING_STEPS: Array<{ id: CastId; line: string }> = [
  { id: "mo", line: "Tôi đang đọc hồ sơ và chấm điểm nguy cơ…" },
  { id: "nho", line: "Tôi lục lại những hồ sơ giống bạn…" },
  { id: "chung", line: "Tôi đang tìm bằng chứng y khoa liên quan…" },
  { id: "luat", line: "Tôi kiểm tra các số đo thực tế với luật an toàn…" },
  { id: "goi", line: "Tôi soạn lời khuyên phù hợp với bạn…" },
];

function WorkingOverlay() {
  return (
    <div role="status" aria-live="polite" className="fixed inset-0 z-20 grid place-items-center bg-canvas/90 px-5">
      <div className="paper w-full max-w-xl rounded-2xl border-2 border-borderSoft p-6 shadow-console md:p-8">
        <h2 className="text-2xl font-bold">Cả đội đang xem hồ sơ của bạn</h2>
        <ul className="mt-5 space-y-3">
          {WORKING_STEPS.map((step, i) => (
            <li key={step.id} className="rise flex items-center gap-3" style={{ animationDelay: `${i * 0.5}s` }}>
              <Avatar id={step.id} size={44} working />
              <div>
                <div className="text-sm font-semibold" style={{ color: CAST[step.id].ink }}>{CAST[step.id].name}</div>
                <div className="text-base">{step.line}</div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
