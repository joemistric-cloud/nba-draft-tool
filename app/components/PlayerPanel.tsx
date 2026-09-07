"use client";

import { useState, useEffect, useCallback } from "react";
import Constellation from "./Constellation";
import { AnyPlayer, Prospect, parseComps } from "@/lib/types";
import { BUST_RISK_COLORS } from "@/lib/constants";

interface PlayerPanelProps {
  player: AnyPlayer;
  onClose: () => void;
}

// ── Stat formatting ──────────────────────────────────────────────────────────

function fmt(val: number | string | null | undefined, type: "pct" | "num" | "rate" | "int"): string {
  if (val == null || val === "") return "—";
  const n = typeof val === "string" ? parseFloat(val) : val;
  if (isNaN(n)) return "—";
  if (type === "pct")  return (n * 100).toFixed(1) + "%";
  if (type === "rate") return (n * 100).toFixed(1) + "%";
  if (type === "int")  return Math.round(n).toString();
  return n.toFixed(1);
}

function StatLine({
  title,
  stats,
}: {
  title: string;
  stats: { label: string; value: string }[];
}) {
  return (
    <div>
      <p className="text-[10px] text-gray-600 font-mono uppercase tracking-widest mb-1.5">
        {title}
      </p>
      <div className="border border-gray-800 rounded overflow-hidden">
        {/* Label row */}
        <div className="flex border-b border-gray-800 bg-gray-900/40">
          {stats.map((s) => (
            <div key={s.label} className="flex-1 text-center py-1.5">
              <span className="text-[10px] text-gray-500 font-mono uppercase tracking-wide">
                {s.label}
              </span>
            </div>
          ))}
        </div>
        {/* Value row */}
        <div className="flex">
          {stats.map((s) => {
            const empty = s.value === "—";
            return (
              <div key={s.label} className="flex-1 text-center py-2.5 border-r border-gray-800/50 last:border-r-0">
                <span className={`text-sm font-medium tabular-nums ${empty ? "text-gray-700" : "text-white"}`}>
                  {s.value}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function CollegeStats({ cs }: { cs: Record<string, number | string | null> }) {
  const school  = cs.school  ? String(cs.school)  : null;
  const team    = cs.team    ? String(cs.team)    : null;
  const league  = cs.league  ? String(cs.league)  : null;
  const season  = cs.season  ? String(cs.season)  : null;

  // Build context line: prefer school (college), fall back to team + league (international)
  const context = school ?? [team, league].filter(Boolean).join(" · ") ?? null;

  return (
    <div className="space-y-6">
      {(season || context) && (
        <p className="text-xs text-gray-500 font-mono -mt-2">
          {season}{season && context ? " · " : ""}{context}
        </p>
      )}

      <StatLine
        title="Per Game"
        stats={[
          { label: "G",    value: fmt(cs.g,          "int") },
          { label: "MIN",  value: fmt(cs.mp_per_g,   "num") },
          { label: "PTS",  value: fmt(cs.pts_per_g,  "num") },
          { label: "REB",  value: fmt(cs.trb_per_g,  "num") },
          { label: "ORB",  value: fmt(cs.orb_per_g,  "num") },
          { label: "AST",  value: fmt(cs.ast_per_g,  "num") },
          { label: "STL",  value: fmt(cs.stl_per_g,  "num") },
          { label: "BLK",  value: fmt(cs.blk_per_g,  "num") },
          { label: "TOV",  value: fmt(cs.tov_per_g,  "num") },
          { label: "PF",   value: fmt(cs.pf_per_g,   "num") },
        ]}
      />

      <StatLine
        title="Shooting & Efficiency"
        stats={[
          { label: "FG%",   value: fmt(cs.fg_pct,      "pct")  },
          { label: "2P%",   value: fmt(cs.fg2_pct,     "pct")  },
          { label: "3P%",   value: fmt(cs.fg3_pct,     "pct")  },
          { label: "3PA",   value: fmt(cs.fg3a_per_g,  "num")  },
          { label: "3PAr",  value: fmt(cs.fg3a_rate,   "rate") },
          { label: "FT%",   value: fmt(cs.ft_pct,      "pct")  },
          { label: "FTr",   value: fmt(cs.fta_rate,    "rate") },
          { label: "Rim%",  value: fmt(cs.rim_fg_pct,  "pct")  },
          { label: "RimFr", value: fmt(cs.rim_freq,    "rate") },
          { label: "TS%",   value: fmt(cs.ts_pct,      "pct")  },
          { label: "eFG%",  value: fmt(cs.efg_pct,     "pct")  },
          { label: "A/TO",  value: fmt(cs.ato_ratio,   "num")  },
        ]}
      />
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export default function PlayerPanel({ player, onClose }: PlayerPanelProps) {
  const [history, setHistory] = useState<AnyPlayer[]>([]);
  const [current, setCurrent] = useState<AnyPlayer>(player);
  const [inSystemSet, setInSystemSet] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setHistory([]);
    setCurrent(player);
  }, [player]);

  const comps = parseComps(current.comparisons);

  useEffect(() => {
    if (comps.length === 0) {
      setInSystemSet(new Set());
      return;
    }
    let cancelled = false;
    Promise.all(
      comps.map(async (comp) => {
        const res = await fetch(`/api/find-player?name=${encodeURIComponent(comp)}`);
        const data = await res.json();
        return data ? comp.trim().toLowerCase() : null;
      })
    ).then((results) => {
      if (cancelled) return;
      setInSystemSet(new Set(results.filter(Boolean) as string[]));
    });
    return () => { cancelled = true; };
  }, [current.id]);

  const handleCompClick = useCallback(
    async (compName: string) => {
      setLoading(true);
      const res = await fetch(`/api/find-player?name=${encodeURIComponent(compName)}`);
      const found: AnyPlayer | null = await res.json();
      setLoading(false);
      if (found) {
        setHistory((h) => [...h, current]);
        setCurrent(found);
      }
    },
    [current]
  );

  const handleBack = useCallback(() => {
    if (history.length === 0) return;
    setCurrent(history[history.length - 1]);
    setHistory((h) => h.slice(0, -1));
  }, [history]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const bustColor = "bust_risk" in current && current.bust_risk
    ? BUST_RISK_COLORS[current.bust_risk] ?? "bg-gray-800 text-gray-400"
    : null;

  const yearLabel = "draft_class" in current
    ? current.draft_class
    : "draft_year" in current
    ? current.draft_year
    : null;

  const collegeStats = "college_stats" in current
    ? (current as Prospect).college_stats ?? null
    : null;

  return (
    <>
      {/* Backdrop — sits behind both panels */}
      <div
        className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* LEFT PANEL — stats, left half of screen */}
      <div className="fixed left-0 top-0 h-full w-1/2 z-50 bg-gray-950/95 border-r border-gray-800 overflow-y-auto">
        <div className="px-8 py-8 max-w-2xl mx-auto">

          {/* Player name + school */}
          <div className="mb-5">
            <h2 className="text-2xl font-bold text-white">{current.name}</h2>
            <p className="text-gray-400 text-sm mt-1">{current.school}</p>
          </div>

          {/* Badges */}
          <div className="flex flex-wrap gap-2 mb-6">
            {current.position && (
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-800 text-gray-300">
                {current.position}
              </span>
            )}
            {"bust_risk" in current && current.bust_risk && bustColor && (
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${bustColor}`}>
                {current.bust_risk}
              </span>
            )}
            {"perceived_draft_range" in current && current.perceived_draft_range && (
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-800 text-gray-400 font-mono">
                {current.perceived_draft_range}
              </span>
            )}
          </div>

          {/* Description */}
          {current.description && (
            <p className="text-gray-300 text-sm leading-relaxed mb-6">
              {current.description}
            </p>
          )}

          {/* Pre-draft stats */}
          <div>
            <p className="text-[10px] text-gray-500 font-mono uppercase tracking-widest mb-4">
              {collegeStats?.league ? "Intl Stats" : "College Stats"}
            </p>
            <CollegeStats cs={collegeStats ?? {}} />
          </div>

          {/* Notes */}
          {"notes" in current && current.notes && (
            <div className="mt-6">
              <p className="text-[10px] text-gray-600 font-mono uppercase tracking-widest mb-2">
                Notes
              </p>
              <p className="text-gray-400 text-sm leading-relaxed">{current.notes}</p>
            </div>
          )}
        </div>
      </div>

      {/* RIGHT PANEL — constellation + comps, right half of screen */}
      <div className="fixed right-0 top-0 h-full w-1/2 bg-gray-950 border-l border-gray-800 z-50 flex flex-col shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800 shrink-0">
          <div className="flex items-center gap-2">
            {history.length > 0 && (
              <button
                onClick={handleBack}
                className="text-gray-400 hover:text-white transition-colors mr-1 text-lg leading-none"
                title="Back"
              >
                ←
              </button>
            )}
            {"is_legend" in current && current.is_legend && (
              <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-amber-900/50 text-amber-400">
                Legend
              </span>
            )}
            <span className="text-xs text-gray-500 font-mono">{yearLabel}</span>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-white transition-colors text-xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Constellation */}
        <div className="shrink-0 relative" style={{ height: "320px" }}>
          {loading && (
            <div className="absolute inset-0 bg-gray-950/80 flex items-center justify-center z-10">
              <span className="text-gray-400 text-sm">Loading...</span>
            </div>
          )}
          {comps.length > 0 ? (
            <Constellation
              playerName={current.name}
              draftYear={yearLabel ?? 0}
              comps={comps}
              inSystemSet={inSystemSet}
              onCompClick={handleCompClick}
            />
          ) : (
            <div
              className="flex items-center justify-center text-gray-700 text-sm font-mono"
              style={{ height: 220, background: "#04040f" }}
            >
              No comps added yet
            </div>
          )}
        </div>

        {/* Player info + comps */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4">
          <div>
            <h2 className="text-xl font-bold text-white">{current.name}</h2>
            <p className="text-gray-400 text-sm mt-0.5">{current.school}</p>
          </div>

          <div className="flex flex-wrap gap-2">
            {current.position && (
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-800 text-gray-300">
                {current.position}
              </span>
            )}
            {"bust_risk" in current && current.bust_risk && bustColor && (
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${bustColor}`}>
                {current.bust_risk}
              </span>
            )}
            {"perceived_draft_range" in current && current.perceived_draft_range && (
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-800 text-gray-400 font-mono">
                {current.perceived_draft_range}
              </span>
            )}
          </div>

          {current.description && (
            <p className="text-gray-300 text-sm leading-relaxed">
              {current.description}
            </p>
          )}

          {comps.length > 0 && (
            <div>
              <p className="text-gray-600 text-xs font-mono uppercase tracking-wider mb-2">
                Comparisons
              </p>
              <div className="flex flex-wrap gap-2">
                {comps.map((comp, i) => {
                  const linked = inSystemSet.has(comp.trim().toLowerCase());
                  return (
                    <button
                      key={i}
                      onClick={() => linked && handleCompClick(comp)}
                      disabled={!linked}
                      className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                        linked
                          ? "bg-blue-900/40 text-blue-300 hover:bg-blue-800/50 cursor-pointer"
                          : "bg-gray-800/50 text-gray-600 cursor-default"
                      }`}
                      title={linked ? `View ${comp}` : "Not in system"}
                    >
                      {comp.replace(/\b\w/g, (c) => c.toUpperCase())}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {"notes" in current && current.notes && (
            <div>
              <p className="text-gray-600 text-xs font-mono uppercase tracking-wider mb-2">
                Notes
              </p>
              <p className="text-gray-400 text-sm leading-relaxed">{current.notes}</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
