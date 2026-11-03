
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from .. import models, auth
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_user(request: Request, db: Session):
    s_uid = request.cookies.get("user_id")
    s_rol = request.cookies.get("rol")
    if not s_uid or not s_rol: return None
    uid = auth.unsign_cookie(s_uid)
    rol = auth.unsign_cookie(s_rol)
    if not uid or not rol: return None
    try:
        return db.query(models.User).filter(models.User.id==int(uid)).first()
    except:
        return None

def get_dashboard_stats(db: Session):
    total_personas = db.query(models.User).filter(models.User.rol=="alumno").count()
    total_carreras = db.query(models.Alumno).count()
    total_unis = db.query(models.Universidad).count()
    total_centros = db.query(models.Centro).count()
    total_notas = db.query(models.RegistroNotas).count()
    total_pagos = db.query(models.RegistroPagos).count()
    total_monto = db.query(func.sum(models.PagoDetalle.monto)).scalar() or 0
    total_supervisores = db.query(models.User).filter(models.User.rol=="supervisor").count()
    total_admins = db.query(models.User).filter(models.User.rol=="admin").count()
    por_pais = db.query(models.Alumno.pais, func.count(models.Alumno.id)).group_by(models.Alumno.pais).all()
    por_estado = db.query(models.Alumno.estado, func.count(models.Alumno.id)).group_by(models.Alumno.estado).all()
    por_beca = db.query(models.Alumno.beca, func.count(models.Alumno.id)).group_by(models.Alumno.beca).all()
    por_tipo_beca = db.query(models.Alumno.tipo_beca, func.count(models.Alumno.id)).group_by(models.Alumno.tipo_beca).all()
    por_genero = db.query(models.Alumno.genero, func.count(models.Alumno.id)).group_by(models.Alumno.genero).all()
    por_universidad = db.query(models.Universidad.nombre, func.count(models.Alumno.id)).join(models.Alumno, models.Alumno.universidad_id==models.Universidad.id).group_by(models.Universidad.nombre).all()
    por_carrera = db.query(models.Carrera.nombre, func.count(models.Alumno.id)).join(models.Alumno, models.Alumno.carrera_id==models.Carrera.id).group_by(models.Carrera.nombre).all()
    por_centro = db.query(models.Centro.nombre, func.count(models.Alumno.id)).join(models.Alumno, models.Alumno.centro_id==models.Centro.id).group_by(models.Centro.nombre).all()
    por_semestre = db.query(models.Alumno.semestre, func.count(models.Alumno.id)).group_by(models.Alumno.semestre).order_by(models.Alumno.semestre).all()
    return {
        "total_personas": total_personas, "total_carreras": total_carreras, "total_unis": total_unis, "total_centros": total_centros,
        "total_notas": total_notas, "total_pagos": total_pagos, "total_monto": total_monto,
        "total_supervisores": total_supervisores, "total_admins": total_admins,
        "por_pais": por_pais, "por_estado": por_estado, "por_beca": por_beca, "por_tipo_beca": por_tipo_beca, "por_genero": por_genero,
        "por_universidad": por_universidad, "por_carrera": por_carrera, "por_centro": por_centro, "por_semestre": por_semestre
    }

