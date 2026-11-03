from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# CONEXION DURA, SIN .env, SIN CARACTERES RAROS
DATABASE_URL = "postgresql+psycopg2://postgres:postgres123@localhost:5432/lowell_becarios"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()