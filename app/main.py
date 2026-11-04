from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from .database import engine, Base, SessionLocal
from .routers import auth_router, admin_router, supervisor_router, alumno_router
from . import models
import os
import traceback

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Lowell Becarios")

# Static
if os.path.isdir("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Routers
app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(supervisor_router.router)
app.include_router(alumno_router.router)

@app.get("/")
def home():
    return RedirectResponse(url="/login", status_code=302)

@app.get("/health")
def health():
    return {"status": "Lowell Becarios OK", "db": "Neon connected"}
