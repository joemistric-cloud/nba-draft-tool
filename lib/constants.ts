export const BUST_RISK_ORDER = [
  "None", "Very Low", "Low", "Low Mid", "Mid", "Upper Mid", "High", "Very High"
];

export const BUST_RISK_COLORS: Record<string, string> = {
  "None":      "bg-emerald-900/60 text-emerald-300",
  "Very Low":  "bg-emerald-900/40 text-emerald-400",
  "Low":       "bg-green-900/40 text-green-400",
  "Low Mid":   "bg-yellow-900/40 text-yellow-300",
  "Mid":       "bg-yellow-900/60 text-yellow-400",
  "Upper Mid": "bg-orange-900/50 text-orange-400",
  "High":      "bg-red-900/50 text-red-400",
  "Very High": "bg-red-900/70 text-red-300",
};
