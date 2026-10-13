from datetime import date, timedelta
from io import BytesIO
import os
from fastapi import Body, FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from modmoimodelo import ModMoiModel
from abmmodelo import abmmodmoimodelo
import sectoresmodelo as modelo_sectores
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
import tipohorariosmodelo as modelo_tipohorarios
from dtprogramadamodelo import ModeloDTProgramadaWeb
from Hchocomodelo import ModeloHChocoWeb
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from fastapi import Query
from principalmodelo import modeloprincipal 
from typing import Optional
from hchocofindemodelo import ModeloHChocoFindeWeb
from hgolomodelo import ModeloHGoloWeb
from hgolofindemodelo import ModeloHGoloFindeWeb


modelo_hchoco = ModeloHChocoWeb()
modelo_dtprog = ModeloDTProgramadaWeb()
app = FastAPI(title="ARMADO DE HORARIOS")

# Instanciamos los modelos
modmoi_modelo = ModMoiModel()
abm_modelo = abmmodmoimodelo()

# ✅ AHORA (usa una ruta absoluta segura basada en la ubicación del script)
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "."))

# Montar imágenes de la carpeta static
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Montar raíz para servir archivos estáticos (CSS, JS)
app.mount("/archivos", StaticFiles(directory="."), name="archivos")


# ==========================================
# 1. VISTAS HTML PRINCIPALES (GENERAL)
# ==========================================

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    # ✅ Indentación corregida correctamente
    return templates.TemplateResponse(request, "principal.html", {})

@app.get("/modmoi", response_class=HTMLResponse)
def vista_modmoi(request: Request):
    return templates.TemplateResponse("modmoi.html", {"request": request})


@app.get("/sectores", response_class=HTMLResponse)
def vista_sectores(request: Request):
    return templates.TemplateResponse("sectores.html", {"request": request})


@app.get("/tiposhorarios", response_class=HTMLResponse)
def vista_tipos_horario(request: Request):
    return templates.TemplateResponse("tipohorarios.html", {"request": request})

@app.get("/hchoco", response_class=HTMLResponse)
def vista_hchoco(request: Request):
    return templates.TemplateResponse("hchoco.html", {"request": request})

@app.get("/dtprogramada", response_class=HTMLResponse)
def vista_dotacion_programada(request: Request):
    return templates.TemplateResponse("dtprogramada.html", {"request": request})

@app.get("/hchocofinde", response_class=HTMLResponse)
def vista_hchocofinde(request: Request):
    return templates.TemplateResponse("hchocofinde.html", {"request": request})

@app.get("/hgolo", response_class=HTMLResponse)
def vista_hgolo(request: Request):
    return templates.TemplateResponse("hgolo.html", {"request": request})

@app.get("/hgolofinde", response_class=HTMLResponse)
def vista_hgolo_finde(request: Request):
    return templates.TemplateResponse("hgolofinde.html", {"request": request})


# ==========================================
# 2. MÓDULO: MANO DE OBRA (MOD/MOI)
# ==========================================

@app.get("/api/modmoi/datos")
def api_obtener_modmoi(
    vista: str = "Semana", columna: str = None, filtro: str = None
):
    es_finde = vista == "Fin de Semana"

    if es_finde:
        columnas, datos = modmoi_modelo.obtener_datos_finde(columna, filtro)
    else:
        columnas, datos = modmoi_modelo.obtener_datos(columna, filtro)

    mod_count, moi_count = modmoi_modelo.contar_mano_de_obra(es_finde=es_finde)

    return {
        "columnas": columnas,
        "datos": datos,
        "mod": mod_count,
        "moi": moi_count,
    }


