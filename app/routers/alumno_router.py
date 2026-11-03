from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, auth
from pathlib import Path
import shutil
from datetime import datetime
from typing import List
import uuid
import os

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
UPLOAD_NOTAS = Path("app/static/uploads/notas")
UPLOAD_PAGOS = Path("app/static/uploads/pagos")

# Config seguridad uploads
ALLOWED_EXT = {".pdf",".jpg",".jpeg",".png"}
ALLOWED_MIME = {"application/pdf","image/jpeg","image/png","image/jpg"}
MAX_SIZE = 10 * 1024 * 1024  # 10MB

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

def validate_csrf(request: Request, csrf_form: str = Form(None)):
    cookie_csrf = request.cookies.get("csrf_token")
    form_csrf = csrf_form
    # Si no hay token, buscar en form data manualmente
    if not form_csrf:
        return False
    if not cookie_csrf:
        return False
    return cookie_csrf == form_csrf and auth.validate_csrf_token(form_csrf)

def save_file_secure(upload: UploadFile, dest_folder: Path):
    try:
        dest_folder.mkdir(parents=True, exist_ok=True)
    except:
        pass
    if not upload or not upload.filename: return None
    if upload.filename.strip() == "": return None
    
    # Validar tamaño leyendo chunk
    upload.file.seek(0, os.SEEK_END)
    size = upload.file.tell()
    upload.file.seek(0)
    if size > MAX_SIZE:
        return None
    if size == 0:
        return None
    
    # Validar extension
    ext = Path(upload.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return None
    
    # Nombre seguro aleatorio + ext
    safe_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    dest = dest_folder / safe_name
    try:
        with open(dest, "wb") as b:
            shutil.copyfileobj(upload.file, b)
        return str(dest)
    except Exception as e:
        print(f"Error save_file: {e}")
        return None

def delete_file_safe(path_str: str):
    if not path_str: return
    try:
        p = Path(path_str)
        # Solo borrar si esta dentro de uploads
        if "app/static/uploads" not in str(p.resolve()):
            return
        if p.exists():
            p.unlink()
    except:
        pass

@router.get("/alumno")
def alumno_dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol!="alumno": return RedirectResponse(url="/login", status_code=302)
    alumnos = db.query(models.Alumno).filter(models.Alumno.user_id==user.id).all()
    csrf = request.cookies.get("csrf_token") or auth.generate_csrf_token()
    return templates.TemplateResponse(request, "alumno/dashboard.html", {"request": request, "user": user, "alumnos": alumnos, "csrf_token": csrf})

@router.get("/alumno/detalle/{alumno_id}")
def alumno_detalle(request: Request, alumno_id: int, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    alumno = db.query(models.Alumno).filter(models.Alumno.id==alumno_id).first()
    if not alumno: return RedirectResponse(url="/alumno" if user.rol=="alumno" else "/admin", status_code=302)
    # FIX IDOR #8 - alumno solo ve suyo, supervisor/admin ven todo pero logueado
    if user.rol=="alumno" and alumno.user_id != user.id:
        return RedirectResponse(url="/alumno", status_code=302)
    es_admin = user.rol in ["admin","supervisor"]
    csrf = request.cookies.get("csrf_token") or auth.generate_csrf_token()
    return templates.TemplateResponse(request, "alumno/detalle.html", {"request": request, "user": user, "alumno": alumno, "es_admin": es_admin, "csrf_token": csrf})

@router.post("/alumno/notas/crear")
def crear_registro_notas(
    request: Request,
    semestre: int = Form(...),
    alumno_id: int = Form(...),
    csrf_token: str = Form(...),
    archivo: UploadFile = File(None),
    cursos: List[str] = Form([]),
    notas: List[str] = Form([]),
    db: Session = Depends(get_db)
):
    user = get_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    # CSRF check FIX #6
    if not validate_csrf(request, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF invalido")
    
    alumno = db.query(models.Alumno).filter(models.Alumno.id==alumno_id).first()
    if not alumno: return RedirectResponse(url="/alumno", status_code=302)
    if user.rol=="alumno" and alumno.user_id != user.id:
        return RedirectResponse(url="/alumno", status_code=302)
    
    # Validar semestre rango
    if semestre < 1 or semestre > 20:
        return RedirectResponse(url=f"/alumno/detalle/{alumno.id}?tab=notas#notas", status_code=302)
    
    archivo_path = save_file_secure(archivo, UPLOAD_NOTAS)
    registro = models.RegistroNotas(alumno_id=alumno.id, semestre=semestre, archivo_path=archivo_path)
    db.add(registro); db.commit(); db.refresh(registro)
    for cur, not_val in zip(cursos, notas):
        if not cur: cur=""
        if not not_val: not_val=""
        if cur.strip()=="" and not_val.strip()=="": continue
        # Sanitizar longitud
        cur = cur.strip()[:100]
        not_val = not_val.strip()[:10]
        det = models.NotaDetalle(registro_id=registro.id, curso=cur, nota=not_val)
        db.add(det)
    db.commit()
    return RedirectResponse(url=f"/alumno/detalle/{alumno.id}?tab=notas#notas", status_code=302)

@router.get("/alumno/notas/registro/{rid}/eliminar")
def eliminar_registro_notas(rid: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    reg = db.query(models.RegistroNotas).filter(models.RegistroNotas.id==rid).first()
    if not reg: return RedirectResponse(url="/alumno", status_code=302)
    alumno = db.query(models.Alumno).filter(models.Alumno.id==reg.alumno_id).first()
    if user.rol=="alumno" and alumno.user_id!=user.id: return RedirectResponse(url="/alumno", status_code=302)
    # FIX #12 borrar archivo fisico
    delete_file_safe(reg.archivo_path)
    db.delete(reg); db.commit()
    return RedirectResponse(url=f"/alumno/detalle/{alumno.id}?tab=notas#notas", status_code=302)

@router.post("/alumno/pagos/crear")
def crear_registro_pagos(
    request: Request,
    semestre: int = Form(...),
    numero_comprobantes: str = Form(...),
    alumno_id: int = Form(...),
    csrf_token: str = Form(...),
    archivo: UploadFile = File(None),
    cuotas: List[str] = Form([]),
    montos: List[str] = Form([]),
    db: Session = Depends(get_db)
):
    user = get_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    if not validate_csrf(request, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF invalido")
    
    alumno = db.query(models.Alumno).filter(models.Alumno.id==alumno_id).first()
    if not alumno: return RedirectResponse(url="/alumno", status_code=302)
    if user.rol=="alumno" and alumno.user_id != user.id:
        return RedirectResponse(url="/alumno", status_code=302)
    
    if semestre < 1 or semestre > 20:
        return RedirectResponse(url=f"/alumno/detalle/{alumno.id}?tab=pagos#pagos", status_code=302)
    
    numero_comprobantes = numero_comprobantes.strip()[:50]
    
    archivo_path = save_file_secure(archivo, UPLOAD_PAGOS)
    registro = models.RegistroPagos(alumno_id=alumno.id, semestre=semestre, numero_comprobantes=numero_comprobantes, archivo_path=archivo_path)
    db.add(registro); db.commit(); db.refresh(registro)
    for cu, mo in zip(cuotas, montos):
        if not cu: cu=""
        if not mo: mo="0"
        if cu.strip()=="" and mo.strip()=="": continue
        try:
            monto_val = float(mo)
            if monto_val < 0 or monto_val > 100000: continue
        except:
            continue
        det = models.PagoDetalle(registro_id=registro.id, cuota=cu.strip()[:50], monto=monto_val)
        db.add(det)
    db.commit()
    return RedirectResponse(url=f"/alumno/detalle/{alumno.id}?tab=pagos#pagos", status_code=302)

@router.get("/alumno/pagos/registro/{rid}/eliminar")
def eliminar_registro_pagos(rid: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    reg = db.query(models.RegistroPagos).filter(models.RegistroPagos.id==rid).first()
    if not reg: return RedirectResponse(url="/alumno", status_code=302)
    alumno = db.query(models.Alumno).filter(models.Alumno.id==reg.alumno_id).first()
    if user.rol=="alumno" and alumno.user_id!=user.id: return RedirectResponse(url="/alumno", status_code=302)
    delete_file_safe(reg.archivo_path)
    db.delete(reg); db.commit()
    return RedirectResponse(url=f"/alumno/detalle/{alumno.id}?tab=pagos#pagos", status_code=302)
