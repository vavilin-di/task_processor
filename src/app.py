from dishka.integrations.fastapi import setup_dishka
from fastapi import APIRouter, FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from .di import create_di_container
from .routers import tasks_router
from .settings import get_settings

settings = get_settings()
app = FastAPI(title=settings.APP_TITLE, version=settings.APP_VERSION)

base_router = APIRouter(prefix=settings.API_PREFIX)

version_router = APIRouter(prefix=settings.API_VERSION_PREFIX)
version_router.include_router(tasks_router)

base_router.include_router(version_router)

app.include_router(base_router)

setup_dishka(container=create_di_container(), app=app)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Конфликт данных. Возможно, связанная запись была удалена."},
    )
