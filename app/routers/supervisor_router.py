
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from .. import models, auth
from datetime import datetime
import io
import openpyxl

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
    # grupos
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
        "por_pais": por_pais, "por_estado": por_estado, "por_beca": por_beca, "por_tipo_beca": por_tipo_beca, "por_genero": por_genero,
        "por_universidad": por_universidad, "por_carrera": por_carrera, "por_centro": por_centro, "por_semestre": por_semestre
    }

@router.get("/supervisor")
def supervisor_dashboard_main(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]: return RedirectResponse(url="/login", status_code=302)
    stats = get_dashboard_stats(db)
    ultimos_alumnos = db.query(models.Alumno).order_by(models.Alumno.id.desc()).limit(5).all()
    ultimas_notas = db.query(models.RegistroNotas).order_by(models.RegistroNotas.id.desc()).limit(5).all()
    ultimos_pagos = db.query(models.RegistroPagos).order_by(models.RegistroPagos.id.desc()).limit(5).all()
    return templates.TemplateResponse(request, "supervisor/dashboard_main.html", {
        "request": request, "user": user, "stats": stats,
        "ultimos_alumnos": ultimos_alumnos, "ultimas_notas": ultimas_notas, "ultimos_pagos": ultimos_pagos
    })

@router.get("/supervisor/mis-alumnos")
def supervisor_mis_alumnos(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]: return RedirectResponse(url="/login", status_code=302)
    users_alumnos = db.query(models.User).filter(models.User.rol=="alumno").all()
    personas = []
    for u in users_alumnos:
        alumnos_de_persona = db.query(models.Alumno).filter(models.Alumno.user_id==u.id).all()
        primer = alumnos_de_persona[0] if alumnos_de_persona else None
        personas.append({"user": u, "alumno": primer, "total_carreras": len(alumnos_de_persona)})
    centros = db.query(models.Centro).all()
    universidades = db.query(models.Universidad).all()
    carreras = db.query(models.Carrera).all()
    error = request.query_params.get("error")
    error_username = request.query_params.get("username", "")
    return templates.TemplateResponse(request, "supervisor/dashboard.html", {
        "request": request, "user": user, "personas": personas,
        "centros": centros, "universidades": universidades, "carreras": carreras,
        "error": error, "error_username": error_username
    })



@router.get("/supervisor/buscar/universidades")
def buscar_universidades(request: Request, q: str = "", db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]:
        return []
    q = q.strip()
    if len(q) < 1:
        # Return first 20 if empty
        unis = db.query(models.Universidad).order_by(models.Universidad.nombre).limit(20).all()
    else:
        unis = db.query(models.Universidad).filter(models.Universidad.nombre.ilike(f"%{q}%")).order_by(models.Universidad.nombre).limit(20).all()
    return [{"id": u.id, "nombre": u.nombre} for u in unis]

@router.get("/supervisor/buscar/carreras")
def buscar_carreras(request: Request, q: str = "", db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]:
        return []
    q = q.strip()
    if len(q) < 1:
        cars = db.query(models.Carrera).order_by(models.Carrera.nombre).limit(20).all()
    else:
        cars = db.query(models.Carrera).filter(models.Carrera.nombre.ilike(f"%{q}%")).order_by(models.Carrera.nombre).limit(20).all()
    return [{"id": c.id, "nombre": c.nombre} for c in cars]


@router.get("/supervisor/carreras")
def supervisor_carreras(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]: return RedirectResponse(url="/login", status_code=302)
    alumnos = db.query(models.Alumno).all()
    centros = db.query(models.Centro).all()
    universidades = db.query(models.Universidad).all()
    carreras = db.query(models.Carrera).all()
    return templates.TemplateResponse(request, "supervisor/carreras.html", {
        "request": request, "user": user, "alumnos": alumnos,
        "centros": centros, "universidades": universidades, "carreras": carreras
    })

@router.get("/supervisor/export/personas/excel")
def export_personas_excel(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]: return RedirectResponse(url="/login", status_code=302)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Mis Alumnos - Personas"
    headers = ["Cedula", "Usuario", "Apellidos Nombres", "Celular", "Genero", "Pais", "Carreras"]
    ws.append(headers)
    users_alumnos = db.query(models.User).filter(models.User.rol=="alumno").all()
    for u in users_alumnos:
        alumnos = db.query(models.Alumno).filter(models.Alumno.user_id==u.id).all()
        primer = alumnos[0] if alumnos else None
        cedula = primer.cedula if primer else ""
        nombres = f"{primer.apellidos} {primer.nombres}" if primer else f"{u.apellidos} {u.nombre}"
        celular = primer.celular if primer else ""
        genero = primer.genero if primer else ""
        pais = primer.pais if primer else ""
        total = len(alumnos)
        ws.append([cedula, u.username, nombres, celular, genero, pais, total])
    output = io.BytesIO()
    wb.save(output); output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Reporte_Mis_Alumnos_Personas.xlsx"})

