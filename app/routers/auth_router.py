from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from ..database import get_db
from .. import models, auth

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
limiter = Limiter(key_func=get_remote_address)

@router.get("/login")
def login_page(request: Request):
    csrf = auth.generate_csrf_token()
    resp = templates.TemplateResponse(request, "login.html", {"request": request, "csrf_token": csrf})
    auth.set_secure_cookie(resp, "csrf_token", csrf)
    return resp

@router.post("/login")
@limiter.limit("5/minute")
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    # CSRF check opcional en login
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not auth.verify_password(password, user.password_hash):
        csrf = auth.generate_csrf_token()
        resp = templates.TemplateResponse(request, "login.html", {"request": request, "error": "Usuario o contraseña incorrectos", "csrf_token": csrf}, status_code=401)
        auth.set_secure_cookie(resp, "csrf_token", csrf)
        return resp
    
    redirect_url = "/admin" if user.rol=="admin" else "/supervisor" if user.rol=="supervisor" else "/alumno"
    resp = RedirectResponse(url=redirect_url, status_code=302)
    auth.set_secure_cookie(resp, "user_id", auth.sign_cookie(user.id))
    auth.set_secure_cookie(resp, "rol", auth.sign_cookie(user.rol))
    # Nuevo csrf para sesion
    auth.set_secure_cookie(resp, "csrf_token", auth.generate_csrf_token())
    return resp

@router.get("/logout")
def logout(request: Request):
    resp = RedirectResponse(url="/login", status_code=302)
    for k in ["user_id","rol","csrf_token"]:
        resp.delete_cookie(k, path="/")
    return resp
