"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchMyReservations,
  fetchReservation,
  checkoutReservation,
} from "@/lib/api/client";
import type { Reservation } from "@/lib/types";

export function useMyReservations() {
  return useQuery({
    queryKey: ["reservations"],
    queryFn: fetchMyReservations,
    staleTime: 5_000,
  });
}

/**
 * Poll a single reservation until it transitions out of 'pending'.
 *
 * The backend queue may not process the reservation immediately;
 * we poll every 2 seconds until `status !== 'pending'`.
 */
export function usePollReservation(id: string | null) {
  return useQuery({
    queryKey: ["reservations", id],
    queryFn: () => fetchReservation(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data as Reservation | undefined;
      // Keep polling while status is pending
      return data?.status === "pending" ? 2000 : false;
    },
  });
}

/**
 * Checkout mutation: reserved → completed.
 */
export function useCheckout() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (reservationId: string) => checkoutReservation(reservationId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reservations"] });
      qc.invalidateQueries({ queryKey: ["products"] });
    },
  });
}
