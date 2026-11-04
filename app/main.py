from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from .database import engine, Base, SessionLocal
from .routers import auth_router, admin_router, supervisor_router, alumno_router
from . import models
from .auth import hash_password
import os

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

@app.get("/init-admin")
def init_admin():
    """Crea el admin inicial - BORRA ESTE ENDPOINT DESPUES DE USARLO"""
    db = SessionLocal()
    try:
        username = "admin_lowell"
        password = "Lowell2026!"
        
        existing = db.query(models.User).filter(models.User.username == username).first()
        if existing:
            existing.password_hash = hash_password(password)
            db.commit()
            return {"status": "actualizado", "username": username, "password": password, "msg": "Ya existia, password reseteado"}
        else:
            user = models.User(
                username=username,
                password_hash=hash_password(password),
                nombre="Angelo",
                apellidos="Delgado",
                rol="admin",
                estado="activo"
            )
            db.add(user)
            db.commit()
            return {"status": "creado", "username": username, "password": password}
    finally:
        db.close()