@app.get("/api/modmoi/exportar-excel")
def api_exportar_excel(vista: str = "Semana"):
    es_finde = vista == "Fin de Semana"

    fecha_proxima = date.today() + timedelta(days=7)
    semana_actual = modmoi_modelo.obtener_numero_semana_personalizado(fecha_proxima)

    if es_finde:
        columnas, datos = modmoi_modelo.obtener_datos_finde()
        nombre_hoja = "Horarios Finde"
        nombre_archivo = f"Consolidado Finde semana {semana_actual}.xlsx"
    else:
        columnas, datos = modmoi_modelo.obtener_datos()
        nombre_hoja = "Horarios Semana"
        nombre_archivo = f"Consolidado Semana {semana_actual}.xlsx"

    if not datos:
        return {"error": "No hay datos registrados para exportar."}

    wb = Workbook()
    ws = wb.active
    ws.title = nombre_hoja

    encabezado_font = Font(bold=True, color="FFFFFF")
    encabezado_fill = PatternFill("solid", fgColor="4F81BD")
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    for i, col in enumerate(columnas, start=1):
        celda = ws.cell(row=1, column=i, value=col)
        celda.font = encabezado_font
        celda.fill = encabezado_fill
        celda.border = thin_border
        celda.alignment = Alignment(horizontal="center", vertical="center")

    for fila_idx, fila in enumerate(datos, start=2):
        for col_idx, valor in enumerate(fila, start=1):
            celda = ws.cell(row=fila_idx, column=col_idx, value=valor)
            celda.border = thin_border
            celda.alignment = Alignment(vertical="center", wrap_text=True)

    for col_idx, col in enumerate(columnas, start=1):
        max_length = len(str(col))
        for fila in datos:
            val_celda = fila[col_idx - 1]
            texto_val = str(val_celda) if val_celda is not None else ""
            if len(texto_val) > max_length:
                max_length = len(texto_val)

        letra_col = get_column_letter(col_idx)
        ws.column_dimensions[letra_col].width = max(15, min(max_length + 2, 50))

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    headers = {"Content-Disposition": f'attachment; filename="{nombre_archivo}"'}

    return StreamingResponse(
        output,
        headers=headers,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/api/modmoi/obtener/{id_registro}")
def api_obtener_registro(id_registro: int):
    data = abm_modelo.obtener_por_id(id_registro)
    if not data:
        return {"error": "Registro no encontrado"}
    return data


@app.post("/api/modmoi/guardar")
def api_guardar_registro(payload: dict = Body(...)):
    modo = payload.get("modo")
    id_registro = payload.get("id")
    datos = payload.get("datos", {})

    if not datos.get("calificacion_mano_obra"):
        return {"status": "error", "message": "Seleccione Calificación de Mano de Obra"}
    if not datos.get("operario"):
        return {"status": "error", "message": "El nombre de operario es requerido"}
    if not datos.get("horario"):
        return {"status": "error", "message": "El horario es requerido"}

    try:
        if modo == "insertar":
            abm_modelo.insertar(datos)
        elif modo == "modificar":
            abm_modelo.modificar(id_registro, datos)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.delete("/api/modmoi/eliminar/{id_registro}")
def api_eliminar_registro(id_registro: int):
    try:
        abm_modelo.eliminar(id_registro)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ==========================================
# 3. MÓDULO: SECTORES
# ==========================================

@app.get("/api/sectores/datos")
def api_obtener_sectores():
    filas = modelo_sectores.obtener_sectores()
    tipos_horario = modelo_sectores.obtener_tipos_horario()
    columnas = ["ID", "Sector", "Planta", "Tipo de Horario", "Requiere Dotación"]
    return {
        "columnas": columnas,
        "datos": filas,
        "tipos_horario": tipos_horario
    }


@app.get("/api/sectores/obtener/{id_sector}")
def api_obtener_sector(id_sector: int):
    data = modelo_sectores.obtener_sector_por_id(id_sector)
    if not data:
        return {"error": "Sector no encontrado"}
    return data


@app.post("/api/sectores/guardar")
def api_guardar_sector(payload: dict = Body(...)):
    modo = payload.get("modo")
    id_sector = payload.get("id")
    datos = payload.get("datos", {})

    try:
        if modo == "insertar":
            modelo_sectores.insertar_sector(datos)
        else:
            modelo_sectores.modificar_sector(id_sector, datos)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.delete("/api/sectores/eliminar/{id_sector}")
def api_eliminar_sector(id_sector: int):
    try:
        modelo_sectores.eliminar_sector(id_sector)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ==========================================
# 4. MÓDULO: TIPOS DE HORARIO
# ==========================================

@app.get("/api/tipohorarios/datos")
def api_obtener_tipos_horarios():
    filas = modelo_tipohorarios.obtener_tipos_horarios()
    columnas = ["ID", "Tipo", "Horarios / Turnos"]
    return {
        "columnas": columnas,
        "datos": filas
    }


@app.get("/api/tipohorarios/obtener/{tipo_id}")
def api_obtener_tipo_horario(tipo_id: int):
    data = modelo_tipohorarios.obtener_tipo_horario_por_id(tipo_id)
    if not data:
        return {"error": "Tipo de horario no encontrado"}
    return data


@app.post("/api/tipohorarios/guardar")
def api_guardar_tipo_horario(payload: dict = Body(...)):
    modo = payload.get("modo")
    tipo_id = payload.get("id")
    datos = payload.get("datos", {})

    if not datos.get("tipo") or not datos.get("horarios_definidos"):
        return {"status": "error", "message": "Complete el tipo y al menos un horario."}

    try:
        if modo == "insertar":
            modelo_tipohorarios.insertar_tipo_horario(datos)
        else:
            modelo_tipohorarios.modificar_tipo_horario(tipo_id, datos)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.delete("/api/tipohorarios/eliminar/{tipo_id}")
def api_eliminar_tipo_horario(tipo_id: int):
    try:
        modelo_tipohorarios.eliminar_tipo_horario(tipo_id)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ==========================================
# 5. MÓDULO: DOTACIÓN PROGRAMADA
# ==========================================

@app.get("/api/dtprogramada/datos")
def api_obtener_dtprogramada(semana: str = None):
    if not semana:
        semana = str(modelo_dtprog.obtener_numero_semana_personalizado(date.today() + timedelta(days=7)))
    
    sectores_choco = modelo_dtprog.obtener_sectores_rotativos_por_planta("Chocolate")
    sectores_golo = modelo_dtprog.obtener_sectores_rotativos_por_planta("Golosinas")
    turnos = modelo_dtprog.obtener_turnos_por_tipo("ROTATIVO")
    dotaciones = modelo_dtprog.obtener_dotaciones_semana(semana)

    return {
        "semana": semana,
        "turnos": turnos,
        "sectores_chocolate": sectores_choco,
        "sectores_golosinas": sectores_golo,
        "dotaciones": dotaciones
    }


@app.post("/api/dtprogramada/guardar")
def api_guardar_dtprogramada(payload: dict = Body(...)):
    semana = payload.get("semana")
    datos = payload.get("datos", {})
    if not semana:
        return {"status": "error", "message": "Semana no especificada"}
    
    exito, mensaje = modelo_dtprog.guardar_dotaciones(semana, datos)
    if exito:
        return {"status": "ok"}
    else:
        return {"status": "error", "message": mensaje}


# ==========================================
# 6. MÓDULO: CHOCOLATES (SEMANAL Y FINDE)
# ==========================================

@app.get("/api/hchoco/datos")
def api_obtener_hchoco(semana: Optional[str] = None):
    modelo = ModeloHChocoWeb()
    modelo_base = modeloprincipal()
    try:
        if not semana or semana.lower() == "none" or semana.strip() == "":
            fecha_proxima = date.today() + timedelta(days=7)
            semana = str(modelo_base.obtener_numero_semana_personalizado(fecha_proxima))

        sectores = modelo.obtener_sectores_chocolates()
        dotacion_teorica = modelo.obtener_dotacion_teorica(semana)
        datos_guardados = modelo.obtener_datos_semana(semana)
        operarios_disponibles = modelo.obtener_operarios_disponibles(semana)
        todos_operarios = modelo.obtener_operarios()

        sectores_info = []
        for sec, tipo, req in sectores:
            t_horario = str(tipo).strip().upper() if tipo else "ROTATIVO"
            turnos = modelo.obtener_turnos_por_tipo(t_horario)
            if not turnos:
                turnos = ["08:00 a 16:00"] if t_horario == "CENTRAL" else ["06:00 a 14:00", "14:00 a 22:00", "22:00 a 06:00"]
            sectores_info.append({
                "sector": sec,
                "tipo_horario": t_horario,
                "requiere_dotacion": req,
                "turnos": turnos
            })

        return {
            "semana": semana,
            "sectores": sectores_info,
            "dotacion_teorica": dotacion_teorica,
            "asignados": datos_guardados,
            "operarios": todos_operarios,
            "operarios_disponibles": operarios_disponibles
        }
    except Exception as e:
        print(f"Error en endpoint /api/hchoco/datos: {e}")
        return {"error": str(e)}
    finally:
        modelo.cerrar_conexion()
        modelo_base.cerrar_conexion()
    

@app.post("/api/hchoco/guardar")
def api_guardar_hchoco(payload: dict = Body(...)):
    semana = payload.get("semana")
    registros = payload.get("registros", [])
    modelo_hchoco.guardar_datos_semana(semana, registros)
    return {"status": "ok"}


@app.get("/api/hchoco/finde/datos")
def api_obtener_hchoco_finde(semana: str = "42"):
    modelo = ModeloHChocoFindeWeb()
    modelo_main = ModeloHChocoWeb()
    try:
        datos = modelo.obtener_datos_semana_finde(semana)
        operarios_disponibles = modelo.obtener_operarios_disponibles(semana)
        sectores = modelo_main.obtener_sectores_chocolates()
        
        modelo.cerrar_conexion()
        modelo_main.cerrar_conexion()
        
        return {
            "semana": semana,
            "asignados_finde": datos,
            "operarios_disponibles": operarios_disponibles,
            "sectores": sectores
        }
    except Exception as e:
        print(f"Error en /api/hchoco/finde/datos: {e}")
        return {"error": str(e)}


@app.post("/api/hchoco/finde/guardar")
def api_guardar_hchoco_finde(payload: dict = Body(...)):
    semana = payload.get("semana")
    registros = payload.get("registros", [])
    
    modelo = ModeloHChocoFindeWeb()
    try:
        modelo.guardar_datos_finde(semana, registros)
        modelo.cerrar_conexion()
        return {"status": "ok"}
    except Exception as e:
        modelo.cerrar_conexion()
        import traceback
        traceback.print_exc()
        print(f"Error detallado en /api/hchoco/finde/guardar: {e}")
        return {"status": "error", "mensaje": str(e)}


@app.get("/api/hchoco/exportar-pdf")
def api_exportar_pdf_hchoco(semana: str = "42"):
    modelo_main = ModeloHChocoWeb()
    modelo_finde = ModeloHChocoFindeWeb()
    
    try:
        output = BytesIO()
        doc = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30,
        )
        elements = []
        styles = getSampleStyleSheet()

        elements.append(
            Paragraph(
                f"<b>Semana {semana} - PLANTA CHOCOLATES (SEMANAL)</b>",
                styles["Title"],
            )
        )
        elements.append(Spacer(1, 12))

        datos_guardados = modelo_main.obtener_datos_semana(semana)
        sectores_operarios = {}

        for id_val, operario, horario, sector in datos_guardados:
            if sector and horario and operario:
                if sector not in sectores_operarios:
                    sectores_operarios[sector] = {}
                if horario not in sectores_operarios[sector]:
                    sectores_operarios[sector][horario] = []
                sectores_operarios[sector][horario].append(operario)

        for sector, turnos in sectores_operarios.items():
            if all(len(lst) == 0 for lst in turnos.values()):
                continue

            elements.append(Paragraph(f"<b>{sector}</b>", styles["Heading2"]))
            elements.append(Spacer(1, 6))

            columnas = list(turnos.keys())
            data = [columnas]
            max_filas = max(len(turnos[t]) for t in columnas) if columnas else 0

            for i in range(max_filas):
                fila = [
                    turnos[t][i] if i < len(turnos[t]) else "" for t in columnas
                ]
                data.append(fila)

            ancho_col = 535 / len(columnas) if columnas else 180
            table = Table(data, colWidths=[ancho_col] * len(columnas))
            table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ])
            )

            elements.append(table)
            elements.append(Spacer(1, 12))

        registros_finde = modelo_finde.obtener_datos_semana_finde(semana)
        if registros_finde:
            elements.append(PageBreak())
            elements.append(
                Paragraph(
                    f"<b>Semana {semana} - FIN DE SEMANA (CHOCOLATES)</b>",
                    styles["Title"],
                )
            )
            elements.append(Spacer(1, 12))

            data_finde = [["OPERARIO", "DÍA", "HORARIO", "SECTOR"]]
            for reg in registros_finde:
                if len(reg) == 5:
                    _, op, dia, hor, sec = reg
                elif len(reg) == 4:
                    op, dia, hor, sec = reg[1], "Fin de Semana", reg[2], reg[3]
                else:
                    continue

                if op:
                    data_finde.append([
                        str(op).strip(),
                        str(dia).strip(),
                        str(hor).strip(),
                        str(sec).strip(),
                    ])

            if len(data_finde) > 1:
                table_finde = Table(data_finde, colWidths=[180, 95, 110, 150])
                table_finde.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAD3")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("ALIGN", (0, 0), (0, -1), "LEFT"),
                        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ])
                )
                elements.append(table_finde)

        doc.build(elements)
        output.seek(0)

        nombre_archivo = f"Horarios chocolates semana {semana}.pdf"
        headers = {"Content-Disposition": f'attachment; filename="{nombre_archivo}"'}
        return StreamingResponse(output, headers=headers, media_type="application/pdf")

    finally:
        modelo_main.cerrar_conexion()
        modelo_finde.cerrar_conexion()