@router.get("/admin")
def admin_dashboard_main(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol!="admin": return RedirectResponse(url="/login", status_code=302)
    stats = get_dashboard_stats(db)
    ultimos_alumnos = db.query(models.Alumno).order_by(models.Alumno.id.desc()).limit(5).all()
    ultimas_notas = db.query(models.RegistroNotas).order_by(models.RegistroNotas.id.desc()).limit(5).all()
    ultimos_pagos = db.query(models.RegistroPagos).order_by(models.RegistroPagos.id.desc()).limit(5).all()
    return templates.TemplateResponse(request, "admin/dashboard_main.html", {
        "request": request, "user": user, "stats": stats,
        "ultimos_alumnos": ultimos_alumnos, "ultimas_notas": ultimas_notas, "ultimos_pagos": ultimos_pagos
    })

@router.get("/admin/usuarios")
def admin_usuarios(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol!="admin": return RedirectResponse(url="/login", status_code=302)
    alumnos = db.query(models.Alumno).all()
    users_alumnos = db.query(models.User).filter(models.User.rol=="alumno").all()
    users_supervisores = db.query(models.User).filter(models.User.rol.in_(["supervisor","admin"])).all()
    centros = db.query(models.Centro).all()
    universidades = db.query(models.Universidad).all()
    carreras = db.query(models.Carrera).all()
    error = request.query_params.get("error")
    error_username = request.query_params.get("username", "")
    return templates.TemplateResponse(request, "admin/dashboard.html", {
        "request": request, "user": user, "alumnos": alumnos,
        "users_alumnos": users_alumnos, "users_supervisores": users_supervisores,
        "centros": centros, "universidades": universidades, "carreras": carreras,
        "error": error, "error_username": error_username
    })


@router.get("/admin/api/check-username")
def check_username_admin(request: Request, q: str = "", db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]:
        return {"exists": False}
    q = q.strip()
    if not q:
        return {"exists": False}
    exists = db.query(models.User).filter(models.User.username==q).first() is not None
    return {"exists": exists, "username": q}

@router.get("/supervisor/api/check-username")
def check_username_supervisor(request: Request, q: str = "", db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]:
        return {"exists": False}
    q = q.strip()
    if not q:
        return {"exists": False}
    exists = db.query(models.User).filter(models.User.username==q).first() is not None
    return {"exists": exists, "username": q}


@router.post("/admin/usuarios/crear")
def crear_usuario(request: Request, username: str = Form(...), password: str = Form(...), nombre: str = Form(...), apellidos: str = Form(...), rol: str = Form(...), db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol!="admin": return RedirectResponse(url="/login", status_code=302)
    username_clean = username.strip()
    if not username_clean:
        return RedirectResponse(url="/admin/usuarios?error=username_empty", status_code=302)
    if db.query(models.User).filter(models.User.username==username_clean).first():
        return RedirectResponse(url=f"/admin/usuarios?error=username_exists&username={username_clean}", status_code=302)
    if rol not in ["supervisor","admin"]: rol="supervisor"
    nuevo = models.User(username=username, password_hash=auth.hash_password(password), nombre=nombre, apellidos=apellidos, rol=rol)
    db.add(nuevo)
    db.commit()
    return RedirectResponse(url="/admin/usuarios", status_code=302)

@router.post("/admin/usuarios/{uid}/editar")
def editar_usuario(uid: int, request: Request, nombre: str = Form(...), apellidos: str = Form(...), new_password: str = Form(None), db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol!="admin": return RedirectResponse(url="/login", status_code=302)
    u = db.query(models.User).filter(models.User.id==uid).first()
    if not u: return RedirectResponse(url="/admin/usuarios", status_code=302)
    u.nombre=nombre; u.apellidos=apellidos
    if new_password and new_password.strip()!="":
        u.password_hash=auth.hash_password(new_password.strip())
    db.commit()
    return RedirectResponse(url="/admin/usuarios", status_code=302)

@router.get("/admin/usuarios/{uid}/eliminar")
def eliminar_usuario(uid: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol!="admin": return RedirectResponse(url="/login", status_code=302)
    if uid==user.id: return RedirectResponse(url="/admin/usuarios", status_code=302)
    u = db.query(models.User).filter(models.User.id==uid).first()
    if u:
        if u.alumno_profile:
            db.delete(u.alumno_profile)
        db.delete(u)
        db.commit()
    return RedirectResponse(url="/admin/usuarios", status_code=302)

@router.post("/admin/centros/crear")
def crear_centro(nombre: str = Form(...), request: Request = None, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]: return RedirectResponse(url="/login", status_code=302)
    if not db.query(models.Centro).filter(models.Centro.nombre==nombre).first():
        db.add(models.Centro(nombre=nombre.strip()))
        db.commit()
    return RedirectResponse(url="/admin/usuarios" if user.rol=="admin" else "/supervisor/mis-alumnos", status_code=302)

@router.post("/admin/centros/{cid}/editar")
def editar_centro(cid: int, nombre: str = Form(...), request: Request = None, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol!="admin": return RedirectResponse(url="/login", status_code=302)
    c = db.query(models.Centro).filter(models.Centro.id==cid).first()
    if c: c.nombre=nombre.strip(); db.commit()
    return RedirectResponse(url="/admin/usuarios", status_code=302)

@router.get("/admin/centros/{cid}/eliminar")
def eliminar_centro(cid: int, request: Request = None, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol!="admin": return RedirectResponse(url="/login", status_code=302)
    c = db.query(models.Centro).filter(models.Centro.id==cid).first()
    if c: db.delete(c); db.commit()
    return RedirectResponse(url="/admin/usuarios", status_code=302)

@router.post("/admin/universidades/crear")
def crear_uni(nombre: str = Form(...), request: Request = None, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]: return RedirectResponse(url="/login", status_code=302)
    if not db.query(models.Universidad).filter(models.Universidad.nombre==nombre).first():
        db.add(models.Universidad(nombre=nombre.strip()))
        db.commit()
    return RedirectResponse(url="/admin/usuarios" if user.rol=="admin" else "/supervisor/mis-alumnos", status_code=302)

@router.post("/admin/universidades/{uid}/editar")
def editar_uni(uid: int, nombre: str = Form(...), request: Request = None, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol!="admin": return RedirectResponse(url="/login", status_code=302)
    u = db.query(models.Universidad).filter(models.Universidad.id==uid).first()
    if u: u.nombre=nombre.strip(); db.commit()
    return RedirectResponse(url="/admin/usuarios", status_code=302)

@router.get("/admin/universidades/{uid}/eliminar")
def eliminar_uni(uid: int, request: Request = None, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol!="admin": return RedirectResponse(url="/login", status_code=302)
    u = db.query(models.Universidad).filter(models.Universidad.id==uid).first()
    if u: db.delete(u); db.commit()
    return RedirectResponse(url="/admin/usuarios", status_code=302)

@router.post("/admin/carreras/crear")
def crear_carrera(nombre: str = Form(...), request: Request = None, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]: return RedirectResponse(url="/login", status_code=302)
    if not db.query(models.Carrera).filter(models.Carrera.nombre==nombre).first():
        db.add(models.Carrera(nombre=nombre.strip()))
        db.commit()
    return RedirectResponse(url="/admin/usuarios" if user.rol=="admin" else "/supervisor/mis-alumnos", status_code=302)

@router.post("/admin/carreras/{cid}/editar")
def editar_carrera(cid: int, nombre: str = Form(...), request: Request = None, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol!="admin": return RedirectResponse(url="/login", status_code=302)
    c = db.query(models.Carrera).filter(models.Carrera.id==cid).first()
    if c: c.nombre=nombre.strip(); db.commit()
    return RedirectResponse(url="/admin/usuarios", status_code=302)

@router.get("/admin/carreras/{cid}/eliminar")
def eliminar_carrera(cid: int, request: Request = None, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol!="admin": return RedirectResponse(url="/login", status_code=302)
    c = db.query(models.Carrera).filter(models.Carrera.id==cid).first()
    if c: db.delete(c); db.commit()
    return RedirectResponse(url="/admin/usuarios", status_code=302)
