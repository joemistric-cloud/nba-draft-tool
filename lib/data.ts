import fs from "fs";
import path from "path";
import type { Prospect, Legend, AnyPlayer } from "./types";

export type { Prospect, Legend, AnyPlayer };
export { parseComps } from "./types";

export function getProspectsByClass(year: number): Prospect[] {
  const filePath = path.join(process.cwd(), "data", "prospects", `${year}.json`);
  if (!fs.existsSync(filePath)) return [];
  const raw = fs.readFileSync(filePath, "utf-8");
  const data = JSON.parse(raw) as Prospect[];
  return data.sort((a, b) => a.rank - b.rank);
}

export function getAllProspects(): Prospect[] {
  const dir = path.join(process.cwd(), "data", "prospects");
  if (!fs.existsSync(dir)) return [];
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".json"));
  return files.flatMap((file) => {
    const raw = fs.readFileSync(path.join(dir, file), "utf-8");
    return JSON.parse(raw) as Prospect[];
  });
}

export function getLegends(): Legend[] {
  const filePath = path.join(process.cwd(), "data", "legends.json");
  if (!fs.existsSync(filePath)) return [];
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw) as Legend[];
}

export function findPlayerByName(name: string): AnyPlayer | null {
  const query = name.trim().toLowerCase();

  const prospectMatch = getAllProspects().find(
    (p) => p.name.toLowerCase() === query
  );
  if (prospectMatch) return prospectMatch;

  const legendMatch = getLegends().find(
    (l) =>
      l.name.toLowerCase() === query ||
      l.aliases.some((a) => a.toLowerCase() === query)
  );
  return legendMatch ?? null;
}

export function formatHeight(inches: number | null): string {
  if (inches === null) return "—";
  const feet = Math.floor(inches / 12);
  const remaining = inches % 12;
  return `${feet}'${remaining % 1 === 0 ? remaining : remaining.toFixed(1)}"`;
}
