"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Prospect, AnyPlayer } from "@/lib/types";
import { BUST_RISK_COLORS } from "@/lib/constants";
import PlayerPanel from "./components/PlayerPanel";

const POSITIONS = ["PG", "SG", "SF", "PF", "C"] as const;

function PositionPicker({
  prospect,
  onSave,
}: {
  prospect: Prospect;
  onSave: (id: string, position: string | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const select = async (pos: string | null) => {
    setSaving(true);
    try {
      await fetch("/api/save-position", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ year: CURRENT_CLASS, id: prospect.id, position: pos }),
      });
      onSave(prospect.id, pos);
    } finally {
      setSaving(false);
      setOpen(false);
    }
  };

  return (
    <div ref={ref} className="relative inline-block">
      <button
        onClick={() => setOpen((v) => !v)}
        className={`text-xs font-mono px-2 py-0.5 rounded transition-colors ${
          prospect.position
            ? "text-sky-300 bg-sky-900/40 hover:bg-sky-800/50"
            : "text-amber-600/60 hover:text-amber-400"
        }`}
      >
        {saving ? "…" : prospect.position ?? "—"}
      </button>
      {open && (
        <div className="absolute z-50 left-0 top-full mt-1 flex gap-1 bg-gray-900 border border-gray-700 rounded p-1.5 shadow-xl">
          {POSITIONS.map((p) => (
            <button
              key={p}
              onClick={() => select(p)}
              className={`text-xs px-2 py-1 rounded font-mono transition-colors ${
                prospect.position === p
                  ? "bg-sky-700 text-white"
                  : "bg-gray-800 text-gray-300 hover:bg-gray-700"
              }`}
            >
              {p}
            </button>
          ))}
          {prospect.position && (
            <button
              onClick={() => select(null)}
              className="text-xs px-2 py-1 rounded text-gray-500 hover:text-red-400 hover:bg-gray-800 transition-colors"
            >
              ✕
            </button>
          )}
        </div>
      )}
    </div>
  );
}

const CURRENT_CLASS = 2026;

