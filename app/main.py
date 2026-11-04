import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .database import engine, Base
from .routers import auth_router, admin_router, supervisor_router, alumno_router

# Crea tablas automaticamente al iniciar (para Neon)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Lowell Becarios")

# Asegura que static exista (en Koyeb es efimero pero se crea)
os.makedirs("app/static/uploads/notas", exist_ok=True)
os.makedirs("app/static/uploads/pagos", exist_ok=True)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(supervisor_router.router)
app.include_router(alumno_router.router)

@app.get("/")
def root():
    return {"status": "Lowell Becarios OK", "docs": "/docs"}
