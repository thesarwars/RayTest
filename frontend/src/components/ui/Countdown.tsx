"use client";

import { useEffect, useState, useCallback } from "react";

interface CountdownProps {
  expiresAt: string;
  onExpire?: () => void;
}

function calcRemaining(expiresAt: string): number {
  return Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000));
}

function formatTime(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/**
 * Countdown Timer – calculates remaining time from the backend's `expires_at`.
 *
 * - Survives page refresh (derives remaining from wall-clock diff, not local state).
 * - Fires `onExpire` callback once when the timer hits zero.
 * - Colour shifts: green → yellow (< 60s) → red (< 15s).
 */
export function Countdown({ expiresAt, onExpire }: CountdownProps) {
  const [remaining, setRemaining] = useState(() => calcRemaining(expiresAt));

  const handleExpire = useCallback(() => {
    onExpire?.();
  }, [onExpire]);

  useEffect(() => {
    // Recalculate on mount (handles page refresh)
    setRemaining(calcRemaining(expiresAt));

    const interval = setInterval(() => {
      const r = calcRemaining(expiresAt);
      setRemaining(r);
      if (r <= 0) {
        clearInterval(interval);
        handleExpire();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [expiresAt, handleExpire]);

  const isExpired = remaining <= 0;
  const isUrgent = remaining <= 15;
  const isWarning = remaining <= 60;

  const colour = isExpired
    ? "text-gray-500"
    : isUrgent
      ? "text-red-600"
      : isWarning
        ? "text-yellow-600"
        : "text-emerald-600";

  return (
    <div className="flex items-center gap-2">
      <div
        className={`relative h-10 w-10 rounded-full border-2 flex items-center justify-center
          ${isExpired ? "border-gray-300" : isUrgent ? "border-red-400 animate-pulse" : "border-emerald-400"}`}
      >
        <svg className="absolute inset-0 -rotate-90" viewBox="0 0 36 36">
          <circle
            cx="18"
            cy="18"
            r="15.9"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeDasharray={`${(remaining / 300) * 100}, 100`}
            className={`${colour} transition-all duration-1000`}
          />
        </svg>
      </div>
      <span className={`font-mono text-lg font-semibold ${colour}`}>
        {isExpired ? "Expired" : formatTime(remaining)}
      </span>
    </div>
  );
}
