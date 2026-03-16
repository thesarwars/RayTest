"use client";

import { useMyReservations } from "@/hooks/useReservations";
import { ReservationCard } from "@/components/ReservationCard";
import { ReservationCardSkeleton } from "@/components/ui/Skeleton";

export function ReservationList() {
  const { data: reservations, isLoading, error } = useMyReservations();

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 3 }, (_, i) => (
          <ReservationCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
        Failed to load reservations.
      </div>
    );
  }

  if (!reservations?.length) {
    return (
      <div className="text-center py-12 text-gray-500">
        You have no reservations yet. Browse products to get started.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {reservations.map((r) => (
        <ReservationCard key={r.reservation_id} reservation={r} />
      ))}
    </div>
  );
}
