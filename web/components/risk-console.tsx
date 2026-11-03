"use client";

import { QueryClient, QueryClientProvider, useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { createPrediction, getHistory } from "@/lib/api";
import type { PatientInput, PredictionResult } from "@/types/healthcare";

import { Assessment } from "./risk-console/assessment";
import { DEFAULT_INPUT } from "./risk-console/constants";
import { EmptyState } from "./risk-console/empty-state";
import { Evidence } from "./risk-console/evidence";
import { Hero } from "./risk-console/hero";
import { History } from "./risk-console/history";
import { ModelStrip } from "./risk-console/model-strip";
import { MeasurementScales } from "./risk-console/measurement-scales";
import { FollowupChange, NextQuestion } from "./risk-console/next-question";
import { PatientSidebar } from "./risk-console/sidebar";
import { Tabs } from "./risk-console/tabs";
import type { TabKey } from "./risk-console/types";
import { calculateBmi } from "./risk-console/utils";

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
  const [activeTab, setActiveTab] = useState<TabKey>("assessment");
  const [lastResult, setLastResult] = useState<PredictionResult | null>(null);
  const [lastInput, setLastInput] = useState<PatientInput | null>(null);
  const [updatedFrom, setUpdatedFrom] = useState<PredictionResult | null>(null);

  const mutation = useMutation({
    mutationFn: createPrediction,
    onSuccess: (result, input) => {
      setLastResult(result);
      setLastInput(input);
      setActiveTab("assessment");
      void queryClient.invalidateQueries({ queryKey: ["history"] });
    },
  });

  const result = lastResult;
  const historyQuery = useQuery({
    queryKey: ["history", result?.request_id],
    queryFn: () => getHistory(25),
    enabled: Boolean(result),
  });
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
    const input = { ...lastInput, ...answer };
    setUpdatedFrom(result);
    setForm(input);
    mutation.mutate(input);
  }

  return (
    <main className="min-h-screen bg-canvas text-ink">
      <div className="grid min-h-screen grid-cols-1 xl:grid-cols-[420px_1fr]">
        <PatientSidebar
          form={form}
          calculatedBmi={calculatedBmi}
          isPending={mutation.isPending}
          error={mutation.error}
          onSubmit={submit}
          onFieldChange={updateField}
        />

        <section className="min-w-0 px-5 py-6 md:px-8 lg:px-10">
          <div className="mx-auto flex max-w-7xl flex-col gap-6">
            <Hero result={result} />
            {result ? (
              <>
                <ModelStrip result={result} />
                <Tabs activeTab={activeTab} onChange={setActiveTab} />
                {activeTab === "assessment" ? (
                  <>
                    {updatedFrom && updatedFrom !== result ? <FollowupChange before={updatedFrom} after={result} /> : null}
                    {result.followup ? <NextQuestion key={`${result.request_id ?? "result"}:${result.followup.id}`} question={result.followup} pending={mutation.isPending} error={mutation.error} onAnswer={answerQuestion} /> : null}
                    {result.patient.glucose_unavailable ? <p role="status" className="text-sm text-muted">Đã ghi nhận bạn chưa có kết quả đường huyết. Hệ thống không hỏi lại trong hồ sơ này; bạn vẫn có thể bổ sung ở phần thông tin bệnh nhân.</p> : null}
                    <MeasurementScales scales={result.measurement_scales ?? []} />
                  </>
                ) : null}
                {activeTab === "assessment" ? <Assessment result={result} /> : null}
                {activeTab === "evidence" ? <Evidence result={result} /> : null}
                {activeTab === "history" ? (
                  <History
                    result={result}
                    records={historyQuery.data?.records ?? []}
                    isLoading={historyQuery.isLoading}
                  />
                ) : null}
              </>
            ) : (
              <EmptyState />
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