# ==========================================
# 7. MÓDULO: GOLOSINAS (SEMANAL Y FINDE)
# ==========================================

@app.get("/api/hgolo/datos")
def api_obtener_hgolo(semana: Optional[str] = None):
    modelo = ModeloHGoloWeb()
    modelo_base = modeloprincipal()
    try:
        if not semana or semana.lower() == "none" or semana.strip() == "":
            fecha_proxima = date.today() + timedelta(days=7)
            semana = str(modelo_base.obtener_numero_semana_personalizado(fecha_proxima))

        sectores = modelo.obtener_sectores_golosinas()
        dotacion_teorica = modelo.obtener_dotacion_teorica(semana)
        datos_guardados = modelo.obtener_datos_semana(semana)
        operarios_disponibles = modelo.obtener_operarios_disponibles(semana)
        todos_operarios = modelo.obtener_operarios()

        sectores_info = []
        for sec, tipo, req in sectores:
            t_horario = str(tipo).strip().upper() if tipo else "ROTATIVO"
            turnos = modelo.obtener_turnos_por_tipo(t_horario)
            if not turnos:
                turnos = ["08:00 a 16:00"] if t_horario == "CENTRAL" else ["06:00 a 14:00", "14:00 a 22:00", "22:00 a 06:00"]
            sectores_info.append({
                "sector": sec,
                "tipo_horario": t_horario,
                "requiere_dotacion": req,
                "turnos": turnos
            })

        return {
            "semana": semana,
            "sectores": sectores_info,
            "dotacion_teorica": dotacion_teorica,
            "asignados": datos_guardados,
            "operarios": todos_operarios,
            "operarios_disponibles": operarios_disponibles
        }
    except Exception as e:
        print(f"Error en endpoint /api/hgolo/datos: {e}")
        return {"error": str(e)}
    finally:
        modelo.cerrar_conexion()
        if hasattr(modelo_base, 'cerrar_conexion'):
            modelo_base.cerrar_conexion()


