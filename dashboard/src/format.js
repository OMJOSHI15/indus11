export const money = (amount) =>
  "₹" + Number(amount).toLocaleString("en-IN", { maximumFractionDigits: 0 });

// MongoDB hands back naive UTC ("2026-09-14T05:38:13.123"). Without a zone the
// browser reads that as local time, which put every IST timestamp 5h30m early.
export const toDate = (iso) =>
  new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);

const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto", style: "short" });
const STEPS = [["day", 86400], ["hour", 3600], ["minute", 60]];

export function ago(iso) {
  const seconds = (toDate(iso) - Date.now()) / 1000;
  for (const [unit, size] of STEPS) {
    if (Math.abs(seconds) >= size) return rtf.format(Math.round(seconds / size), unit);
  }
  return "just now";
}

export const fullTime = (iso) =>
  toDate(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
