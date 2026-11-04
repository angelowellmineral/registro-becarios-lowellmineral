import os
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv

load_dotenv()

# Lee SECRET_KEY de entorno, si no existe usa el de tu .env local como fallback pero con al menos 32 chars
SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    # Fallback seguro para que no crashee en Render si olvidas poner la variable
    SECRET_KEY = os.getenv("SECRET_KEY_FALLBACK", "lowell-becarios-2026-clave-super-segura-de-32-caracteres-minimo")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
serializer = URLSafeTimedSerializer(SECRET_KEY)

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def sign_cookie(value: str):
    return serializer.dumps(value)

def unsign_cookie(value: str):
    try:
        return serializer.loads(value)
    except:
        return None
