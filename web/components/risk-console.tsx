"use client";

import { QueryClient, QueryClientProvider, useMutation } from "@tanstack/react-query";
import { ChevronDown, Loader2, Stethoscope } from "lucide-react";
import { useState } from "react";

import { createPrediction } from "@/lib/api";
import type { PatientInput, PredictionResult } from "@/types/healthcare";

import { AgentTrace } from "./risk-console/agent-trace";
import { Assessment } from "./risk-console/assessment";
import { DEFAULT_INPUT } from "./risk-console/constants";
import { Hero } from "./risk-console/hero";
import { ModelStrip } from "./risk-console/model-strip";
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
    const skipped = [...(lastInput.skipped_fields ?? []), ...(answer.skipped_fields ?? [])];
    const input = { ...lastInput, ...answer, skipped_fields: skipped };
    setUpdatedFrom(result);
    setForm(input);
    mutation.mutate(input);
  }

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <div className="border-b border-borderSoft bg-panel">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-5">
          <div className="flex items-center gap-2 font-bold">
            <Stethoscope aria-hidden="true" className="h-5 w-5 text-info" />
            Sức khỏe AI
          </div>
          <span className="text-sm text-muted">Chạy cục bộ · Nguyên mẫu học tập</span>
        </div>
      </div>

      {view === "form" || !result ? (
        <Intake
          form={form}
          calculatedBmi={calculatedBmi}
          isPending={mutation.isPending}
          error={mutation.error}
          hasResult={result !== null}
          onSubmit={submit}
          onFieldChange={updateField}
          onCancel={() => setView("result")}
        />
      ) : (
        <main className="mx-auto flex max-w-6xl flex-col gap-6 px-5 py-8" aria-busy={mutation.isPending}>
          <Hero result={result} onEdit={() => setView("form")} />
          {mutation.isPending ? (
            <p role="status" className="flex items-center gap-2 text-sm text-muted">
              <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> Đang cập nhật kết quả…
            </p>
          ) : null}
          {updatedFrom && updatedFrom !== result ? <FollowupChange before={updatedFrom} after={result} /> : null}
          {result.followup ? (
            <NextQuestion
              key={`${result.request_id ?? "result"}:${result.followup.id}`}
              question={result.followup}
              pending={mutation.isPending}
              error={mutation.error}
              onAnswer={answerQuestion}
            />
          ) : null}
          {result.patient.glucose_unavailable ? (
            <p role="status" className="text-sm text-muted">
              Đã ghi nhận bạn chưa có kết quả đường huyết. Hệ thống không hỏi lại trong hồ sơ này; bạn vẫn có thể bổ sung ở phần chỉnh sửa hồ sơ.
            </p>
          ) : null}
          <Assessment result={result} scales={result.measurement_scales ?? []} />
          <Fold title="Chi tiết kỹ thuật" hint="Quy trình các agent và thông tin mô hình">
            <div className="space-y-8">
              <AgentTrace result={result} />
              <ModelStrip result={result} />
            </div>
          </Fold>
        </main>
      )}
    </div>
  );
}

function Fold({ title, hint, children }: { title: string; hint: string; children: React.ReactNode }) {
  return (
    <details className="group console-panel rounded-xl">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4 p-5 md:px-6 [&::-webkit-details-marker]:hidden">
        <span>
          <span className="block text-lg font-bold">{title}</span>
          <span className="block text-sm text-muted">{hint}</span>
        </span>
        <ChevronDown aria-hidden="true" className="h-5 w-5 shrink-0 text-muted transition group-open:rotate-180" />
      </summary>
      <div className="border-t border-borderSoft p-5 md:p-6">{children}</div>
    </details>
  );
}
