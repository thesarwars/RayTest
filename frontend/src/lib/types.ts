/* ── Shared TypeScript types mirroring the FastAPI schemas ── */

export interface TokenResponse {
  user_id: string;
  access_token: string;
  token_type: string;
}

export interface Product {
  id: string;
  name: string;
  description: string | null;
  price: number;
  total_inventory: number;
  available_inventory: number;
}

export interface Reservation {
  reservation_id: string;
  product_id: string;
  product_name: string;
  quantity: number;
  status: "pending" | "reserved" | "completed" | "expired" | "cancelled";
  expires_at: string | null;
  created_at?: string;
}

export interface CheckoutResponse {
  reservation_id: string;
  status: string;
}

export interface ApiError {
  detail: string;
}