@app.post("/api/hgolo/guardar")
def api_guardar_hgolo(payload: dict = Body(...)):
    semana = payload.get("semana")
    registros = payload.get("registros", [])
    modelo = ModeloHGoloWeb()
    try:
        registros_tuplas = [(r[0], r[1], r[2], r[3]) for r in registros]
        modelo.guardar_datos_semana(semana, registros_tuplas)
        return {"status": "ok"}
    except Exception as e:
        print(f"Error en /api/hgolo/guardar: {e}")
        return {"status": "error", "mensaje": str(e)}
    finally:
        modelo.cerrar_conexion()


@app.get("/api/hgolo/finde/datos")
def api_hgolo_finde_datos(semana: str = ""):
    modelo = ModeloHGoloFindeWeb()
    try:
        operarios = modelo.obtener_operarios_disponibles(semana)
        sectores = modelo.obtener_sectores()
        asignados = modelo.obtener_datos_semana_finde(semana)
        return {
            "semana": semana,
            "operarios_disponibles": operarios,
            "sectores": sectores,
            "asignados_finde": asignados
        }
    finally:
        modelo.cerrar_conexion()


@app.post("/api/hgolo/finde/guardar")
async def api_hgolo_finde_guardar(request: Request):
    data = await request.json()
    semana = data.get("semana")
    registros = data.get("registros")
    
    modelo = ModeloHGoloFindeWeb()
    try:
        modelo.guardar_datos_finde(semana, registros)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        modelo.cerrar_conexion()


