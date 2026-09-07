import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { Prospect } from "@/lib/data";

export async function POST(req: NextRequest) {
  try {
    const { year, prospects }: { year: number; prospects: Prospect[] } = await req.json();

    if (!year || !Array.isArray(prospects)) {
      return NextResponse.json({ error: "Invalid payload" }, { status: 400 });
    }

    // Re-assign ranks based on the order received
    const reranked = prospects.map((p, i) => ({ ...p, rank: i + 1 }));

    const filePath = path.join(process.cwd(), "data", "prospects", `${year}.json`);
    fs.writeFileSync(filePath, JSON.stringify(reranked, null, 2), "utf-8");

    return NextResponse.json({ ok: true, count: reranked.length });
  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: "Failed to save" }, { status: 500 });
  }
}
