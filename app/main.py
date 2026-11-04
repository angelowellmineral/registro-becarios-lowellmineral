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

@app.get("/init-admin")
def init_admin():
    """Crea el admin inicial - segun models.py REAL (sin estado)"""
    db = SessionLocal()
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        def hash_password(pw):
            return pwd_context.hash(pw)

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
                rol="admin"
            )
            db.add(user)
            db.commit()
            return {"status": "creado", "username": username, "password": password}
    except Exception as e:
        tb = traceback.format_exc()
        return JSONResponse(status_code=500, content={"error": str(e), "trace": tb})
    finally:
        db.close()
