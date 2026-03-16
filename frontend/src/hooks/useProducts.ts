"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchProducts,
  fetchProduct,
  createReservation,
} from "@/lib/api/client";
import type { Product } from "@/lib/types";

export function useProducts() {
  return useQuery({
    queryKey: ["products"],
    queryFn: fetchProducts,
    staleTime: 10_000,
  });
}

export function useProduct(id: string) {
  return useQuery({
    queryKey: ["products", id],
    queryFn: () => fetchProduct(id),
    enabled: !!id,
  });
}

/**
 * Optimistic reserve mutation.
 *
 * On click → immediately decrement `available_inventory` in the products
 * query cache. If the server returns an error (e.g. out of stock) → roll back.
 */
export function useReserveProduct() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({ productId, quantity }: { productId: string; quantity: number }) =>
      createReservation(productId, quantity),

    onMutate: async ({ productId, quantity }) => {
      // Cancel in-flight refetches so they don't overwrite our optimistic update
      await qc.cancelQueries({ queryKey: ["products"] });

      const prev = qc.getQueryData<Product[]>(["products"]);

      // Optimistically decrement available_inventory
      if (prev) {
        qc.setQueryData<Product[]>(
          ["products"],
          prev.map((p) =>
            p.id === productId
              ? { ...p, available_inventory: Math.max(0, p.available_inventory - quantity) }
              : p,
          ),
        );
      }

      return { prev };
    },

    onError: (_err, _vars, ctx) => {
      // Roll back the optimistic update
      if (ctx?.prev) {
        qc.setQueryData(["products"], ctx.prev);
      }
    },

    onSettled: () => {
      // Re-fetch products to get the server truth
      qc.invalidateQueries({ queryKey: ["products"] });
      qc.invalidateQueries({ queryKey: ["reservations"] });
    },
  });
}
