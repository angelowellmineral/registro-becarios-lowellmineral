from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import os
import secrets

# OBLIGATORIO en .env, sin default debil
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY no configurado o muy corto. Define SECRET_KEY de al menos 32 chars en .env")

serializer = URLSafeTimedSerializer(SECRET_KEY)
csrf_serializer = URLSafeTimedSerializer(SECRET_KEY + "_csrf")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(p): 
    return pwd_context.hash(p)

def verify_password(p, h): 
    return pwd_context.verify(p, h)

def sign_cookie(v): 
    return serializer.dumps(str(v))

def unsign_cookie(t):
    try:
        return serializer.loads(t, max_age=86400*7)
    except (BadSignature, SignatureExpired):
        return None

def generate_csrf_token():
    return csrf_serializer.dumps(secrets.token_urlsafe(32))

def validate_csrf_token(token):
    try:
        csrf_serializer.loads(token, max_age=86400)
        return True
    except:
        return False

# Cookie segura centralizada
def set_secure_cookie(response, key, value):
    is_prod = os.getenv("ENVIRONMENT","production") == "production"
    response.set_cookie(
        key=key, 
        value=value, 
        httponly=True, 
        secure=is_prod,  # True en prod con HTTPS
        samesite="lax",
        max_age=86400*7,
        path="/"
    )