@router.get("/supervisor/export/carreras/excel")
def export_carreras_excel(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]: return RedirectResponse(url="/login", status_code=302)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Carreras"
    headers = ["Cedula","Nombre completo","Universidad","Carrera","Pais","Semestre (numero)","Actual Semestre","Beca","Tipo Beca","Estado","Centro","Alimentacion","Arriendo","Matricula","Observacion"]
    ws.append(headers)
    alumnos = db.query(models.Alumno).all()
    for a in alumnos:
        nombre_completo = f"{a.apellidos} {a.nombres}"
        uni = a.universidad.nombre if a.universidad else ""
        car = a.carrera.nombre if a.carrera else ""
        centro = a.centro.nombre if a.centro else ""
        ws.append([a.cedula, nombre_completo, uni, car, a.pais, a.semestre, a.actual_semestre, a.beca, a.tipo_beca, a.estado, centro, a.alimentacion, a.arriendo, a.matricula, a.observacion or ""])
    output = io.BytesIO()
    wb.save(output); output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Reporte_Carreras.xlsx"})

@router.get("/supervisor/reportes/notas")
def reportes_notas(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]: return RedirectResponse(url="/login", status_code=302)
    registros = db.query(models.RegistroNotas).all()
    filas = []
    for reg in registros:
        alumno = db.query(models.Alumno).filter(models.Alumno.id==reg.alumno_id).first()
        if not alumno: continue
        for det in reg.detalles:
            filas.append({"alumno": alumno, "registro": reg, "detalle": det})
    return templates.TemplateResponse(request, "supervisor/reportes_notas.html", {"request": request, "user": user, "filas": filas})

@router.get("/supervisor/reportes/notas/excel")
def export_notas_excel(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]: return RedirectResponse(url="/login", status_code=302)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte Notas"
    headers = ["Cedula","Nombre completo","Universidad","Carrera","Semestre (numero) Alumno","Actual Semestre Alumno","Ruta PDF/Imagen","Semestre (numero) Bloque Notas","Fecha Carga","Curso","Nota"]
    ws.append(headers)
    registros = db.query(models.RegistroNotas).all()
    for reg in registros:
        alumno = db.query(models.Alumno).filter(models.Alumno.id==reg.alumno_id).first()
        if not alumno: continue
        nombre = f"{alumno.apellidos} {alumno.nombres}"
        uni = alumno.universidad.nombre if alumno.universidad else ""
        car = alumno.carrera.nombre if alumno.carrera else ""
        for det in reg.detalles:
            ruta = reg.archivo_path or ""
            ruta_excel = ""
            if ruta:
                try:
                    fname = ruta.split("/")[-1]
                    tipo = ruta.split("/")[-2] if "/" in ruta else "notas"
                    if tipo not in ["notas","pagos"]: tipo="notas"
                    ruta_excel = f"/ver-pdf/{tipo}/{fname}"
                except: ruta_excel = ruta
            ws.append([alumno.cedula, nombre, uni, car, alumno.semestre, alumno.actual_semestre, ruta_excel, reg.semestre, reg.created_at.strftime("%Y-%m-%d") if reg.created_at else "", det.curso, det.nota])
    output = io.BytesIO()
    wb.save(output); output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=Reporte_Notas.xlsx"})

@router.get("/supervisor/reportes/pagos")
def reportes_pagos(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]: return RedirectResponse(url="/login", status_code=302)
    registros = db.query(models.RegistroPagos).all()
    filas = []
    for reg in registros:
        alumno = db.query(models.Alumno).filter(models.Alumno.id==reg.alumno_id).first()
        if not alumno: continue
        for det in reg.detalles:
            filas.append({"alumno": alumno, "registro": reg, "detalle": det})
    return templates.TemplateResponse(request, "supervisor/reportes_pagos.html", {"request": request, "user": user, "filas": filas})

