import { useEffect, useRef, useState } from "react";

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/**
 * Count a number up to `target` over `duration` ms.
 *
 * Uses requestAnimationFrame rather than an interval so the steps line up with
 * the browser's paint and the value never lands short of the target. Honours
 * prefers-reduced-motion by jumping straight to the final value — an animated
 * counter is decoration, and decoration is what that setting turns off.
 */
export default function useCountUp(target, duration = 900) {
  const [value, setValue] = useState(target);
  const fromRef = useRef(target);
  const frameRef = useRef(0);

  useEffect(() => {
    if (prefersReducedMotion()) {
      setValue(target);
      fromRef.current = target;
      return undefined;
    }

    const from = fromRef.current;
    const delta = target - from;
    if (delta === 0) return undefined;

    const start = performance.now();
    // easeOutCubic: quick at first, settling gently on the final number.
    const ease = (t) => 1 - Math.pow(1 - t, 3);

    const step = (now) => {
      const t = Math.min((now - start) / duration, 1);
      setValue(Math.round(from + delta * ease(t)));
      if (t < 1) {
        frameRef.current = requestAnimationFrame(step);
      } else {
        fromRef.current = target;
      }
    };

    frameRef.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frameRef.current);
  }, [target, duration]);

  return value;
}
