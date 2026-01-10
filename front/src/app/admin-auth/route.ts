import { NextResponse } from "next/server";
export const runtime = "nodejs";

export async function POST(req: Request) {
  try {
    let username = "";
    let password = "";
    try {
      const form = await req.formData();
      username = String(form.get("username") || "");
      password = String(form.get("password") || "");
    } catch {
      const bodyText = await req.text();
      const params = new URLSearchParams(bodyText);
      username = params.get("username") || "";
      password = params.get("password") || "";
    }
    const valid = username === "Martin" && password === "SistemaIMAA12345";
    if (!valid) {
      return NextResponse.json({ ok: false, error: "invalid_credentials" }, { status: 401 });
    }
    return NextResponse.json({ ok: true }, { status: 200 });
  } catch {
    return NextResponse.json({ ok: false, error: "server_error" }, { status: 500 });
  }
}