@router.get("/supervisor/reportes/pagos/excel")
def export_pagos_excel(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]: return RedirectResponse(url="/login", status_code=302)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte Pagos"
    headers = ["Cedula","Nombre completo","Universidad","Carrera","Semestre (numero) Alumno","Actual Semestre Alumno","Ruta PDF/Imagen","Semestre (archivo adjunto)","Numero de comprobantes (serie)","Fecha Carga","Cuota","Monto"]
    ws.append(headers)
    registros = db.query(models.RegistroPagos).all()
    for reg in registros:
        alumno = db.query(models.Alumno).filter(models.Alumno.id==reg.alumno_id).first()
        if not alumno: continue
        nombre = f"{alumno.apellidos} {alumno.nombres}"
        uni = alumno.universidad.nombre if alumno.universidad else ""
        car = alumno.carrera.nombre if alumno.carrera else ""
        for det in reg.detalles:
            ruta = reg.archivo_path or ""
            ruta_excel = ""
            if ruta:
                try:
                    fname = ruta.split("/")[-1]
                    tipo = ruta.split("/")[-2] if "/" in ruta else "pagos"
                    if tipo not in ["notas","pagos"]: tipo="pagos"
                    ruta_excel = f"/ver-pdf/{tipo}/{fname}"
                except: ruta_excel = ruta
            ws.append([alumno.cedula, nombre, uni, car, alumno.semestre, alumno.actual_semestre, ruta_excel, reg.semestre, reg.numero_comprobantes or "", reg.created_at.strftime("%Y-%m-%d") if reg.created_at else "", det.cuota, det.monto])
    output = io.BytesIO()
    wb.save(output); output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=Reporte_Pagos.xlsx"})


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


@router.post("/supervisor/alumnos/crear")
def crear_alumno_completo(request: Request, username: str = Form(...), password: str = Form(...), apellidos: str = Form(...), nombres: str = Form(...), cedula: str = Form(...), celular: str = Form(...), universidad_id: int = Form(...), carrera_id: int = Form(...), centro_id: int = Form(...), actual_semestre: str = Form(...), semestre: int = Form(...), inicia_beca: str = Form(None), beca: str = Form(...), tipo_beca: str = Form(...), alimentacion: str = Form(...), arriendo: str = Form(...), matricula: str = Form(...), genero: str = Form(...), estado: str = Form(...), pais: str = Form(...), observacion: str = Form(None), db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]: return RedirectResponse(url="/login", status_code=302)
    # Validar universidad y carrera existen - FIX autocomplete
    uni_exists = db.query(models.Universidad).filter(models.Universidad.id==universidad_id).first()
    car_exists = db.query(models.Carrera).filter(models.Carrera.id==carrera_id).first()
    centro_exists = db.query(models.Centro).filter(models.Centro.id==centro_id).first()
    if not uni_exists or not car_exists or not centro_exists:
        return RedirectResponse(url="/supervisor/mis-alumnos?error=invalid_ref", status_code=302)

    username_clean = username.strip()
    if not username_clean:
        return RedirectResponse(url="/supervisor/mis-alumnos?error=username_empty", status_code=302)

    # FIX: Todos los usernames deben ser únicos - si ya existe, error
    existing_user = db.query(models.User).filter(models.User.username==username_clean).first()
    if existing_user:
        # Si ya existe, no permitir duplicado - mostrar alerta
        return RedirectResponse(url=f"/supervisor/mis-alumnos?error=username_exists&username={username_clean}", status_code=302)
    else:
        u = models.User(username=username_clean, password_hash=auth.hash_password(password), nombre=nombres, apellidos=apellidos, rol="alumno")
        db.add(u); db.commit(); db.refresh(u)
    fecha_beca = None
    if inicia_beca:
        try: fecha_beca = datetime.strptime(inicia_beca, "%Y-%m-%d").date()
        except: fecha_beca = None
    alumno = models.Alumno(user_id=u.id, creado_por_id=user.id, apellidos=apellidos, nombres=nombres, cedula=cedula, celular=celular, universidad_id=universidad_id, carrera_id=carrera_id, centro_id=centro_id, actual_semestre=actual_semestre, semestre=semestre, inicia_beca=fecha_beca, beca=beca, tipo_beca=tipo_beca, alimentacion=alimentacion, arriendo=arriendo, matricula=matricula, genero=genero, estado=estado, pais=pais, observacion=observacion)
    db.add(alumno); db.commit()
    return RedirectResponse(url="/supervisor/mis-alumnos", status_code=302)

    existing_user = db.query(models.User).filter(models.User.username==username).first()
    if existing_user:
        if existing_user.rol == "alumno": u = existing_user
        else: return RedirectResponse(url="/supervisor/mis-alumnos", status_code=302)
    else:
        u = models.User(username=username, password_hash=auth.hash_password(password), nombre=nombres, apellidos=apellidos, rol="alumno")
        db.add(u); db.commit(); db.refresh(u)
    fecha_beca = None
    if inicia_beca:
        try: fecha_beca = datetime.strptime(inicia_beca, "%Y-%m-%d").date()
        except: fecha_beca = None
    alumno = models.Alumno(user_id=u.id, creado_por_id=user.id, apellidos=apellidos, nombres=nombres, cedula=cedula, celular=celular, universidad_id=universidad_id, carrera_id=carrera_id, centro_id=centro_id, actual_semestre=actual_semestre, semestre=semestre, inicia_beca=fecha_beca, beca=beca, tipo_beca=tipo_beca, alimentacion=alimentacion, arriendo=arriendo, matricula=matricula, genero=genero, estado=estado, pais=pais, observacion=observacion)
    db.add(alumno); db.commit()
    return RedirectResponse(url="/supervisor/mis-alumnos", status_code=302)

