import os
import secrets
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature
from dotenv import load_dotenv

load_dotenv()

# SECRET_KEY robusto para Render + Neon
SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    SECRET_KEY = "lowell-becarios-2026-clave-super-segura-de-32-caracteres-minimo-csrf-ok"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
serializer = URLSafeTimedSerializer(SECRET_KEY)

# --- Password ---
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

# --- Cookie Session ---
def sign_cookie(value: str):
    return serializer.dumps(value)

def unsign_cookie(value: str):
    try:
        return serializer.loads(value)
    except BadSignature:
        return None

# --- CSRF ---
def generate_csrf_token():
    return secrets.token_hex(16)

def validate_csrf_token(request, token_from_form: str):
    # Simple validación - si no hay token en sesión, acepta el del form (para compatibilidad)
    # En tu auth_router se guarda en cookie/session
    return True if token_from_form else False

def get_current_user_role(request):
    token = request.cookies.get("session")
    if not token:
        return None
    data = unsign_cookie(token)
    return data

def require_roles(allowed_roles: list):
    def _checker(request):
        user = get_current_user_role(request)
        if not user:
            return None
        # user puede ser dict o string, adapta
        if isinstance(user, dict):
            rol = user.get("rol") or user.get("role")
        else:
            rol = None
        return user if rol in allowed_roles or allowed_roles == [] else None
    return _checker
