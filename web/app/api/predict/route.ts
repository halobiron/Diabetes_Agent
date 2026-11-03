import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export async function POST(request: Request) {
  const body = await request.json();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (process.env.API_TOKEN) {
    headers.Authorization = `Bearer ${process.env.API_TOKEN}`;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/v1/predict`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const payload = await response.json();

    return NextResponse.json(payload, { status: response.status });
  } catch {
    const message = "Không kết nối được dịch vụ phân tích. Vui lòng kiểm tra backend và thử lại.";
    return NextResponse.json({ detail: message }, { status: 502 });
  }
}
