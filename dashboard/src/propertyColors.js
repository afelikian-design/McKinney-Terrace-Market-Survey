export const PROPERTY_COLORS = {
  "McKinney Terrace": "#1d4ed8",
  "The Bridge at McKinney": "#dc2626",
  Kinstead: "#16a34a",
  "Collin Square": "#9333ea",
  "Gray Branch Apartments": "#ea580c",
  "Bexley Lake Forest": "#0891b2",
  "McKinney Village": "#ca8a04",
  "The Dalton": "#db2777",
};

export const FALLBACK_COLOR = "#64748b";

export function colorFor(name) {
  return PROPERTY_COLORS[name] ?? FALLBACK_COLOR;
}
