"""
Build the data-derived figures and screenshot crops used by docs/build_report.py.

    python docs/report_assets.py              charts from docs/eval-layer-scores.json
    python docs/report_assets.py --from-api   first rebuild that file from the running API

Charts are drawn with Pillow (already a dependency of the document builders) in
greyscale so they survive a black-and-white print.
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "report-assets")
SCORES = os.path.join(HERE, "eval-layer-scores.json")
FONT_DIR = "/System/Library/Fonts/Supplemental"

RULE_POINTS = {"BLACKLISTED_ACCOUNT": 40, "VELOCITY_EXCEEDED": 15, "AMOUNT_ANOMALY": 12,
               "HIGH_RISK_MERCHANT": 8, "HIGH_RISK_SENDER_TIER": 5, "ELEVATED_RISK_SENDER_TIER": 2}
GRAPH_POINTS = {"SHARED_DEVICE": 15, "CIRCULAR_FLOW": 12, "MONEY_MULE_PATTERN": 8,
                "SHARED_IP": 8, "FRAUD_CLUSTER_PROXIMITY": 10}


def rebuild_from_api():
    """Recompute rule and graph points from each stored record's flag codes."""
    import httpx
    scored = json.load(open(os.path.join(HERE, "eval-results.json")))["scored"]
    rows = []
    with httpx.Client(base_url="http://localhost:8000/api/v1", timeout=30) as c:
        for x in scored:
            exp = c.get(f"/transactions/{x['tx_id']}").json()["explanation"] or ""
            sig = exp.split("Triggered signals: ", 1)[1].split(". ", 1)[0] if exp.startswith("Triggered signals: ") else ""
            codes = [s.strip().split(" (")[0] for s in sig.split(";") if s.strip()]
            rule = 40 if "BLACKLISTED_ACCOUNT" in codes else min(sum(RULE_POINTS.get(k, 0) for k in codes), 40)
            graph = min(sum(GRAPH_POINTS.get(k, 0) for k in codes), 30)
            rag = x["composite_score"] - rule - graph
            assert 0 <= rag <= 30, (x["tx_id"], rag)
            rows.append({"tx_id": x["tx_id"], "label": x["label"], "pattern": x["pattern"],
                         "composite_score": x["composite_score"], "rule_score": rule,
                         "graph_score": graph, "rag_score": rag, "codes": codes})
    data = json.load(open(SCORES))
    data["rows"] = rows
    json.dump(data, open(SCORES, "w"), indent=1)


def font(size, bold=False):
    name = "Times New Roman Bold.ttf" if bold else "Times New Roman.ttf"
    try:
        return ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    except OSError:
        return ImageFont.load_default()


INK, GRID = (20, 20, 20), (215, 215, 215)
SHADES = [(45, 45, 45), (120, 120, 120), (190, 190, 190)]


