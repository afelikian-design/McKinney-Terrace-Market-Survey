export function formatRent(rent) {
  if (rent == null || Number.isNaN(rent)) return "—";
  return `$${Math.round(rent).toLocaleString()}`;
}

export function formatSqft(sqft) {
  if (sqft == null || Number.isNaN(sqft)) return "—";
  return Math.round(sqft).toLocaleString();
}

export function formatPsf(rent, sqft) {
  if (!rent || !sqft) return "—";
  return `$${(rent / sqft).toFixed(2)}`;
}

export function formatTimestamp(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const date = d.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
  const time = d.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
  return `${date} at ${time}`;
}

export function classifyBeds(beds) {
  if (beds === 0) return "studios";
  if (beds === 1) return "one";
  if (beds === 2) return "two";
  if (beds === 3) return "three";
  return null;
}

export function truncate(text, max = 40) {
  if (!text) return "";
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1)}…`;
}
