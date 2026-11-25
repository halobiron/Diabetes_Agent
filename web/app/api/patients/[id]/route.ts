import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const headers: HeadersInit = {};
  if (process.env.API_TOKEN) headers.Authorization = `Bearer ${process.env.API_TOKEN}`;
  try {
    const response = await fetch(`${API_BASE_URL}/v1/patients/${encodeURIComponent(id)}`, { headers, cache: "no-store" });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ detail: "Không kết nối được dịch vụ lưu trữ. Vui lòng thử lại." }, { status: 502 });
  }
}