@router.post("/supervisor/alumnos/{aid}/editar")
def editar_alumno(aid: int, request: Request, universidad_id: int = Form(...), carrera_id: int = Form(...), centro_id: int = Form(...), actual_semestre: str = Form(...), semestre: int = Form(...), beca: str = Form(...), tipo_beca: str = Form(...), alimentacion: str = Form(...), arriendo: str = Form(...), matricula: str = Form(...), estado: str = Form(...), observacion: str = Form(None), new_password: str = Form(None), db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]: return RedirectResponse(url="/login", status_code=302)
    alumno = db.query(models.Alumno).filter(models.Alumno.id==aid).first()
    if not alumno: return RedirectResponse(url="/supervisor/carreras", status_code=302)
    alumno.universidad_id=universidad_id; alumno.carrera_id=carrera_id; alumno.centro_id=centro_id
    alumno.actual_semestre=actual_semestre; alumno.semestre=semestre; alumno.beca=beca; alumno.tipo_beca=tipo_beca; alumno.alimentacion=alimentacion; alumno.arriendo=arriendo; alumno.matricula=matricula; alumno.estado=estado; alumno.observacion=observacion
    if new_password and new_password.strip()!="":
        u = db.query(models.User).filter(models.User.id==alumno.user_id).first()
        if u: u.password_hash=auth.hash_password(new_password.strip())
    db.commit()
    return RedirectResponse(url="/supervisor/carreras", status_code=302)

@router.post("/supervisor/persona/{uid}/editar")
def editar_persona(uid: int, request: Request, apellidos: str = Form(...), nombres: str = Form(...), cedula: str = Form(...), celular: str = Form(...), genero: str = Form(...), pais: str = Form(...), new_password: str = Form(None), db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]: return RedirectResponse(url="/login", status_code=302)
    u = db.query(models.User).filter(models.User.id==uid).first()
    if not u or u.rol!="alumno": return RedirectResponse(url="/supervisor/mis-alumnos", status_code=302)
    # Username NO se puede actualizar - se deja intacto
    u.nombre=nombres; u.apellidos=apellidos
    if new_password and new_password.strip()!="": u.password_hash=auth.hash_password(new_password.strip())
    alumnos = db.query(models.Alumno).filter(models.Alumno.user_id==uid).all()
    for a in alumnos: a.apellidos=apellidos; a.nombres=nombres; a.cedula=cedula; a.celular=celular; a.genero=genero; a.pais=pais
    db.commit()
    return RedirectResponse(url="/supervisor/mis-alumnos", status_code=302)
    u.username=username; u.nombre=nombres; u.apellidos=apellidos
    if new_password and new_password.strip()!="": u.password_hash=auth.hash_password(new_password.strip())
    alumnos = db.query(models.Alumno).filter(models.Alumno.user_id==uid).all()
    for a in alumnos: a.apellidos=apellidos; a.nombres=nombres; a.cedula=cedula; a.celular=celular; a.genero=genero; a.pais=pais
    db.commit()
    return RedirectResponse(url="/supervisor/mis-alumnos", status_code=302)

@router.get("/supervisor/alumnos/{aid}/eliminar")
def eliminar_alumno(aid: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]: return RedirectResponse(url="/login", status_code=302)
    alumno = db.query(models.Alumno).filter(models.Alumno.id==aid).first()
    if not alumno: return RedirectResponse(url="/supervisor/carreras", status_code=302)
    db.delete(alumno); db.commit()
    return RedirectResponse(url="/supervisor/carreras", status_code=302)

@router.get("/supervisor/persona/{uid}/eliminar")
def eliminar_persona(uid: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.rol not in ["admin","supervisor"]: return RedirectResponse(url="/login", status_code=302)
    u = db.query(models.User).filter(models.User.id==uid).first()
    if not u or u.rol!="alumno": return RedirectResponse(url="/supervisor/mis-alumnos", status_code=302)
    alumnos = db.query(models.Alumno).filter(models.Alumno.user_id==uid).all()
    for a in alumnos: db.delete(a)
    db.delete(u); db.commit()
    return RedirectResponse(url="/supervisor/mis-alumnos", status_code=302)