def bar_chart(path, title, groups, series, values, y_max, y_step, y_label,
              thresholds=(), horizontal_labels=True):
    """Grouped vertical bars. values[g][s] is the bar for group g, series s."""
    W, H = 2000, 1150
    L, R, T, B = 170, 60, 150, 190
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    d.text((W // 2, 50), title, font=font(46, True), fill=INK, anchor="mm")
    pw, ph = W - L - R, H - T - B
    y = lambda v: T + ph - ph * v / y_max
    for v in range(0, int(y_max) + 1, y_step) if isinstance(y_step, int) else []:
        d.line([(L, y(v)), (W - R, y(v))], fill=GRID, width=2)
        d.text((L - 18, y(v)), f"{v}", font=font(32), fill=INK, anchor="rm")
    if not isinstance(y_step, int):
        v = 0.0
        while v <= y_max + 1e-9:
            d.line([(L, y(v)), (W - R, y(v))], fill=GRID, width=2)
            d.text((L - 18, y(v)), f"{v:.1f}", font=font(32), fill=INK, anchor="rm")
            v += y_step
    d.line([(L, T), (L, T + ph), (W - R, T + ph)], fill=INK, width=3)
    lab = Image.new("RGBA", (ph, 60), (255, 255, 255, 0))
    ImageDraw.Draw(lab).text((ph // 2, 30), y_label, font=font(34), fill=INK, anchor="mm")
    im.paste(lab.rotate(90, expand=True), (30, T), lab.rotate(90, expand=True))
    gw = pw / len(groups)
    bw = gw * 0.78 / len(series)
    for gi, g in enumerate(groups):
        x0 = L + gi * gw + gw * 0.11
        for si in range(len(series)):
            v = values[gi][si]
            xa, xb = x0 + si * bw, x0 + (si + 1) * bw - 6
            d.rectangle([xa, y(v), xb, T + ph], fill=SHADES[si], outline=INK, width=2)
            txt = f"{v:.2f}" if isinstance(v, float) else f"{v}"
            if v:
                d.text(((xa + xb) / 2, y(v) - 16), txt, font=font(26), fill=INK, anchor="mm")
        if isinstance(values[gi][0], float) and not any(values[gi]):
            d.text((L + gi * gw + gw / 2, T + ph - 24), "none flagged", font=font(28), fill=INK, anchor="mm")
        d.text((L + gi * gw + gw / 2, T + ph + 40), g, font=font(32), fill=INK, anchor="mm")
    for pos, text in thresholds:
        xx = L + pos * pw
        for yy in range(T, T + ph, 24):
            d.line([(xx, yy), (xx, yy + 12)], fill=INK, width=3)
        d.text((xx + 10, T + 10), text, font=font(30, True), fill=INK, anchor="la")
    lx = L
    for si, s in enumerate(series):
        d.rectangle([lx, H - 70, lx + 40, H - 40], fill=SHADES[si], outline=INK, width=2)
        d.text((lx + 55, H - 55), s, font=font(32), fill=INK, anchor="lm")
        lx += 90 + d.textlength(s, font=font(32))
    im.save(path)


def stacked_bars(path, title, groups, series, values, x_max, marks):
    """Horizontal stacked bars on a 0..x_max scale."""
    W, H = 2000, 900
    L, R, T, B = 330, 80, 150, 180
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    d.text((W // 2, 50), title, font=font(46, True), fill=INK, anchor="mm")
    pw, ph = W - L - R, H - T - B
    x = lambda v: L + pw * v / x_max
    for v in range(0, x_max + 1, 10):
        d.line([(x(v), T), (x(v), T + ph)], fill=GRID, width=2)
        d.text((x(v), T + ph + 30), f"{v}", font=font(30), fill=INK, anchor="mm")
    d.text((L + pw / 2, T + ph + 80), "Mean composite points", font=font(34), fill=INK, anchor="mm")
    rh = ph / len(groups)
    for gi, g in enumerate(groups):
        y0, y1 = T + gi * rh + rh * 0.2, T + (gi + 1) * rh - rh * 0.2
        acc = 0.0
        for si in range(len(series)):
            v = values[gi][si]
            d.rectangle([x(acc), y0, x(acc + v), y1], fill=SHADES[si], outline=INK, width=2)
            if v >= 4:
                d.text(((x(acc) + x(acc + v)) / 2, (y0 + y1) / 2), f"{v:.1f}", font=font(28),
                       fill="white" if si == 0 else INK, anchor="mm")
            acc += v
        d.text((x(acc) + 14, (y0 + y1) / 2), f"{acc:.1f}", font=font(30, True), fill=INK, anchor="lm")
        d.text((L - 20, (y0 + y1) / 2), g, font=font(32), fill=INK, anchor="rm")
    for pos, text in marks:
        for yy in range(T, T + ph, 24):
            d.line([(x(pos), yy), (x(pos), yy + 12)], fill=INK, width=3)
        d.text((x(pos) + 8, T - 12), text, font=font(28, True), fill=INK, anchor="lb")
    lx = L
    for si, s in enumerate(series):
        d.rectangle([lx, H - 60, lx + 40, H - 30], fill=SHADES[si], outline=INK, width=2)
        d.text((lx + 55, H - 45), s, font=font(32), fill=INK, anchor="lm")
        lx += 90 + d.textlength(s, font=font(32))
    im.save(path)


def main():
    if "--from-api" in sys.argv:
        rebuild_from_api()
    sys.path.insert(0, ROOT)
    from scripts.evaluate import metrics_at
    rows = json.load(open(SCORES))["rows"]
    os.makedirs(OUT, exist_ok=True)

    # 1. composite score distribution by true label, 10-point buckets
    buckets = [f"{b}-{b + 9}" if b < 90 else "90-100" for b in range(0, 100, 10)]
    count = lambda lab, b: sum(1 for r in rows if r["label"] == lab and min(r["composite_score"] // 10, 9) == b)
    bar_chart(os.path.join(OUT, "score-distribution.png"),
              "Composite score by true label (208 transactions)", buckets,
              ["Fraud (52)", "Legitimate (156)"],
              [[count("fraud", b), count("legit", b)] for b in range(10)],
              y_max=140, y_step=20, y_label="Transactions",
              thresholds=[(0.4, " REVIEW 40"), (0.7, " BLOCK 70")])

    # 2. ablation: which layer combinations catch the fraud at the configured bands
    combos = [("Rule", ("rule_score",)), ("Graph", ("graph_score",)), ("LLM", ("rag_score",)),
              ("Rule+Graph", ("rule_score", "graph_score")), ("Rule+LLM", ("rule_score", "rag_score")),
              ("Graph+LLM", ("graph_score", "rag_score")), ("All three", ("rule_score", "graph_score", "rag_score"))]
    ablation = []
    for name, keys in combos:
        m = metrics_at([dict(r, composite_score=min(sum(r[k] for k in keys), 100)) for r in rows], 40, 70)
        c = m["confusion"]
        ablation.append({"layers": name, **m["flagged"],
                         "tp": c["REVIEW"]["fraud"] + c["BLOCK"]["fraud"],
                         "fp": c["REVIEW"]["legit"] + c["BLOCK"]["legit"]})
    bar_chart(os.path.join(OUT, "ablation.png"), "Detection by layer combination (REVIEW at 40)",
              [a["layers"] for a in ablation], ["Precision", "Recall", "F1"],
              [[a["precision"], a["recall"], a["f1"]] for a in ablation],
              y_max=1.0, y_step=0.2, y_label="Score")

    # 3. mean layer points by planted pattern
    pats = [("Mule ring (36)", "mule_ring"), ("Shared IP (6)", "shared_ip"),
            ("Shared device (10)", "shared_device"), ("Legitimate (156)", "normal")]
    mean = lambda p, k: sum(r[k] for r in rows if r["pattern"] == p) / sum(1 for r in rows if r["pattern"] == p)
    stacked_bars(os.path.join(OUT, "layer-points-by-pattern.png"),
                 "Where the points come from, by planted pattern", [g for g, _ in pats],
                 ["Rule", "Graph", "LLM"],
                 [[mean(p, "rule_score"), mean(p, "graph_score"), mean(p, "rag_score")] for _, p in pats],
                 x_max=80, marks=[(40, "REVIEW"), (70, "BLOCK")])

    json.dump(ablation, open(os.path.join(OUT, "ablation.json"), "w"), indent=1)
    print("charts written to", OUT)
    for a in ablation:
        print(f"  {a['layers']:10} P {a['precision']:.3f}  R {a['recall']:.3f}  F1 {a['f1']:.3f}  TP {a['tp']}  FP {a['fp']}")


if __name__ == "__main__":
    main()
