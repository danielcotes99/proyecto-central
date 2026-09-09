import qrcode
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime
import os
import platform
import subprocess
import tempfile
# ─────────────────────────────────────────────
#  FUNCIONES DE SÍMBOLOS ISO (ReportLab)
# ─────────────────────────────────────────────

def dibujar_lot(c, x, y, size):
    """Símbolo LOT: rectángulo con texto LOT adentro"""
    c.setLineWidth(0.4)
    c.rect(x, y, size, size)
    c.setFont("Helvetica-Bold", size * 0.45)
    c.drawCentredString(x + size / 2, y + size * 0.28, "LOT")


def dibujar_exp(c, x, y, size):
    """Símbolo EXP: reloj de arena invertido ISO 15223-1"""
    c.setLineWidth(0.4)

    # Tapa superior e inferior
    c.line(x,        y + size, x + size, y + size)
    c.line(x,        y,        x + size, y)

    # Diagonales (forma de reloj de arena)
    c.line(x,        y + size, x + size, y)
    c.line(x + size, y + size, x,        y)

    # Triángulo VACÍO arriba (sin relleno)
    p = c.beginPath()
    p.moveTo(x + size * 0.15, y + size * 0.85)
    p.lineTo(x + size * 0.85, y + size * 0.85)
    p.lineTo(x + size * 0.50, y + size * 0.52)
    p.close()
    c.drawPath(p, fill=0, stroke=0)  # fill=0 → vacío

    # Triángulo RELLENO abajo (arena acumulada)
    p = c.beginPath()
    p.moveTo(x + size * 0.15, y + size * 0.15)
    p.lineTo(x + size * 0.85, y + size * 0.15)
    p.lineTo(x + size * 0.50, y + size * 0.48)
    p.close()
    c.drawPath(p, fill=1, stroke=0)  # fill=1 → relleno


def dibujar_mfd(c, x, y, size):
    """Símbolo MFD: fábrica simplificada ISO 15223-1"""
    c.setLineWidth(0.4)

    # Cuerpo del edificio
    c.rect(x, y, size, size * 0.5)

    # Techo (triángulo)
    p = c.beginPath()
    p.moveTo(x,            y + size * 0.5)
    p.lineTo(x + size / 2, y + size * 0.85)
    p.lineTo(x + size,     y + size * 0.5)
    p.close()
    c.drawPath(p, fill=0, stroke=1)

    # Chimeneas (3 rectángulos pequeños en el techo)
    ch_w = size * 0.08
    ch_h = size * 0.18
    ch_y = y + size * 0.82
    for cx in [x + size*0.25, x + size*0.48, x + size*0.68]:
        c.rect(cx, ch_y, ch_w, ch_h, fill=1)

    # Puerta
    door_w = size * 0.22
    door_h = size * 0.28
    c.rect(x + (size - door_w) / 2, y, door_w, door_h)


def generar_qr(datos):
    """
    Genera imagen QR con formato GS1-128
    Formato: ÌÊ010000000000283810400A1EQ-02-03-26-1Ê17260305|Î
    
    Ì = Carácter de inicio FNC1
    Ê = Separador GS (Group Separator)
    01 = AI para GTIN (código de producto)
    10 = AI para Lote
    17 = AI para Fecha de vencimiento (YYMMDD)
    Î = Carácter de fin
    """
    # Extraer datos
    codigo = str(datos.get("codigo", "0"))
    lote = datos.get("lote", "")
    fecha = datos.get("vencimiento", "")
    
    # GTIN: rellenar código con ceros a la izquierda (14 dígitos)
    gtin = codigo.zfill(14)
    
    # Convertir fecha a YYMMDD para vencimiento (+1 año)
    
        
    fecha_venc = fecha.strftime("%y%m%d")
    
    # Construir código GS1-128
    # Formato: ÌÊ01{GTIN}10{LOTE}Ê17{VENC}|Î
    qr_text = f"01{gtin}17{fecha_venc}10{lote}"
    
    # Generar QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_text)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir a bytes
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return img_buffer

