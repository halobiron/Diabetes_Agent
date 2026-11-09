import type { ChatReply, KbEntityDetail, KbGraph, PatientInput, PredictionResult } from "@/types/healthcare";

export async function createPrediction(input: PatientInput): Promise<PredictionResult> {
  const response = await fetch("/api/predict", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });

  const payload = await response.json();

  if (!response.ok) {
    const detail = typeof payload?.detail === "string" ? payload.detail : "Không thể phân tích hồ sơ. Vui lòng kiểm tra dữ liệu và thử lại.";
    throw new Error(detail);
  }

  return payload as PredictionResult;
}


export async function askQuestion(question: string): Promise<ChatReply> {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  const payload = await response.json();

  if (!response.ok) {
    const detail = typeof payload?.detail === "string" ? payload.detail : "Không thể trả lời câu hỏi lúc này. Vui lòng thử lại.";
    throw new Error(detail);
  }

  return payload as ChatReply;
}

async function getJson<T>(path: string, fallback: string): Promise<T> {
  const response = await fetch(path, { cache: "no-store" });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(typeof payload?.detail === "string" ? payload.detail : fallback);
  }
  return payload as T;
}

export function fetchKb(): Promise<KbGraph> {
  return getJson<KbGraph>("/api/kb", "Không đọc được cơ sở tri thức.");
}

export function fetchKbEntity(id: string): Promise<KbEntityDetail> {
  return getJson<KbEntityDetail>(`/api/kb/entities/${encodeURIComponent(id)}`, "Không đọc được chi tiết thực thể.");
}
