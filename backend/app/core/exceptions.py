"""Application-level custom exceptions."""

from uuid import UUID


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, entity: str, entity_id: UUID | str):
        super().__init__(f"{entity} {entity_id} not found", status_code=404)


class ConflictError(AppError):
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, status_code=409)


class InsufficientStockError(AppError):
    def __init__(self, product_id: UUID):
        super().__init__(f"Insufficient stock for product {product_id}", status_code=409)


class AuthenticationError(AppError):
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, status_code=401)