def generar_etiqueta_pdf(datos, copias=1):

    buffer = BytesIO()

    ancho_mm = 63.33
    alto_mm = 37.93

    ancho = ancho_mm * mm
    alto = alto_mm * mm

    scale = ancho_mm / 72

    def s(x):
        return x * scale

    c = canvas.Canvas(buffer, pagesize=(ancho, alto))

    tipo = datos.get("tipo", "")
    num_copias = copias if tipo == "INSUMO" else copias

    for _ in range(num_copias):
        sym_size = s(2.8) * mm
        gap = s(1) * mm  # espacio entre símbolo y texto
        margen = s(1.5) * mm
        qr_size = s(14) * mm  # QR un poco más grande

        # ---------------------------
        # BORDE EXTERIOR
        # ---------------------------
        c.setLineWidth(0.6)
        c.rect(0.5*mm, 0.5*mm, ancho-1*mm, alto-1*mm)

        # ---------------------------
        # AREA QR
        # ---------------------------
        qr_area_width = qr_size + s(4)*mm
        qr_area_height = qr_size + s(11)*mm  # MAS ALTURA

        c.rect(margen/2, alto - qr_area_height - margen/2,
               qr_area_width, qr_area_height)

        qr_img = generar_qr(datos)

        c.drawImage(
            ImageReader(qr_img),
            margen,
            alto - margen - qr_size - s(2.5)*mm,
            width=qr_size,
            height=qr_size
        )

        # texto codigo
        c.setFont("Helvetica", s(5.8))
        c.drawString(margen,
                     alto - margen - qr_size - s(3.5)*mm,
                     "Código de cobro:")

        c.setFont("Helvetica-Bold", s(7))
        c.drawString(margen,
                     alto - margen - qr_size - s(6)*mm,
                     str(datos.get('codigo', '')))

        # ---------------------------
        # AREA INFORMACION
        # ---------------------------
        x_info = margen + qr_size + s(6)*mm
        info_width = ancho - x_info - margen/2
        info_height = qr_area_height

        c.rect(x_info - s(1)*mm,
               alto - info_height - margen/2,
               info_width,
               info_height)

        y_titulo = alto - margen - s(4.5)*mm

        styles = getSampleStyleSheet()
        style = styles["Normal"]
        style.fontName = "Helvetica-Bold"
        style.fontSize = s(7)
        style.leading = s(7.5)  # espacio entre líneas

        detalle = datos.get('detalle', '')

        p = Paragraph(detalle, style)

        # ancho disponible
        text_width = info_width - s(1)*mm

        # calcular tamaño del párrafo
        w, h = p.wrap(text_width, 50)

        # dibujar (ajustando hacia abajo)
        p.drawOn(c, x_info, y_titulo - h + s(2)*mm)    

        y_current = y_titulo - s(8)*mm

        c.setFont("Helvetica", s(7))

        c.drawString(x_info, y_current, str(datos.get('ubicacion', '1')))
        y_current -= s(3.4)*mm

        procedencia = datos.get('procedencia', '')[:25]
        c.drawString(x_info, y_current, procedencia)
        y_current -= s(3.4)*mm

        # LOT
        lote = datos.get('lote', '')
        dibujar_lot(c, x_info, y_current - sym_size * 0.1, sym_size)
        c.setFont("Helvetica", s(7))
        c.drawString(x_info + sym_size + gap, y_current, lote)
        y_current -= s(3.4) * mm

        # EXP
        fecha = datos.get('vencimiento', '')
        dibujar_exp(c, x_info, y_current - sym_size * 0.1, sym_size)
        c.setFont("Helvetica", s(7))
        c.drawString(x_info + sym_size + gap, y_current, str(fecha))
        y_current -= s(3.4) * mm

        # ---------------------------
        # AREA CONTROLES
        # ---------------------------
        tabla_y = s(6.8) * mm  # la subimos un poco para dejar espacio al comentario
        tabla_height = s(10.5) * mm
        tabla_width = ancho - 2*margen

        c.rect(margen, tabla_y, tabla_width, tabla_height)

        col_width = tabla_width / 3

        c.line(margen + col_width, tabla_y,
               margen + col_width, tabla_y + tabla_height)

        c.line(margen + 2*col_width, tabla_y,
               margen + 2*col_width, tabla_y + tabla_height)

        c.line(margen, tabla_y + tabla_height/2,
               margen + tabla_width, tabla_y + tabla_height/2)

        c.setFont("Helvetica", s(5.8))
        pad = s(0.8)*mm

        # fila superior
        y1 = tabla_y + tabla_height/2 + pad

        c.drawString(margen + pad,
                     y1 + s(2.7)*mm,
                     "I.Q.EXT.")

        c.drawString(margen + pad,
                     y1,
                     datos.get('indicador_externo', ''))

        c.drawString(margen + col_width + pad,
                     y1 + s(2.7)*mm,
                     "I.Q.INT.")

        c.drawString(margen + col_width + pad,
                     y1,
                     datos.get('indicador_quimico', ''))

        c.drawString(margen + 2*col_width + pad,
                     y1 + s(2.7)*mm,
                     "P.TEMP.")

        c.drawString(margen + 2*col_width + pad,
                     y1,
                     datos.get('prueba_temperatura', ''))

        # fila inferior
        y2 = tabla_y + pad

        c.drawString(margen + pad,
                     y2 + s(2.7)*mm,
                     "P.PROT.")

        c.drawString(margen + pad,
                     y2,
                     datos.get('prueba_proteinas', ''))

        c.drawString(margen + col_width + pad,
                     y2 + s(2.7)*mm,
                     "P.BIO.")

        c.drawString(margen + col_width + pad,
                     y2,
                     datos.get('prueba_biologica', ''))
        
        c.drawString(margen + 2*col_width + pad,
                     y2 + s(2.7)*mm,
                     "S.EST.")

        c.drawString(margen + 2*col_width + pad,
                     y2,
                     datos.get('servicio_esterilizacion', ''))

        # ---------------------------
        # AREA COMENTARIO (NUEVA)
        # ---------------------------
        comentario_y = s(1.5) * mm
        comentario_height = s(5.5) * mm
        comentario_width = ancho - 2*margen

        c.rect(margen, comentario_y, comentario_width, comentario_height)

        c.setFont("Helvetica", s(5.8))
        c.drawString(margen + pad,
                     comentario_y + comentario_height - s(2)*mm,
                     "COMENTARIO")

        c.setFont("Helvetica", s(5))
        c.drawString(margen + pad,
                     comentario_y + s(1.2)*mm,
                     datos.get('comentario', '')[:40])

    c.save()
    buffer.seek(0)

    return buffer

