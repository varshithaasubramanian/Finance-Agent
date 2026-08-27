export function formatMoney(value: number, symbol = "\u20b9"): string {
  const rounded = Math.round((value + Number.EPSILON) * 100) / 100;
  const [intPart, decPart] = Math.abs(rounded).toFixed(2).split(".");
  // Indian-style comma grouping (e.g. 1,00,000.00)
  let lastThree = intPart.slice(-3);
  const otherNumbers = intPart.slice(0, -3);
  if (otherNumbers !== "") {
    lastThree = "," + lastThree;
  }
  const grouped = otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ",") + lastThree;
  const sign = rounded < 0 ? "-" : "";
  return `${sign}${symbol}${grouped}.${decPart}`;
}

export function formatDate(iso: string): string {
  const d = new Date(iso + (iso.length === 10 ? "T00:00:00" : ""));
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export function formatShortDate(iso: string): string {
  const d = new Date(iso + (iso.length === 10 ? "T00:00:00" : ""));
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

export function periodLabel(period: string): string {
  const [year, month] = period.split("-").map(Number);
  const d = new Date(year, month - 1, 1);
  return d.toLocaleDateString("en-IN", { month: "long", year: "numeric" });
}

export function clampPercent(value: number): number {
  return Math.max(0, Math.min(100, value));
}

export function statusColor(percentUsed: number): "healthy" | "caution" | "critical" {
  if (percentUsed >= 100) return "critical";
  if (percentUsed >= 75) return "caution";
  return "healthy";
}
