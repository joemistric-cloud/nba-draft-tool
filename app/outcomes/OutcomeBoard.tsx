"use client";

import { useState, useCallback } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
  useDraggable,
  DragEndEvent,
  DragStartEvent,
} from "@dnd-kit/core";
import { Prospect } from "@/lib/types";
import PlayerPanel from "@/app/components/PlayerPanel";

// ── Types ──────────────────────────────────────────────────────────────────
type Outcome = "Hit" | "Solid" | "Mixed" | "Bust";

const OUTCOMES: Outcome[] = ["Hit", "Solid", "Mixed", "Bust"];

const OUTCOME_STYLES: Record<Outcome, { zone: string; badge: string; title: string }> = {
  Hit:   { zone: "border-emerald-700/40 bg-emerald-950/30", badge: "bg-emerald-800/60 text-emerald-300", title: "text-emerald-400" },
  Solid: { zone: "border-blue-700/40 bg-blue-950/30",       badge: "bg-blue-800/60 text-blue-300",       title: "text-blue-400"    },
  Mixed: { zone: "border-amber-700/40 bg-amber-950/30",     badge: "bg-amber-800/60 text-amber-300",     title: "text-amber-400"   },
  Bust:  { zone: "border-red-800/40 bg-red-950/30",         badge: "bg-red-900/60 text-red-300",         title: "text-red-400"     },
};

const POSITIONS = ["PG", "SG", "SF", "PF", "C", "Wing"] as const;

const SUGGESTED_TAGS = [
  "Shot creation", "Playmaking", "Athleticism", "Defense",
  "Outside shooting", "Size/length", "Injury history", "Off-court",
  "Consistency", "Finishing", "IQ/feel", "Role acceptance",
  "Development", "Draft position", "Team fit", "Age/upside",
];

