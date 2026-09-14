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

/** ₹11.5 Cr, ₹4.2 L — Indian units, since the amounts here are rupees. */
export const moneyShort = (amount) =>
  amount >= 1e7 ? `₹${(amount / 1e7).toFixed(1)} Cr`
    : amount >= 1e5 ? `₹${(amount / 1e5).toFixed(1)} L`
      : money(amount);
