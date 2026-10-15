from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.encoders import jsonable_encoder

async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "type": "HTTPException",
                "message": exc.detail
            }
        }
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "type": "ValidationError",
                "message": "Request validation failed",
                "details": jsonable_encoder(exc.errors())
            }
        }
    )


async def general_exception_handler(
    request: Request,
    exc: Exception
):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "type": "InternalServerError",
                "message": "An unexpected error occurred"
            }
        }
    )


class NotificationNotFoundError(Exception):
    """Raised when a notification does not exist."""
    pass
from fastapi import Request
from fastapi.responses import JSONResponse


class AnalyticsNotFoundException(Exception):
    """Raised when an analytics record or tenant is not found."""

    def __init__(self, message: str = "Analytics record not found"):
        self.message = message
        super().__init__(self.message)


class AnalyticsValidationException(Exception):
    """Raised when analytics data fails business validation."""

    def __init__(self, message: str = "Invalid analytics data"):
        self.message = message
        super().__init__(self.message)


class AnalyticsDatabaseException(Exception):
    """Raised when a database operation fails."""

    def __init__(self, message: str = "Database operation failed"):
        self.message = message
        super().__init__(self.message)


async def analytics_not_found_handler(
    request: Request,
    exc: AnalyticsNotFoundException
):
    return JSONResponse(
        status_code=404,
        content={"detail": exc.message}
    )


async def analytics_validation_handler(
    request: Request,
    exc: AnalyticsValidationException
):
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message}
    )


async def analytics_database_handler(
    request: Request,
    exc: AnalyticsDatabaseException
):
    return JSONResponse(
        status_code=500,
        content={"detail": exc.message}
    )
