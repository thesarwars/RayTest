"use client";

import { useState } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/useAuth";
import { useReserveProduct } from "@/hooks/useProducts";
import type { Product } from "@/lib/types";

export function ProductCard({ product }: { product: Product }) {
  const { isAuthenticated } = useAuth();
  const reserve = useReserveProduct();
  const router = useRouter();
  const [qty, setQty] = useState(1);

  const outOfStock = product.available_inventory <= 0;

  const handleReserve = async () => {
    if (!isAuthenticated) {
      router.push("/login");
      return;
    }
    try {
      const res = await reserve.mutateAsync({
        productId: product.id,
        quantity: qty,
      });
      toast.success(`Reserved! ID: ${res.reservation_id.slice(0, 8)}…`);
      router.push("/reservations");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Reservation failed";
      toast.error(message);
    }
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm hover:shadow-md transition-shadow">
      <h3 className="text-lg font-semibold text-gray-900">{product.name}</h3>
      {product.description && (
        <p className="mt-1 text-sm text-gray-500">{product.description}</p>
      )}
      <div className="mt-4 flex items-center justify-between">
        <span className="text-2xl font-bold text-gray-900">
          ${product.price.toFixed(2)}
        </span>
        <span
          className={`text-sm font-medium ${outOfStock ? "text-red-600" : "text-emerald-600"}`}
        >
          {outOfStock ? "Sold out" : `${product.available_inventory} left`}
        </span>
      </div>

      <div className="mt-4 flex items-center gap-3">
        <select
          value={qty}
          onChange={(e) => setQty(Number(e.target.value))}
          disabled={outOfStock}
          className="rounded-lg border border-gray-300 px-2 py-2 text-sm"
        >
          {Array.from({ length: Math.min(10, product.available_inventory) }, (_, i) => (
            <option key={i + 1} value={i + 1}>
              {i + 1}
            </option>
          ))}
        </select>
        <Button
          onClick={handleReserve}
          loading={reserve.isPending}
          disabled={outOfStock}
          className="flex-1"
        >
          {outOfStock ? "Sold Out" : "Reserve Now"}
        </Button>
      </div>
    </div>
  );
}
