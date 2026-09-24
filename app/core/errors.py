from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Base class for business-rule failures.

    Services raise these; `register_exception_handlers` turns them into
    consistent JSON responses so services never depend on HTTP details.
    """

    status_code: int = 400
    code: str = "domain_error"
    default_detail: str = "The request could not be processed."

    def __init__(
        self,
        detail: str | None = None,
        *,
        headers: dict[str, str] | None = None,
        extra: dict | None = None,
    ):
        self.detail = detail or self.default_detail
        self.headers = headers
        self.extra = extra or {}
        super().__init__(self.detail)


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"
    default_detail = "Resource not found."


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"
    default_detail = "The request conflicts with the current state of the resource."


class ValidationFailedError(DomainError):
    status_code = 422
    code = "validation_error"
    default_detail = "The request data is invalid."


class UnauthorizedError(DomainError):
    status_code = 401
    code = "unauthorized"
    default_detail = "Could not validate credentials."

    def __init__(
        self,
        detail: str | None = None,
        *,
        headers: dict[str, str] | None = None,
        extra: dict | None = None,
    ):
        super().__init__(
            detail,
            headers=headers if headers is not None else {"WWW-Authenticate": "Bearer"},
            extra=extra,
        )


class ForbiddenError(DomainError):
    status_code = 403
    code = "forbidden"
    default_detail = "You do not have permission to perform this action."


class InvalidTransitionError(ConflictError):
    code = "invalid_transition"

    def __init__(self, entity: str, current, target):
        current_value = getattr(current, "value", current)
        target_value = getattr(target, "value", target)
        super().__init__(
            f"Cannot change {entity} status from '{current_value}' to '{target_value}'.",
            extra={"current": current_value, "target": target_value},
        )


class InsufficientStockError(ConflictError):
    code = "insufficient_stock"

    def __init__(self, name: str, requested: int, available: int):
        self.name = name
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for {name}: requested {requested}, available {available}.",
            extra={"requested": requested, "available": available},
        )


class IdempotencyConflictError(ConflictError):
    code = "idempotency_conflict"
    default_detail = "Idempotency-Key was already used with a different request."


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        content = {"detail": exc.detail, "code": exc.code, **exc.extra}
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            headers=exc.headers or None,
        )