@app.get("/api/hgolo/exportar-pdf")
def api_exportar_pdf_hgolo(semana: str = "42"):
    modelo_main = ModeloHGoloWeb()
    modelo_finde = ModeloHGoloFindeWeb()
    
    try:
        output = BytesIO()
        doc = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30,
        )
        elements = []
        styles = getSampleStyleSheet()

        elements.append(
            Paragraph(
                f"<b>Semana {semana} - PLANTA GOLOSINAS (SEMANAL)</b>",
                styles["Title"],
            )
        )
        elements.append(Spacer(1, 12))

        datos_guardados = modelo_main.obtener_datos_semana(semana)
        sectores_operarios = {}

        for id_val, operario, horario, sector in datos_guardados:
            if sector and horario and operario:
                if sector not in sectores_operarios:
                    sectores_operarios[sector] = {}
                if horario not in sectores_operarios[sector]:
                    sectores_operarios[sector][horario] = []
                sectores_operarios[sector][horario].append(operario)

        for sector, turnos in sectores_operarios.items():
            if all(len(lst) == 0 for lst in turnos.values()):
                continue

            elements.append(Paragraph(f"<b>{sector}</b>", styles["Heading2"]))
            elements.append(Spacer(1, 6))

            columnas = list(turnos.keys())
            data = [columnas]
            max_filas = max(len(turnos[t]) for t in columnas) if columnas else 0

            for i in range(max_filas):
                fila = [
                    turnos[t][i] if i < len(turnos[t]) else "" for t in columnas
                ]
                data.append(fila)

            ancho_col = 535 / len(columnas) if columnas else 180
            table = Table(data, colWidths=[ancho_col] * len(columnas))
            table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ])
            )

            elements.append(table)
            elements.append(Spacer(1, 12))

        registros_finde = modelo_finde.obtener_datos_semana_finde(semana)
        if registros_finde:
            elements.append(PageBreak())
            elements.append(
                Paragraph(
                    f"<b>Semana {semana} - FIN DE SEMANA (GOLOSINAS)</b>",
                    styles["Title"],
                )
            )
            elements.append(Spacer(1, 12))

            data_finde = [["OPERARIO", "DÍA", "HORARIO", "SECTOR"]]
            for reg in registros_finde:
                if len(reg) == 5:
                    _, op, dia, hor, sec = reg
                elif len(reg) == 4:
                    op, dia, hor, sec = reg[1], "Fin de Semana", reg[2], reg[3]
                else:
                    continue

                if op:
                    data_finde.append([
                        str(op).strip(),
                        str(dia).strip(),
                        str(hor).strip(),
                        str(sec).strip(),
                    ])

            if len(data_finde) > 1:
                table_finde = Table(data_finde, colWidths=[180, 95, 110, 150])
                table_finde.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAD3")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("ALIGN", (0, 0), (0, -1), "LEFT"),
                        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ])
                )
                elements.append(table_finde)

        doc.build(elements)
        output.seek(0)

        nombre_archivo = f"Horarios golosinas semana {semana}.pdf"
        headers = {"Content-Disposition": f'attachment; filename="{nombre_archivo}"'}
        return StreamingResponse(output, headers=headers, media_type="application/pdf")

    finally:
        modelo_main.cerrar_conexion()
        modelo_finde.cerrar_conexion()