// ── Player chip ─────────────────────────────────────────────────────────────
function PlayerChip({
  prospect,
  onSave,
  onSelect,
  overlay = false,
}: {
  prospect: Prospect;
  onSave: (id: string, outcome: Outcome | null, tags: string[]) => Promise<void>;
  onSelect: (p: Prospect) => void;
  overlay?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [outcome, setOutcome] = useState<Outcome | null>(prospect.outcome as Outcome | null);
  const [tags, setTags] = useState<string[]>(prospect.outcome_tags ?? []);
  const [customTag, setCustomTag] = useState("");
  const [saving, setSaving] = useState(false);

  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: prospect.id,
    data: { prospect },
  });

  const toggleTag = (tag: string) => {
    setTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag].slice(0, 2)
    );
  };

  const addCustom = () => {
    const t = customTag.trim();
    if (t && !tags.includes(t) && tags.length < 2) {
      setTags((prev) => [...prev, t]);
      setCustomTag("");
    }
  };

  const handleSave = async () => {
    setSaving(true);
    await onSave(prospect.id, outcome, tags);
    setSaving(false);
    setOpen(false);
  };

  const pick = prospect.drafted?.pick;
  const outstyle = outcome ? OUTCOME_STYLES[outcome] : null;

  return (
    <>
      <div
        ref={overlay ? undefined : setNodeRef}
        style={{ opacity: isDragging && !overlay ? 0 : 1 }}
        className={`relative text-left rounded-lg border px-3 py-2.5 w-44 shrink-0 transition-all ${
          overlay ? "rotate-1 scale-105 shadow-2xl cursor-grabbing" : "cursor-grab hover:scale-[1.02] hover:brightness-110"
        } ${
          outstyle
            ? `${outstyle.zone} border-opacity-60`
            : "border-gray-700/40 bg-gray-900/40"
        }`}
        {...(overlay ? {} : { ...attributes, ...listeners })}
        onClick={(e) => {
          if (!isDragging) onSelect(prospect);
        }}
      >
        <div className="flex items-start justify-between gap-1 mb-1.5">
          <span className="text-white text-sm font-semibold leading-tight">
            {prospect.name}
          </span>
          {/* Edit icon — opens outcome/tags modal */}
          <button
            onClick={(e) => { e.stopPropagation(); setOpen(true); }}
            className="text-gray-600 hover:text-gray-300 transition-colors shrink-0 mt-0.5 text-xs leading-none"
            title="Edit outcome"
          >
            ✎
          </button>
        </div>
        <div className="flex items-center gap-1.5 mb-2">
          <span className="text-gray-500 text-xs font-mono">{prospect.draft_class}</span>
          {pick && (
            <span className="text-gray-600 text-xs font-mono">· #{pick}</span>
          )}
        </div>
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {tags.map((tag) => (
              <span
                key={tag}
                className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                  outstyle ? outstyle.badge : "bg-gray-800 text-gray-400"
                }`}
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Edit modal */}
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />
          <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-80 p-5 z-10">
            <div className="mb-4">
              <h3 className="text-white font-bold text-base">{prospect.name}</h3>
              <p className="text-gray-500 text-xs font-mono">
                {prospect.draft_class} · Pick #{pick} · {prospect.school || "—"}
              </p>
            </div>

            <p className="text-gray-400 text-xs uppercase tracking-widest mb-2">Outcome</p>
            <div className="grid grid-cols-4 gap-1.5 mb-4">
              {OUTCOMES.map((o) => (
                <button
                  key={o}
                  onClick={() => setOutcome(outcome === o ? null : o)}
                  className={`py-1.5 rounded text-xs font-semibold transition-all ${
                    outcome === o
                      ? `${OUTCOME_STYLES[o].badge} ring-1 ring-white/20`
                      : "bg-gray-800 text-gray-500 hover:text-gray-300"
                  }`}
                >
                  {o}
                </button>
              ))}
            </div>

            <p className="text-gray-400 text-xs uppercase tracking-widest mb-2">
              Tags <span className="text-gray-600 normal-case">(pick 2)</span>
            </p>
            <div className="flex flex-wrap gap-1.5 mb-3">
              {SUGGESTED_TAGS.map((tag) => (
                <button
                  key={tag}
                  onClick={() => toggleTag(tag)}
                  disabled={tags.length >= 2 && !tags.includes(tag)}
                  className={`text-xs px-2 py-1 rounded transition-colors ${
                    tags.includes(tag)
                      ? "bg-blue-800/60 text-blue-200"
                      : tags.length >= 2
                      ? "bg-gray-800/40 text-gray-700 cursor-not-allowed"
                      : "bg-gray-800 text-gray-400 hover:text-gray-200"
                  }`}
                >
                  {tag}
                </button>
              ))}
            </div>

            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={customTag}
                onChange={(e) => setCustomTag(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addCustom()}
                placeholder="Custom tag…"
                disabled={tags.length >= 2}
                className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white placeholder-gray-600 focus:outline-none focus:border-gray-500"
              />
              <button
                onClick={addCustom}
                disabled={tags.length >= 2 || !customTag.trim()}
                className="text-xs px-2 py-1 bg-gray-700 text-gray-300 rounded hover:bg-gray-600 disabled:opacity-40"
              >
                Add
              </button>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => setOpen(false)}
                className="flex-1 py-1.5 rounded text-sm text-gray-500 hover:text-gray-300 bg-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex-1 py-1.5 rounded text-sm font-medium bg-blue-700 hover:bg-blue-600 text-white disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ── Outcome zone (droppable) ────────────────────────────────────────────────
function OutcomeZone({
  outcome,
  players,
  onSave,
  onSelect,
}: {
  outcome: Outcome | null;
  players: Prospect[];
  onSave: (id: string, outcome: Outcome | null, tags: string[]) => Promise<void>;
  onSelect: (p: Prospect) => void;
}) {
  const zoneId = outcome ?? "Unrated";
  const { setNodeRef, isOver } = useDroppable({ id: zoneId });

  const style = outcome ? OUTCOME_STYLES[outcome] : null;
  const title = outcome ?? "Unrated";
  const titleClass = style ? style.title : "text-gray-600";
  const zoneClass = style ? style.zone : "border-gray-800 bg-gray-900/20";

  return (
    <div
      ref={setNodeRef}
      className={`rounded-xl border p-4 transition-all ${zoneClass} ${
        isOver ? "brightness-125 scale-[1.005]" : ""
      }`}
    >
      <div className="flex items-center gap-2 mb-3">
        <h2 className={`text-sm font-bold uppercase tracking-widest ${titleClass}`}>
          {title}
        </h2>
        <span className="text-gray-600 text-xs">{players.length}</span>
      </div>
      {players.length === 0 ? (
        <p className="text-gray-700 text-xs italic py-2">
          {isOver ? "Drop here" : "No players assigned yet"}
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {players.map((p) => (
            <PlayerChip key={p.id} prospect={p} onSave={onSave} onSelect={onSelect} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main board ─────────────────────────────────────────────────────────────
export default function OutcomeBoard({
  initialProspects,
}: {
  initialProspects: Prospect[];
}) {
  const [prospects, setProspects] = useState(initialProspects);
  const [activePositions, setActivePositions] = useState<Set<string>>(new Set());
  const [yearFilter, setYearFilter] = useState<number | null>(null);

  const togglePosition = (pos: string) => {
    setActivePositions((prev) => {
      const next = new Set(prev);
      if (next.has(pos)) next.delete(pos);
      else next.add(pos);
      return next;
    });
  };
  const [activeProspect, setActiveProspect] = useState<Prospect | null>(null);
  const [selectedPlayer, setSelectedPlayer] = useState<Prospect | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  const allYears = Array.from(
    new Set(initialProspects.map((p) => p.draft_class))
  ).sort();

  const filtered = prospects.filter((p) => {
    if (activePositions.size > 0) {
      if (!p.position || !activePositions.has(p.position)) return false;
    }
    if (yearFilter && p.draft_class !== yearFilter) return false;
    return true;
  });

  const sortByYearPick = (a: Prospect, b: Prospect) =>
    a.draft_class !== b.draft_class
      ? a.draft_class - b.draft_class
      : (a.drafted?.pick ?? 99) - (b.drafted?.pick ?? 99);

  const byOutcome = (o: Outcome | null) =>
    filtered.filter((p) => p.outcome === o).sort(sortByYearPick);

  const handleSave = useCallback(
    async (id: string, outcome: Outcome | null, tags: string[]) => {
      const prospect = prospects.find((p) => p.id === id);
      if (!prospect) return;

      await fetch("/api/save-outcome", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id,
          draft_class: prospect.draft_class,
          outcome,
          outcome_tags: tags,
        }),
      });

      setProspects((prev) =>
        prev.map((p) =>
          p.id === id ? { ...p, outcome, outcome_tags: tags } : p
        )
      );
    },
    [prospects]
  );

  const handleDragStart = (event: DragStartEvent) => {
    const p = prospects.find((p) => p.id === event.active.id);
    setActiveProspect(p ?? null);
  };

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveProspect(null);
      const { active, over } = event;
      if (!over) return;

      const playerId = active.id as string;
      const zoneId = over.id as string;
      const newOutcome = zoneId === "Unrated" ? null : (zoneId as Outcome);

      const player = prospects.find((p) => p.id === playerId);
      if (!player || player.outcome === newOutcome) return;

      handleSave(playerId, newOutcome, player.outcome_tags ?? []);
    },
    [prospects, handleSave]
  );

  const rated = filtered.filter((p) => p.outcome !== null);
  const unrated = byOutcome(null);

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="px-6 py-6">
        {/* Position filter — multi-select: click any combination of positions */}
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          <span className="text-gray-500 text-xs uppercase tracking-widest mr-1">
            Position
          </span>
          <button
            onClick={() => setActivePositions(new Set())}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              activePositions.size === 0
                ? "bg-blue-700 text-white"
                : "bg-gray-800 text-gray-400 hover:text-gray-200"
            }`}
          >
            All
          </button>
          {POSITIONS.map((pos) => (
            <button
              key={pos}
              onClick={() => togglePosition(pos)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                activePositions.has(pos)
                  ? "bg-blue-700 text-white"
                  : "bg-gray-800 text-gray-400 hover:text-gray-200"
              }`}
            >
              {pos}
            </button>
          ))}
          <span className="text-gray-600 text-xs ml-2">
            {rated.length}/{filtered.length} rated
          </span>
        </div>

        {/* Year filter */}
        <div className="flex items-center gap-2 mb-6 flex-wrap">
          <span className="text-gray-500 text-xs uppercase tracking-widest mr-1">
            Class
          </span>
          <button
            onClick={() => setYearFilter(null)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              yearFilter === null
                ? "bg-blue-700 text-white"
                : "bg-gray-800 text-gray-400 hover:text-gray-200"
            }`}
          >
            All
          </button>
          {allYears.map((y) => (
            <button
              key={y}
              onClick={() => setYearFilter(yearFilter === y ? null : y)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                yearFilter === y
                  ? "bg-blue-700 text-white"
                  : "bg-gray-800 text-gray-400 hover:text-gray-200"
              }`}
            >
              {y}
            </button>
          ))}
        </div>

        {/* Outcome zones */}
        <div className="flex flex-col gap-4 mb-6">
          {OUTCOMES.map((o) => (
            <OutcomeZone
              key={o}
              outcome={o}
              players={byOutcome(o)}
              onSave={handleSave}
              onSelect={setSelectedPlayer}
            />
          ))}
        </div>

        {/* Unrated */}
        <OutcomeZone
          outcome={null}
          players={unrated}
          onSave={handleSave}
          onSelect={setSelectedPlayer}
        />
      </div>

      {/* Player stats panel */}
      {selectedPlayer && (
        <PlayerPanel
          player={selectedPlayer}
          onClose={() => setSelectedPlayer(null)}
        />
      )}

      {/* Drag overlay — ghost chip while dragging */}
      <DragOverlay>
        {activeProspect && (
          <PlayerChip
            prospect={activeProspect}
            onSave={handleSave}
            onSelect={setSelectedPlayer}
            overlay
          />
        )}
      </DragOverlay>
    </DndContext>
  );
}