function SortableRow({
  prospect,
  index,
  onClick,
  onPositionSave,
}: {
  prospect: Prospect;
  index: number;
  onClick: () => void;
  onPositionSave: (id: string, position: string | null) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: prospect.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  const bustColor = prospect.bust_risk
    ? BUST_RISK_COLORS[prospect.bust_risk] ?? "bg-gray-800 text-gray-400"
    : "";

  return (
    <tr
      ref={setNodeRef}
      style={style}
      className={`border-b border-gray-800/50 group ${
        index % 2 === 0 ? "bg-transparent" : "bg-gray-900/30"
      } ${isDragging ? "bg-gray-700/60" : ""}`}
    >
      {/* Drag handle */}
      <td className="py-3 pr-2 w-6">
        <span
          {...attributes}
          {...listeners}
          className="cursor-grab active:cursor-grabbing text-gray-700 hover:text-gray-400 select-none text-lg leading-none block text-center"
        >
          ⠿
        </span>
      </td>

      <td className="py-3 pr-4 text-gray-500 font-mono text-sm w-10">
        {index + 1}
      </td>

      {/* Clickable name */}
      <td className="py-3 pr-6 text-sm">
        <button
          onClick={onClick}
          className="font-semibold text-white hover:text-blue-300 transition-colors text-left"
        >
          {prospect.name}
        </button>
      </td>

      <td className="py-3 pr-6 text-gray-300 text-sm">{prospect.school || "—"}</td>

      <td className="py-3 pr-4 text-sm">
        <PositionPicker prospect={prospect} onSave={onPositionSave} />
      </td>

      <td className="py-3 pr-6 text-sm">
        {prospect.bust_risk ? (
          <span className={`rounded px-2 py-0.5 text-xs font-medium ${bustColor}`}>
            {prospect.bust_risk}
          </span>
        ) : (
          <span className="text-gray-700">—</span>
        )}
      </td>

      <td className="py-3 pr-6 text-gray-400 text-sm font-mono">
        {prospect.perceived_draft_range || "—"}
      </td>

      <td className="py-3 text-gray-400 text-sm max-w-xs">
        <span className="line-clamp-1">{prospect.description || "—"}</span>
      </td>
    </tr>
  );
}

export default function BigBoard({ initialProspects }: { initialProspects: Prospect[] }) {
  const [prospects, setProspects] = useState(initialProspects);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [selectedPlayer, setSelectedPlayer] = useState<AnyPlayer | null>(null);
  const [search, setSearch] = useState("");
  const [showUnassigned, setShowUnassigned] = useState(false);

  const sensors = useSensors(useSensor(PointerSensor));

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    setProspects((prev) => {
      const oldIndex = prev.findIndex((p) => p.id === active.id);
      const newIndex = prev.findIndex((p) => p.id === over.id);
      return arrayMove(prev, oldIndex, newIndex);
    });
    setHasChanges(true);
    setSaved(false);
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch("/api/save-board", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ year: CURRENT_CLASS, prospects }),
      });
      if (!res.ok) throw new Error("Save failed");
      setSaved(true);
      setHasChanges(false);
    } catch (err) {
      console.error(err);
      alert("Failed to save.");
    } finally {
      setSaving(false);
    }
  };

  const handlePositionSave = useCallback((id: string, position: string | null) => {
    setProspects((prev) =>
      prev.map((p) => (p.id === id ? { ...p, position } : p))
    );
  }, []);

  const assignedCount = prospects.filter((p) => p.position).length;
  const unassignedCount = prospects.length - assignedCount;

  const query = search.trim().toLowerCase();
  const visible = prospects.filter((p) => {
    if (showUnassigned && p.position) return false;
    if (query) return (
      p.name.toLowerCase().includes(query) ||
      (p.school ?? "").toLowerCase().includes(query)
    );
    return true;
  });

  return (
    <>
      {/* Toolbar */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <p className="text-gray-500 text-sm">{prospects.length} prospects</p>
          <span className="text-xs font-mono text-gray-500">
            <span className="text-sky-400">{assignedCount}</span>
            <span className="text-gray-600"> / {prospects.length} positions filled</span>
            {unassignedCount > 0 && (
              <span className="text-amber-500/70"> · {unassignedCount} remaining</span>
            )}
          </span>
          <button
            onClick={() => { setShowUnassigned((v) => !v); setSearch(""); }}
            className={`text-xs px-2.5 py-1 rounded transition-colors font-medium ${
              showUnassigned
                ? "bg-amber-600/30 text-amber-300 border border-amber-600/40"
                : "bg-gray-800 text-gray-500 hover:text-gray-300"
            }`}
          >
            Unassigned only
          </button>
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setShowUnassigned(false); }}
            placeholder="Filter by name or school…"
            className="bg-gray-900 border border-gray-700 rounded px-3 py-1 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-gray-500 w-56"
          />
          {(search || showUnassigned) && (
            <span className="text-gray-500 text-xs">{visible.length} shown</span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {saved && <span className="text-emerald-400 text-sm">Saved</span>}
          <button
            onClick={handleSave}
            disabled={saving || !hasChanges}
            className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
              hasChanges
                ? "bg-emerald-600 hover:bg-emerald-500 text-white"
                : "bg-gray-800 text-gray-600 cursor-not-allowed"
            }`}
          >
            {saving ? "Saving..." : "Save Order"}
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400 text-left">
              <th className="pb-3 pr-2 w-6" />
              <th className="pb-3 pr-4 font-medium w-10">#</th>
              <th className="pb-3 pr-6 font-medium">Player</th>
              <th className="pb-3 pr-6 font-medium">School / Club</th>
              <th className="pb-3 pr-4 font-medium">Pos</th>
              <th className="pb-3 pr-6 font-medium">Risk</th>
              <th className="pb-3 pr-6 font-medium">Draft Range</th>
              <th className="pb-3 font-medium">Description</th>
            </tr>
          </thead>
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={prospects.map((p) => p.id)}
              strategy={verticalListSortingStrategy}
            >
              <tbody>
                {visible.map((p, i) => (
                  <SortableRow
                    key={p.id}
                    prospect={p}
                    index={prospects.indexOf(p)}
                    onClick={() => setSelectedPlayer(p)}
                    onPositionSave={handlePositionSave}
                  />
                ))}
              </tbody>
            </SortableContext>
          </DndContext>
        </table>
      </div>

      {/* Player panel */}
      {selectedPlayer && (
        <PlayerPanel
          player={selectedPlayer}
          onClose={() => setSelectedPlayer(null)}
        />
      )}
    </>
  );
}
