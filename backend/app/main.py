from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import chat, interactions

# Create tables on startup if they don't exist yet. For a real production
# deployment, use Alembic migrations instead - this is kept simple here so
# the reviewer can run the app with zero extra setup steps.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI-First CRM - HCP Interaction Module")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(interactions.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
