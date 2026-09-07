"use client";

import { useMemo } from "react";

const NODE_COLORS = [
  "#60a5fa", // blue
  "#a78bfa", // violet
  "#34d399", // emerald
  "#f472b6", // pink
  "#fb923c", // orange
  "#facc15", // yellow
];

function seededHash(str: string): number {
  let h = 5381;
  for (let i = 0; i < str.length; i++) {
    h = (((h << 5) + h) + str.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

function makeRand(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = ((s * 1664525) + 1013904223) >>> 0;
    return s / 0x100000000;
  };
}

// Star field — same for every player (fixed seed)
const _starRand = makeRand(9137);
const STARS = Array.from({ length: 55 }, () => ({
  x: _starRand() * 420,
  y: _starRand() * 380,
  r: 0.3 + _starRand() * 1.2,
  o: 0.06 + _starRand() * 0.3,
}));

const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5)); // ≈ 2.399 rad

function formatComp(name: string): string {
  return name.trim().replace(/\b\w/g, (c) => c.toUpperCase());
}

function getTextOffset(angle: number): { dy: number; anchor: "start" | "middle" | "end" } {
  // Normalize angle to [0, 2π]
  const a = ((angle % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
  const deg = a * (180 / Math.PI);

  if (deg >= 315 || deg < 45) return { dy: 4, anchor: "start" };   // right
  if (deg >= 45 && deg < 135)  return { dy: 22, anchor: "middle" }; // bottom
  if (deg >= 135 && deg < 225) return { dy: 4, anchor: "end" };     // left
  return { dy: -14, anchor: "middle" };                              // top
}

interface CompNode {
  raw: string;
  label: string;
  x: number;
  y: number;
  color: string;
  angle: number;
  pulseDur: string;
  pulseDelay: string;
  inSystem: boolean;
}

interface ConstellationProps {
  playerName: string;
  draftYear: number;
  comps: string[];
  inSystemSet: Set<string>; // lowercase names/aliases already resolved
  onCompClick?: (compName: string) => void;
}

export default function Constellation({
  playerName,
  draftYear,
  comps,
  inSystemSet,
  onCompClick,
}: ConstellationProps) {
  const W = 420, H = 370, CX = 210, CY = 180;

  const nodes: CompNode[] = useMemo(() => {
    return comps.map((comp, i) => {
      const rand = makeRand(seededHash(comp + playerName + i));
      const angle = i * GOLDEN_ANGLE + (rand() - 0.5) * 0.35;
      const radius = 118 + rand() * 58;

      const x = CX + radius * Math.cos(angle);
      const y = CY + radius * Math.sin(angle);

      // Clamp to stay within viewbox with padding
      const pad = 36;
      const cx = Math.max(pad, Math.min(W - pad, x));
      const cy = Math.max(pad, Math.min(H - pad, y));

      const label = formatComp(comp);
      const inSystem = inSystemSet.has(comp.trim().toLowerCase());

      return {
        raw: comp,
        label,
        x: cx,
        y: cy,
        color: NODE_COLORS[i % NODE_COLORS.length],
        angle,
        pulseDur: (2.8 + rand() * 1.8).toFixed(2),
        pulseDelay: (rand() * 2.5).toFixed(2),
        inSystem,
      };
    });
  }, [playerName, comps, inSystemSet]);

  return (
    <svg
      width="100%"
      height="100%"
      viewBox={`40 25 340 305`}
      style={{ display: "block", background: "#04040f" }}
      aria-label={`Constellation for ${playerName}`}
    >
      <defs>
        <filter id="glow-center" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="7" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="glow-node" x="-80%" y="-80%" width="260%" height="260%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="glow-line" x="-5%" y="-100%" width="110%" height="300%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="1.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <radialGradient id="center-fill" cx="38%" cy="32%" r="65%">
          <stop offset="0%" stopColor="#e0f2fe" />
          <stop offset="100%" stopColor="#7dd3fc" />
        </radialGradient>
      </defs>

      {/* Star field */}
      {STARS.map((s, i) => (
        <circle key={i} cx={s.x} cy={s.y} r={s.r} fill="white" opacity={s.o} />
      ))}

      {/* Connection lines */}
      {nodes.map((node, i) => (
        <line
          key={`line-${i}`}
          x1={CX} y1={CY}
          x2={node.x} y2={node.y}
          stroke={node.color}
          strokeWidth={node.inSystem ? "0.85" : "0.5"}
          strokeOpacity={node.inSystem ? "0.5" : "0.25"}
          strokeDasharray="5 4"
          filter="url(#glow-line)"
        >
          <animate
            attributeName="stroke-dashoffset"
            from="0"
            to="-36"
            dur={`${2.2 + i * 0.35}s`}
            repeatCount="indefinite"
          />
        </line>
      ))}

      {/* Comp nodes */}
      {nodes.map((node, i) => {
        const { dy, anchor } = getTextOffset(node.angle);
        return (
          <g
            key={`comp-${i}`}
            onClick={() => node.inSystem && onCompClick?.(node.raw)}
            style={{ cursor: node.inSystem ? "pointer" : "default" }}
          >
            {/* Glow halo */}
            <circle
              cx={node.x} cy={node.y} r="18"
              fill={node.color}
              opacity={node.inSystem ? "0.13" : "0.06"}
              filter="url(#glow-node)"
            >
              <animate
                attributeName="r"
                values="16;21;16"
                dur={`${node.pulseDur}s`}
                begin={`${node.pulseDelay}s`}
                repeatCount="indefinite"
              />
            </circle>

            {/* Main node */}
            <circle
              cx={node.x} cy={node.y}
              r={node.inSystem ? "10" : "7"}
              fill={node.color}
              opacity={node.inSystem ? "0.88" : "0.4"}
            >
              <animate
                attributeName="r"
                values={node.inSystem ? "10;11.5;10" : "7;8;7"}
                dur={`${node.pulseDur}s`}
                begin={`${node.pulseDelay}s`}
                repeatCount="indefinite"
              />
            </circle>

            {/* Center dot */}
            <circle
              cx={node.x} cy={node.y} r="2.5"
              fill="white"
              opacity={node.inSystem ? "0.95" : "0.4"}
            />

            {/* Label */}
            <text
              x={node.x}
              y={node.y + dy}
              textAnchor={anchor}
              fill="white"
              fontSize="8.5"
              fontFamily="ui-monospace, monospace"
              letterSpacing="0.4"
              opacity={node.inSystem ? "0.9" : "0.45"}
            >
              {node.label}
            </text>

            {/* "In system" indicator dot */}
            {node.inSystem && (
              <circle
                cx={node.x + 8}
                cy={node.y - 8}
                r="2.5"
                fill={node.color}
                opacity="0.9"
              />
            )}
          </g>
        );
      })}

      {/* Central node — rendered last, on top */}
      <g filter="url(#glow-center)">
        {/* Outer pulse */}
        <circle cx={CX} cy={CY} r="36" fill="#7dd3fc" opacity="0.05">
          <animate attributeName="r" values="33;42;33" dur="4.5s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.05;0.1;0.05" dur="4.5s" repeatCount="indefinite" />
        </circle>
        {/* Ring */}
        <circle cx={CX} cy={CY} r="27" fill="none" stroke="#7dd3fc" strokeWidth="0.6" opacity="0.28">
          <animate attributeName="r" values="25;29;25" dur="4.5s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.28;0.5;0.28" dur="4.5s" repeatCount="indefinite" />
        </circle>
        {/* Main circle */}
        <circle cx={CX} cy={CY} r="20" fill="url(#center-fill)" opacity="0.95" />
        {/* Inner dot */}
        <circle cx={CX} cy={CY} r="5" fill="white" opacity="1" />
      </g>

      {/* Central player name */}
      <text
        x={CX} y={CY + 38}
        textAnchor="middle"
        fill="white"
        fontSize="11"
        fontWeight="600"
        fontFamily="ui-sans-serif, sans-serif"
        opacity="0.95"
        letterSpacing="0.3"
      >
        {playerName}
      </text>
      <text
        x={CX} y={CY + 51}
        textAnchor="middle"
        fill="#60a5fa"
        fontSize="8"
        fontFamily="ui-monospace, monospace"
        opacity="0.55"
        letterSpacing="1.5"
      >
        {draftYear}
      </text>

      {/* Legend */}
      {nodes.some((n) => n.inSystem) && (
        <g>
          <circle cx="14" cy={H - 12} r="3" fill="#60a5fa" opacity="0.85" />
          <text x="21" y={H - 9} fill="#9ca3af" fontSize="7.5" fontFamily="ui-monospace, monospace" opacity="0.7">
            in system
          </text>
        </g>
      )}
    </svg>
  );
}
