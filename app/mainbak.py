import os
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware

Path("app/static/uploads/notas").mkdir(parents=True, exist_ok=True)
Path("app/static/uploads/pagos").mkdir(parents=True, exist_ok=True)

from app.database import get_db
from app import models, auth

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(title="Sistema Becarios Lowell - Seguro")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

from app.routers import auth_router, admin_router, supervisor_router, alumno_router

app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(supervisor_router.router)
app.include_router(alumno_router.router)

@app.get("/")
def root():
    return RedirectResponse(url="/login")

@app.get("/ver-pdf/{tipo}/{filename}")
def ver_pdf_protegido(tipo: str, filename: str, request: Request, db: Session = Depends(get_db)):
    s_uid = request.cookies.get("user_id")
    if not s_uid or not auth.unsign_cookie(s_uid):
        return RedirectResponse(url="/login")
    
    if tipo not in ["notas","pagos"]:
        return RedirectResponse(url="/login")
    
    safe_name = Path(filename).name
    if ".." in safe_name or "/" in safe_name or chr(92) in safe_name:
        return RedirectResponse(url="/login")
    
    allowed_ext = (".pdf",".jpg",".jpeg",".png")
    if not safe_name.lower().endswith(allowed_ext):
        return RedirectResponse(url="/login")
    
    file_path = Path(f"app/static/uploads/{tipo}/{safe_name}")
    try:
        file_path.resolve().relative_to(Path(f"app/static/uploads/{tipo}").resolve())
    except:
        return RedirectResponse(url="/login")
    
    if not file_path.exists():
        return RedirectResponse(url="/login")
    
    return FileResponse(file_path, filename=safe_name)

@app.get("/static/uploads/{path:path}")
def block_direct_uploads(path: str):
    return RedirectResponse(url="/login")
