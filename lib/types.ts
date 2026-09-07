// Shared types — safe to import in both server and client components

export interface Measurements {
  height_no_shoes: number | null;
  height_with_shoes: number | null;
  wingspan: number | null;
  weight: number | null;
  hand_length: number | null;
  hand_width: number | null;
  standing_reach: number | null;
  vertical_no_step: number | null;
  vertical_max: number | null;
}

export interface Prospect {
  id: string;
  name: string;
  draft_class: number;
  rank: number;
  position: string | null;
  school: string;
  nationality: string | null;
  age: number | null;
  role: string | null;
  bust_risk: string | null;
  description: string | null;
  perceived_draft_range: string | null;
  comparisons: string | null;
  measurements: Measurements;
  stats: Record<string, unknown>;
  college_stats?: Record<string, number | string | null>;
  college_stats_all?: Record<string, number | string | null>[];
  notes: string;
  drafted: { pick: number; round: number | null; team: string } | null;
  outcome: "Hit" | "Solid" | "Mixed" | "Bust" | null;
  outcome_tags: string[];
  is_legend?: false;
}

export interface Legend {
  id: string;
  name: string;
  aliases: string[];
  is_legend: true;
  draft_year: number;
  position: string | null;
  school: string;
  nationality: string | null;
  description: string | null;
  comparisons: string | null;
  measurements: Measurements;
}

export type AnyPlayer = Prospect | Legend;

export function parseComps(raw: string | null): string[] {
  if (!raw) return [];
  return raw.split(",").map((s) => s.trim()).filter(Boolean);
}
