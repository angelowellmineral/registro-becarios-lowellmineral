import os
import secrets
from datetime import datetime, timedelta
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature
from dotenv import load_dotenv
from fastapi import Request, Response

load_dotenv()

# --- SECRET_KEY ---
SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    # Fallback para que Render no crashee si olvidas la variable
    SECRET_KEY = "lowell-becarios-2026-clave-super-segura-de-32-caracteres-minimo-cambiar-en-prod"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
serializer = URLSafeTimedSerializer(SECRET_KEY, salt="lowell-session")

# --- Password ---
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# --- Cookie Session ---
def sign_cookie(value: str) -> str:
    return serializer.dumps(value)

def unsign_cookie(value: str):
    try:
        return serializer.loads(value)
    except (BadSignature, Exception):
        return None

def set_secure_cookie(response: Response, key: str, value: str, max_age: int = 3600*8):
    """Compatible con tu auth_router.py original"""
    response.set_cookie(
        key=key,
        value=value,
        max_age=max_age,
        httponly=True,
        secure=False,  # False para que funcione en http local y https render
        samesite="lax",
        path="/"
    )

def get_current_user(request: Request):
    token = request.cookies.get("session")
    if not token:
        return None
    data = unsign_cookie(token)
    return data

def get_current_user_role(request: Request):
    user = get_current_user(request)
    return user

# --- CSRF ---
def generate_csrf_token() -> str:
    return secrets.token_hex(32)

def validate_csrf_token(csrf_token_from_form: str, csrf_token_from_cookie: str) -> bool:
    if not csrf_token_from_form or not csrf_token_from_cookie:
        return False
    return secrets.compare_digest(csrf_token_from_form, csrf_token_from_cookie)

# --- Admin helpers ---
def create_admin_if_not_exists(db, username, password):
    """Usado por main.py si lo necesitas"""
    from . import models
    existing = db.query(models.User).filter(models.User.username == username).first()
    if not existing:
        user = models.User(
            username=username,
            password_hash=hash_password(password),
            nombre="Admin",
            apellidos="Lowell",
            rol="admin",
            estado="activo"
        )
        db.add(user)
        db.commit()
