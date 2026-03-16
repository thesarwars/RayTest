/**
 * API Client – thin wrapper around fetch() for the FastAPI backend.
 *
 * - Reads the JWT from localStorage and attaches it as a Bearer token.
 * - Throws typed errors with the backend's `detail` message.
 * - Base URL resolves to the backend container in Docker or localhost in dev.
 */

import type { ApiError } from "@/lib/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiClientError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body: ApiError = await res.json();
      message = body.detail ?? message;
    } catch {
      /* response body wasn't JSON */
    }
    throw new ApiClientError(message, res.status);
  }

  return res.json() as Promise<T>;
}

/* ────────────────────────── Auth ────────────────────────── */

import type { TokenResponse } from "@/lib/types";

export async function register(email: string, password: string): Promise<TokenResponse> {
  return request<TokenResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  return request<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

/* ────────────────────────── Products ────────────────────── */

import type { Product } from "@/lib/types";

export async function fetchProducts(): Promise<Product[]> {
  return request<Product[]>("/api/v1/products");
}

export async function fetchProduct(id: string): Promise<Product> {
  return request<Product>(`/api/v1/products/${encodeURIComponent(id)}`);
}

/* ────────────────────────── Reservations ────────────────── */

import type { Reservation, CheckoutResponse } from "@/lib/types";

export async function createReservation(
  productId: string,
  quantity: number,
): Promise<Reservation> {
  return request<Reservation>("/api/v1/reservations", {
    method: "POST",
    body: JSON.stringify({ product_id: productId, quantity }),
  });
}

export async function fetchReservation(id: string): Promise<Reservation> {
  return request<Reservation>(`/api/v1/reservations/${encodeURIComponent(id)}`);
}

export async function fetchMyReservations(): Promise<Reservation[]> {
  return request<Reservation[]>("/api/v1/reservations");
}

export async function checkoutReservation(id: string): Promise<CheckoutResponse> {
  return request<CheckoutResponse>(
    `/api/v1/reservations/${encodeURIComponent(id)}/checkout`,
    { method: "POST" },
  );
}
