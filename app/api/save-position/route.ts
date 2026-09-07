import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export async function POST(req: NextRequest) {
  try {
    const { year, id, position }: { year: number; id: string; position: string | null } =
      await req.json();

    if (!year || !id) {
      return NextResponse.json({ error: "Invalid payload" }, { status: 400 });
    }

    const filePath = path.join(process.cwd(), "data", "prospects", `${year}.json`);
    const prospects = JSON.parse(fs.readFileSync(filePath, "utf-8"));

    const idx = prospects.findIndex((p: { id: string }) => p.id === id);
    if (idx === -1) {
      return NextResponse.json({ error: "Prospect not found" }, { status: 404 });
    }

    prospects[idx].position = position;
    fs.writeFileSync(filePath, JSON.stringify(prospects, null, 2), "utf-8");

    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: "Failed to save" }, { status: 500 });
  }
}
