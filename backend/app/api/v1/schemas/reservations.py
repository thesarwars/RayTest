from pydantic import BaseModel, Field


class ReserveRequest(BaseModel):
    product_id: str
    quantity: int = Field(gt=0, le=10, description="Max 10 per reservation to prevent hoarding")


class ReservationResponse(BaseModel):
    reservation_id: str
    product_id: str
    product_name: str
    quantity: int
    status: str
    expires_at: str | None = None


class CheckoutResponse(BaseModel):
    reservation_id: str
    status: str
