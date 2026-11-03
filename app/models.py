from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Boolean, Float, Text
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    nombre = Column(String)
    apellidos = Column(String)
    rol = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    alumno_profile = relationship("Alumno", foreign_keys="Alumno.user_id", back_populates="user", uselist=False)
    alumnos_creados = relationship("Alumno", foreign_keys="Alumno.creado_por_id", back_populates="creador")

class Centro(Base):
    __tablename__ = "centros"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True)

class Universidad(Base):
    __tablename__ = "universidades"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True)

class Carrera(Base):
    __tablename__ = "carreras"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True)

class Alumno(Base):
    __tablename__ = "alumnos"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    creado_por_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    apellidos = Column(String)
    nombres = Column(String)
    cedula = Column(String)
    celular = Column(String)
    universidad_id = Column(Integer, ForeignKey("universidades.id"))
    carrera_id = Column(Integer, ForeignKey("carreras.id"))
    centro_id = Column(Integer, ForeignKey("centros.id"))
    actual_semestre = Column(String)
    semestre = Column(Integer)
    inicia_beca = Column(Date, nullable=True)
    beca = Column(String)
    tipo_beca = Column(String)
    alimentacion = Column(String)
    arriendo = Column(String)
    matricula = Column(String)
    genero = Column(String)
    estado = Column(String)
    pais = Column(String)
    observacion = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id], back_populates="alumno_profile")
    creador = relationship("User", foreign_keys=[creado_por_id], back_populates="alumnos_creados")
    universidad = relationship("Universidad")
    carrera = relationship("Carrera")
    centro = relationship("Centro")
    registros_notas = relationship("RegistroNotas", back_populates="alumno", cascade="all, delete-orphan")
    registros_pagos = relationship("RegistroPagos", back_populates="alumno", cascade="all, delete-orphan")

class RegistroNotas(Base):
    __tablename__ = "registro_notas"
    id = Column(Integer, primary_key=True)
    alumno_id = Column(Integer, ForeignKey("alumnos.id"))
    semestre = Column(Integer)
    archivo_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    alumno = relationship("Alumno", back_populates="registros_notas")
    detalles = relationship("NotaDetalle", back_populates="registro", cascade="all, delete-orphan")

class NotaDetalle(Base):
    __tablename__ = "notas_detalle"
    id = Column(Integer, primary_key=True)
    registro_id = Column(Integer, ForeignKey("registro_notas.id"))
    curso = Column(String)
    nota = Column(String)
    registro = relationship("RegistroNotas", back_populates="detalles")

class RegistroPagos(Base):
    __tablename__ = "registro_pagos"
    id = Column(Integer, primary_key=True)
    alumno_id = Column(Integer, ForeignKey("alumnos.id"))
    semestre = Column(Integer)
    numero_comprobantes = Column(String)
    archivo_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    alumno = relationship("Alumno", back_populates="registros_pagos")
    detalles = relationship("PagoDetalle", back_populates="registro", cascade="all, delete-orphan")

class PagoDetalle(Base):
    __tablename__ = "pagos_detalle"
    id = Column(Integer, primary_key=True)
    registro_id = Column(Integer, ForeignKey("registro_pagos.id"))
    cuota = Column(String)
    monto = Column(Float)
    registro = relationship("RegistroPagos", back_populates="detalles")