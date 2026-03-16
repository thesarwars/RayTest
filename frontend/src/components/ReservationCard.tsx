"use client";

import { useState, useCallback } from "react";
import toast from "react-hot-toast";
import { Button } from "@/components/ui/Button";
import { Countdown } from "@/components/ui/Countdown";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import { useCheckout, usePollReservation } from "@/hooks/useReservations";
import type { Reservation } from "@/lib/types";

interface Props {
  reservation: Reservation;
}

export function ReservationCard({ reservation: initial }: Props) {
  const isPending = initial.status === "pending";

  // Poll while pending → transitions to reserved/failed
  const { data: polled } = usePollReservation(isPending ? initial.reservation_id : null);
  const reservation = polled ?? initial;

  const checkout = useCheckout();
  const [expired, setExpired] = useState(false);

  const handleExpire = useCallback(() => {
    setExpired(true);
    toast.error("Reservation expired");
  }, []);

  const handleCheckout = async () => {
    try {
      await checkout.mutateAsync(reservation.reservation_id);
      toast.success("Checkout complete!");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Checkout failed";
      toast.error(message);
    }
  };

  const isReserved = reservation.status === "reserved";
  const isCompleted = reservation.status === "completed";
  const isExpiredStatus = reservation.status === "expired" || expired;
  const canCheckout = isReserved && !expired;

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">
            {reservation.product_name}
          </h3>
          <span className="text-xs text-gray-400 font-mono">
            {reservation.reservation_id.slice(0, 8)}…
          </span>
          <p className="text-sm text-gray-600 mt-0.5">
            Qty: <span className="font-semibold">{reservation.quantity}</span>
          </p>
        </div>
        <StatusBadge status={expired ? "expired" : reservation.status} />
      </div>

      {/* Pending spinner */}
      {reservation.status === "pending" && (
        <div className="mt-4 flex items-center gap-2 text-yellow-700">
          <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10"
              stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm">Processing reservation…</span>
        </div>
      )}

      {/* Countdown (only for reserved, not yet expired) */}
      {isReserved && reservation.expires_at && !isExpiredStatus && (
        <div className="mt-4">
          <p className="text-xs text-gray-400 mb-1">Time remaining</p>
          <Countdown expiresAt={reservation.expires_at} onExpire={handleExpire} />
        </div>
      )}

      {/* Actions */}
      <div className="mt-4">
        {canCheckout && (
          <Button
            onClick={handleCheckout}
            loading={checkout.isPending}
            className="w-full"
          >
            Complete Checkout
          </Button>
        )}
        {isExpiredStatus && (
          <p className="text-sm text-gray-500 italic">This reservation has expired.</p>
        )}
        {isCompleted && (
          <p className="text-sm text-emerald-600 font-medium">✓ Purchase completed</p>
        )}
      </div>
    </div>
  );
}
