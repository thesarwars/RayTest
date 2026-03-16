"use client";

import { useAuth } from "@/hooks/useAuth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { ReservationList } from "@/components/ReservationList";

export default function ReservationsPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading || !isAuthenticated) {
    return null;
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">My Reservations</h1>
        <p className="mt-2 text-gray-500">
          Complete checkout within 5 minutes or your reservation will expire.
        </p>
      </div>
      <ReservationList />
    </div>
  );
}
