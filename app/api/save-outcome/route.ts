import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { Prospect } from "@/lib/types";

export async function POST(req: NextRequest) {
  try {
    const {
      id,
      draft_class,
      outcome,
      outcome_tags,
    }: {
      id: string;
      draft_class: number;
      outcome: string | null;
      outcome_tags: string[];
    } = await req.json();

    const filePath = path.join(
      process.cwd(),
      "data",
      "prospects",
      `${draft_class}.json`
    );

    if (!fs.existsSync(filePath)) {
      return NextResponse.json({ error: "Draft class not found" }, { status: 404 });
    }

    const prospects: Prospect[] = JSON.parse(fs.readFileSync(filePath, "utf-8"));
    const idx = prospects.findIndex((p) => p.id === id);

    if (idx === -1) {
      return NextResponse.json({ error: "Player not found" }, { status: 404 });
    }

    prospects[idx].outcome = outcome as Prospect["outcome"];
    prospects[idx].outcome_tags = outcome_tags ?? [];

    fs.writeFileSync(filePath, JSON.stringify(prospects, null, 2), "utf-8");

    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: "Failed to save" }, { status: 500 });
  }
}
