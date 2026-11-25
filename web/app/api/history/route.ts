import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = searchParams.get("limit") ?? "25";
  const query = new URLSearchParams({ limit });
  const patientId = searchParams.get("patient_id");
  if (patientId) query.set("patient_id", patientId);
  const headers: HeadersInit = {};

  if (process.env.API_TOKEN) {
    headers.Authorization = `Bearer ${process.env.API_TOKEN}`;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/v1/history?${query}`, {
      headers,
      cache: "no-store",
    });
    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  } catch {
    const message = "Không kết nối được dịch vụ lưu trữ. Vui lòng kiểm tra backend và thử lại.";
    return NextResponse.json({ detail: message }, { status: 502 });
  }
}
