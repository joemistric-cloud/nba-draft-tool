import { NextRequest, NextResponse } from "next/server";
import { findPlayerByName } from "@/lib/data";

export async function GET(req: NextRequest) {
  const name = req.nextUrl.searchParams.get("name");
  if (!name) return NextResponse.json(null);
  const player = findPlayerByName(name);
  return NextResponse.json(player);
}
