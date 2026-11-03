import os
from dotenv import load_dotenv
load_dotenv()

from app.database import engine, Base, SessionLocal
from app import models, auth

# Solo en dev crear tablas, en prod usar alembic
ENV = os.getenv("ENVIRONMENT","production")
if ENV != "production":
    Base.metadata.create_all(bind=engine)
    print("Tablas creadas (solo DEV)")

db=SessionLocal()

ADMIN_USER=os.getenv("ADMIN_USER")
ADMIN_PASS=os.getenv("ADMIN_PASS")

if not ADMIN_USER or not ADMIN_PASS:
    print("ERROR: Define ADMIN_USER y ADMIN_PASS en .env para crear admin inicial")
    db.close()
    exit(1)

if len(ADMIN_PASS) < 8:
    print("ERROR: ADMIN_PASS debe tener al menos 8 caracteres")
    db.close()
    exit(1)

u=db.query(models.User).filter_by(username=ADMIN_USER).first()
if not u:
    admin=models.User(username=ADMIN_USER, password_hash=auth.hash_password(ADMIN_PASS), nombre="Admin", apellidos="Lowell", rol="admin")
    db.add(admin);db.commit()
    print(f"Admin creado: {ADMIN_USER} / ******")
else:
    print(f"Admin ya existe: {ADMIN_USER}")

db.close()
print("Listo! Recuerda borrar RUN.py en producción o protegerlo")
