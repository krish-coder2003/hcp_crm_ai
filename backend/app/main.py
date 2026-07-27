from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import chat, interactions

app = FastAPI(
    title="AI-First CRM - HCP Interaction Module",
    description="Production-grade API for AI-first logging of HCP interactions.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Versioning: primary v1, fallback legacy alias
app.include_router(chat.router, prefix="/api/v1")
app.include_router(interactions.router, prefix="/api/v1")

app.include_router(chat.router, prefix="/api")
app.include_router(interactions.router, prefix="/api")


@app.get("/api/v1/health", tags=["health"])
@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Clean validation error response structure instead of raw Pydantic details."""
    details = []
    for error in exc.errors():
        field = ".".join([str(loc) for loc in error["loc"][1:]]) if len(error["loc"]) > 1 else str(error["loc"][0])
        details.append({
            "field": field,
            "message": error["msg"]
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": details
            }
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Global exception handler to capture unexpected internal server errors and format cleanly."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred on the server.",
                "details": str(exc) if "sqlite" in settings.database_url or "localhost" in settings.database_url else None
            }
        }
    )
