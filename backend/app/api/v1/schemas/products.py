from pydantic import BaseModel


class ProductResponse(BaseModel):
    id: str
    name: str
    description: str | None
    price: float
    total_inventory: int
    available_inventory: int
