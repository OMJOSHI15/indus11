"""
Reading back a stored explanation.

The decision engine writes "Triggered signals: CODE (detail); CODE. <prose>",
and two callers need to take it apart again: the dashboard aggregate counts
codes, and the drain script feeds the signals back to the language model. The
details carry the evidence ("sent ₹600000 of ₹25005 received"), so the drain
needs the whole part and the aggregate needs only the code — one boundary
scan, two shapes.

Finding that boundary is the part worth writing once: a detail can contain a
full stop of its own (an IP address, an amount), so the list ends at the first
one outside brackets, not the first ". ".
"""
SIGNAL_PREFIX = "Triggered signals: "


def signal_parts(explanation: str | None) -> list[str]:
    """The flag list as written, each part still carrying its parenthetical."""
    if not explanation or not explanation.startswith(SIGNAL_PREFIX):
        return []
    body, depth = explanation[len(SIGNAL_PREFIX):], 0
    end = len(body)
    for i, ch in enumerate(body):
        depth += (ch == "(") - (ch == ")")
        if ch == "." and depth == 0 and body[i + 1:i + 2] in ("", " "):
            end = i
            break
    return [part.strip() for part in body[:end].split("; ") if part.strip()]


def flag_codes(explanation: str | None) -> list[str]:
    """Just the codes, without details. Layer errors are failures, not signals."""
    codes = (part.split(" (", 1)[0].strip() for part in signal_parts(explanation))
    return [c for c in codes if c and not c.endswith("_ERROR")]
