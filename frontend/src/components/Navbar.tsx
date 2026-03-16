"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/Button";

export function Navbar() {
  const { isAuthenticated, logout, isLoading } = useAuth();

  return (
    <nav className="border-b border-gray-200 bg-white">
      <div className="mx-auto max-w-6xl flex items-center justify-between px-4 py-3">
        <Link href="/" className="text-lg font-bold text-indigo-600">
          ⚡ FlashSale
        </Link>
        <div className="flex items-center gap-4">
          <Link href="/" className="text-sm text-gray-600 hover:text-gray-900">
            Products
          </Link>
          {!isLoading && isAuthenticated && (
            <>
              <Link
                href="/reservations"
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                My Reservations
              </Link>
              <Button variant="ghost" size="sm" onClick={logout}>
                Logout
              </Button>
            </>
          )}
          {!isLoading && !isAuthenticated && (
            <Link href="/login">
              <Button variant="primary" size="sm">
                Sign In
              </Button>
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
