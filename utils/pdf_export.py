import os
# Set matplotlib to use non-interactive backend before importing
os.environ['MPLBACKEND'] = 'Agg'  # Force matplotlib to use non-GUI backend

import io
import tempfile
import requests
import traceback
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.platypus.flowables import Flowable
import plotly.io as pio
from PIL import Image as PILImage, ImageDraw, ImageFont
import logging
import pdfkit

# Configurar logging
logger = logging.getLogger(__name__)

# Definir colores corporativos de Alfred Smart
class AlfredColors:
    # Colores principales del brandbook
    COBALTO = colors.Color(0/255, 61/255, 89/255)  # RGB 0 61 89, HEX 003D59
    YELLOW = colors.Color(255/255, 190/255, 44/255)  # RGB 255 190 44, HEX FFBE2C
    BLACK = colors.Color(0/255, 22/255, 30/255)  # RGB 0 22 30, HEX 00161E
    GREY = colors.Color(221/255, 221/255, 221/255)  # RGB 221 221 221, HEX DDDDDD
    LIGHT_GREY = colors.Color(235/255, 235/255, 235/255)  # RGB 235 235 235, HEX EBEBEB
    WHITE = colors.white

    # Colores derivados para uso en el PDF
    COBALTO_LIGHT = colors.Color(0/255, 91/255, 119/255)  # Versión más clara del cobalto
    YELLOW_DARK = colors.Color(225/255, 160/255, 14/255)  # Versión más oscura del amarillo

# Clase para crear líneas horizontales
class HRFlowable(Flowable):
    """Flowable para crear líneas horizontales"""
    
    def __init__(self, width, height=0.1*cm, color=AlfredColors.COBALTO, thickness=1):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.color = color
        self.thickness = thickness
        
    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, self.height/2, self.width, self.height/2)

def download_image(url, temp_dir):
    """Descarga una imagen desde una URL y la guarda en un directorio temporal"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Crear un nombre de archivo temporal
        img_path = os.path.join(temp_dir, "logo.png")
        
        # Guardar la imagen
        with open(img_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return img_path
    except Exception as e:
        logger.error(f"Error al descargar la imagen: {str(e)}")
        return None

def fig_to_img(fig, width=800, height=500, temp_dir=None, scale=2.0):
    """
    Convierte una figura de Plotly a una imagen de alta calidad
    
    Args:
        fig: Figura de Plotly a convertir (o diccionario de figura)
        width: Ancho de la imagen en píxeles
        height: Alto de la imagen en píxeles
        temp_dir: Directorio temporal donde guardar la imagen
        scale: Factor de escala para aumentar la resolución (2.0 = doble resolución)
        
    Returns:
        str: Ruta a la imagen generada o None si hay un error
    """
    # Asegurar que tenemos un directorio temporal
    if temp_dir is None:
        temp_dir = tempfile.mkdtemp()
    
    # Crear un nombre de archivo temporal único
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    img_path = os.path.join(temp_dir, f"plot_{timestamp}.png")
    
    # MÉTODO 1: Usar plotly.io con kaleido (método principal)
    try:
        import plotly.graph_objects as go
        
        # Asegurarse de que la figura es válida
        if fig is None:
            logger.warning("La figura es None, se usará una figura vacía")
            fig = go.Figure()
            fig.add_annotation(
                text="No hay datos disponibles",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=16)
            )
        
        # Convertir diccionario a figura si es necesario
        if isinstance(fig, dict):
            logger.info("Convirtiendo diccionario a objeto Figure")
            try:
                # Si es un diccionario de figura de Plotly (con data y layout)
                if 'data' in fig and 'layout' in fig:
                    fig_obj = go.Figure(data=fig['data'], layout=fig['layout'])
                else:
                    # Si es un diccionario pero no tiene la estructura esperada
                    fig_obj = go.Figure()
                    fig_obj.add_annotation(
                        text="Error: Formato de figura no válido",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5,
                        showarrow=False,
                        font=dict(size=16, color='red')
                    )
                fig = fig_obj
            except Exception as e:
                logger.error(f"Error al convertir diccionario a figura: {str(e)}")
                fig = go.Figure()
                fig.add_annotation(
                    text=f"Error: {str(e)}",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5,
                    showarrow=False,
                    font=dict(size=16, color='red')
                )
        
        # Configurar la figura para exportación con colores corporativos
        fig.update_layout(
            margin=dict(l=40, r=40, t=40, b=40),
            paper_bgcolor='white',
            plot_bgcolor='white',
            font=dict(size=12),
            colorway=[
                'rgb(0,61,89)',    # COBALTO
                'rgb(0,91,119)',   # COBALTO_LIGHT (reemplazando YELLOW)
                'rgb(0,22,30)',    # BLACK
                'rgb(221,221,221)',# GREY
                'rgb(235,235,235)'  # LIGHT_GREY
            ]
        )
        
        # Intentar usar pio.to_image directamente (método más seguro)
        try:
            # Configurar opciones para evitar problemas con espacios en rutas
            pio.kaleido.scope.mathjax = None
            
            # Obtener la imagen como bytes
            img_bytes = pio.to_image(fig, format='png', width=width, height=height, scale=scale, engine='kaleido')
            
            # Guardar los bytes directamente en un archivo
            with open(img_path, 'wb') as f:
                f.write(img_bytes)
            
            logger.info(f"Gráfico guardado exitosamente en {img_path} usando kaleido")
            return img_path
            
        except Exception as e:
            logger.error(f"Error al usar kaleido: {str(e)}")
            logger.error(traceback.format_exc())
            # Continuar con el siguiente método
    
    except Exception as e:
        logger.error(f"Error en el método principal: {str(e)}")
        logger.error(traceback.format_exc())
        # Continuar con métodos alternativos
    
    # MÉTODO 2: Usar matplotlib con backend Agg (no interactivo)
    try:
        logger.info("Intentando método de respaldo con matplotlib (Agg backend)")
        
        # Importar matplotlib con backend Agg
        import matplotlib
        matplotlib.use('Agg')  # Asegurar que usamos backend no interactivo
        import matplotlib.pyplot as plt
        
        # Crear una figura simple
        plt.figure(figsize=(width/100, height/100), dpi=100)
        
        # Si tenemos una figura de plotly, intentar extraer datos
        try:
            import json
            from plotly.io import to_json
            
            # Convertir la figura de Plotly a JSON
            if hasattr(fig, 'to_dict'):
                fig_dict = fig.to_dict()
            elif isinstance(fig, dict):
                fig_dict = fig
            else:
                # Si no podemos convertir, crear un diccionario vacío
                fig_dict = {'data': [], 'layout': {}}
            
            # Extraer datos y graficarlos
            data = fig_dict.get('data', [])
            layout = fig_dict.get('layout', {})
            
            if data:
                for trace in data:
                    x = trace.get('x', [])
                    y = trace.get('y', [])
                    name = trace.get('name', '')
                    if x and y and len(x) == len(y):
                        plt.plot(x, y, label=name if name else None)
                
                # Añadir título y etiquetas
                title = layout.get('title', {})
                if isinstance(title, dict):
                    title_text = title.get('text', '')
                else:
                    title_text = str(title)
                
                plt.title(title_text)
                
                # Añadir etiquetas de ejes
                xaxis = layout.get('xaxis', {})
                if isinstance(xaxis, dict) and 'title' in xaxis:
                    if isinstance(xaxis['title'], dict):
                        plt.xlabel(xaxis['title'].get('text', ''))
                    else:
                        plt.xlabel(str(xaxis['title']))
                
                yaxis = layout.get('yaxis', {})
                if isinstance(yaxis, dict) and 'title' in yaxis:
                    if isinstance(yaxis['title'], dict):
                        plt.ylabel(yaxis['title'].get('text', ''))
                    else:
                        plt.ylabel(str(yaxis['title']))
                
                # Añadir leyenda si hay datos etiquetados
                if any(trace.get('name') for trace in data):
                    plt.legend()
            else:
                # Si no hay datos, mostrar un mensaje
                plt.text(0.5, 0.5, "No hay datos disponibles", 
                         horizontalalignment='center', verticalalignment='center',
                         transform=plt.gca().transAxes)
        
        except Exception as e:
            logger.error(f"Error al procesar datos de plotly: {str(e)}")
            # Si falla la extracción de datos, crear un gráfico simple con mensaje de error
            plt.text(0.5, 0.5, f"Error al procesar datos: {str(e)}", 
                     horizontalalignment='center', verticalalignment='center',
                     transform=plt.gca().transAxes, color='red')
        
        # Guardar la figura y cerrarla para liberar recursos
        plt.savefig(img_path, bbox_inches='tight')
        plt.close('all')  # Cerrar todas las figuras para evitar fugas de memoria
        
        logger.info(f"Gráfico guardado exitosamente en {img_path} usando matplotlib")
        return img_path
        
    except Exception as e:
        logger.error(f"Error al usar matplotlib: {str(e)}")
        logger.error(traceback.format_exc())
        # Continuar con el método de imagen de error
    
    # MÉTODO 3: Crear una imagen de error simple con PIL
    try:
        logger.info("Creando imagen de error con PIL")
        
        # Crear una imagen en blanco
        img = PILImage.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Añadir un borde
        border_color = (0, 61, 89)  # COBALTO
        border_width = 5
        draw.rectangle([(0, 0), (width-1, height-1)], outline=border_color, width=border_width)
        
        # Añadir un mensaje de error
        error_message = "Error al generar gráfico"
        
        # Calcular tamaño de texto y posición
        text_color = (0, 22, 30)  # BLACK
        text_position = (width//2, height//2)
        
        # Dibujar texto centrado
        draw.text(
            text_position, 
            error_message, 
            fill=text_color, 
            anchor="mm"  # Centrar texto
        )
        
        # Guardar la imagen
        img.save(img_path)
        
        logger.info(f"Imagen de error creada en {img_path}")
        return img_path
        
    except Exception as e:
        logger.error(f"Error al crear imagen de error con PIL: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Si todos los métodos fallan, devolver None
    logger.error("Todos los métodos de generación de imagen han fallado")
    return None

def create_cover_page(canvas, doc, logo_path, title, subtitle, client_name, community_name, period_label):
    """Crea una portada para el PDF con fondo azul completo y textos en blanco"""
    canvas.saveState()
    
    # Fondo de color azul cobalto en toda la página
    canvas.setFillColor(AlfredColors.COBALTO)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    
    # Barra superior - Mismo color COBALTO pero con un borde para distinguirla
    canvas.setStrokeColor(AlfredColors.YELLOW)
    canvas.setLineWidth(1)
    canvas.rect(0, A4[1] - 3*cm, A4[0], 3*cm, fill=1, stroke=1)
    
    # Barra inferior - Mismo color COBALTO pero con un borde para distinguirla
    canvas.setStrokeColor(AlfredColors.YELLOW)
    canvas.setLineWidth(1)
    canvas.rect(0, 0, A4[0], 1.5*cm, fill=1, stroke=1)
    
    # Añadir logo - Usando mask=True para preservar la transparencia
    if logo_path:
        canvas.drawImage(logo_path, A4[0]/2 - 2*inch, A4[1] - 5*inch, width=4*inch, height=2*inch, preserveAspectRatio=True, mask='auto')
    
    # Título principal - Movido más abajo para evitar solapamiento con el logo
    canvas.setFont("Helvetica-Bold", 24)
    canvas.setFillColor(AlfredColors.WHITE)
    canvas.drawCentredString(A4[0]/2, A4[1]/2 - 1*inch, title)
    
    # Subtítulo - Ajustado para mantener la distancia con el título
    canvas.setFont("Helvetica", 16)
    canvas.setFillColor(AlfredColors.WHITE)
    canvas.drawCentredString(A4[0]/2, A4[1]/2 - 1.5*inch, subtitle)
    
    # Información del cliente - Ajustada para mantener la distancia con el subtítulo
    canvas.setFont("Helvetica-Bold", 14)
    canvas.setFillColor(AlfredColors.WHITE)
    
    # Mostrar directamente el nombre del cliente sin el prefijo "Cliente:"
    client_text = client_name
    if community_name and community_name.lower() != "all" and community_name.lower() != "comunidad":
        client_text += f" - {community_name}"
    canvas.drawCentredString(A4[0]/2, A4[1]/2 - 2.5*inch, client_text)
    
    # Período - Ajustado para mantener la distancia con la información del cliente
    canvas.setFont("Helvetica", 12)
    canvas.setFillColor(AlfredColors.WHITE)
    canvas.drawCentredString(A4[0]/2, A4[1]/2 - 3*inch, f"Período de análisis: {period_label}")
    
    # Añadir una línea decorativa
    canvas.setStrokeColor(AlfredColors.YELLOW)
    canvas.setLineWidth(2)
    canvas.line(A4[0]/4, A4[1]/2 - 2*inch, 3*A4[0]/4, A4[1]/2 - 2*inch)
    
    # Footer profesional
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(AlfredColors.WHITE)
    footer_text = "Optimizando la gestión de espacios | © 2025 Alfred Smart"
    
    # Posición del footer
    footer_x = 1*cm
    footer_y = 0.5*cm
    
    canvas.drawString(footer_x, footer_y, footer_text)
    
    canvas.restoreState()

def add_page_number(canvas, doc):
    """Añade números de página al PDF con estilo corporativo"""
    canvas.saveState()
    
    # Barra inferior con color COBALTO_LIGHT (reemplazando YELLOW)
    canvas.setFillColor(AlfredColors.COBALTO_LIGHT)
    canvas.rect(0, 0, A4[0], 1*cm, fill=1, stroke=0)
    
    # Barra superior con color COBALTO
    canvas.setFillColor(AlfredColors.COBALTO)
    canvas.rect(0, A4[1] - 1.5*cm, A4[0], 1.5*cm, fill=1, stroke=0)
    
    # Logo pequeño en el encabezado
    canvas.setFont('Helvetica-Bold', 10)
    canvas.setFillColor(AlfredColors.WHITE)
    canvas.drawString(2*cm, A4[1] - 1*cm, "Alfred Smart - Informe de Reservas")
    
    # Número de página con formato simplificado
    canvas.setFont("Helvetica-Bold", 10)
    canvas.setFillColor(AlfredColors.WHITE)
    page_num = canvas.getPageNumber()
    text = f"Página {page_num} | Alfred Spaces - Análisis de Reservas | Optimizando la gestión de espacios | © 2025 Alfred Smart"
    canvas.drawRightString(A4[0] - 2*cm, 0.5*cm, text)
    
    canvas.restoreState()

def generate_spaces_report_pdf(
    client_name, 
    community_name, 
    period_label, 
    weekly_bookings_fig, 
    daily_occupation_fig, 
    avg_weekly_bookings, 
    max_day_occupation, 
    total_bookings_period, 
    avg_occupation_rate,
    weekly_occupation_data=None,
    spaces_reservations_data=None,
    logo_url="https://alfred-storage.ams3.digitaloceanspaces.com/images/93fff449-e583-47c7-951b-fb1eff8c2d2c/20240129/f12bf27d-0b07-466f-9e6f-43f8a1b2d392.png"
):
    """
    Genera un informe PDF con los datos de análisis de espacios.
    
    Args:
        client_name: Nombre del cliente
        community_name: Nombre de la comunidad
        period_label: Etiqueta del período de análisis
        weekly_bookings_fig: Figura de reservas semanales
        daily_occupation_fig: Figura de ocupación diaria
        avg_weekly_bookings: Promedio de reservas semanales
        max_day_occupation: Día con mayor ocupación
        total_bookings_period: Total de reservas en el período
        avg_occupation_rate: Tasa de ocupación media
        weekly_occupation_data: Datos de ocupación por semana y día
        spaces_reservations_data: Datos de espacios por reservas
        logo_url: URL del logo de Alfred Smart
    
    Returns:
        bytes: Contenido del PDF generado
    """
    try:
        # Crear un directorio temporal para las imágenes
        with tempfile.TemporaryDirectory() as temp_dir:
            # Descargar el logo
            logo_path = download_image(logo_url, temp_dir)
            
            # Convertir las figuras a imágenes de alta calidad
            weekly_img_path = fig_to_img(weekly_bookings_fig, temp_dir=temp_dir, scale=2.0)
            daily_img_path = fig_to_img(daily_occupation_fig, temp_dir=temp_dir, scale=2.0)
            
            # Crear un buffer para el PDF
            buffer = io.BytesIO()
            
            # Asegurar que client_name y community_name tengan valores predeterminados si son None o "all"
            if not client_name or client_name.lower() == "all":
                client_name = "Todos los clientes"
            if not community_name or community_name.lower() == "all":
                community_name = "Todas las comunidades"
            
            # Crear el documento PDF
            doc = SimpleDocTemplate(
                buffer, 
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            # Estilos
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                name='CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                alignment=1,  # Centrado
                spaceAfter=12,
                textColor=AlfredColors.COBALTO
            )
            
            subtitle_style = ParagraphStyle(
                name='CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=8,
                textColor=AlfredColors.COBALTO
            )
            
            normal_style = ParagraphStyle(
                name='CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=6,
                textColor=AlfredColors.BLACK
            )
            
            # Elementos del PDF
            elements = []
            
            # Primera página (portada) - se maneja con onFirstPage
            elements.append(PageBreak())
            
            # Título de la sección de resumen ejecutivo
            elements.append(Paragraph("Resumen Ejecutivo", title_style))
            elements.append(HRFlowable(width=doc.width, color=AlfredColors.COBALTO, thickness=2))
            elements.append(Spacer(1, 0.5*cm))
            
            # Descripción del informe con datos clave destacados
            description = f"""
            Este informe presenta un análisis detallado de las reservas de espacios para <b>{client_name}</b>
            durante el período <b>{period_label}</b>. A continuación se presentan los datos más relevantes:
            """
            elements.append(Paragraph(description, normal_style))
            elements.append(Spacer(1, 0.5*cm))
            
            # Resumen ejecutivo con los datos clave solicitados
            executive_summary = [
                ["Métrica", "Valor", "Descripción"],
                ["Total de reservas", total_bookings_period, "Número total de reservas realizadas en el período"],
                ["Promedio", avg_weekly_bookings, "Promedio de reservas por semana"],
                ["Mayor Ocupación", max_day_occupation, "Día de la semana con mayor tasa de ocupación"],
                ["Ocupación media", avg_occupation_rate, "Porcentaje promedio de ocupación de los espacios"]
            ]
            
            # Estilo de tabla para el resumen ejecutivo
            exec_table_style = TableStyle([
                # Encabezado
                ('BACKGROUND', (0, 0), (-1, 0), AlfredColors.COBALTO),
                ('TEXTCOLOR', (0, 0), (-1, 0), AlfredColors.WHITE),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                # Filas alternas
                ('BACKGROUND', (0, 1), (-1, 1), AlfredColors.LIGHT_GREY),
                ('BACKGROUND', (0, 3), (-1, 3), AlfredColors.LIGHT_GREY),
                # Bordes
                ('GRID', (0, 0), (-1, -1), 0.5, AlfredColors.GREY),
                ('BOX', (0, 0), (-1, -1), 1, AlfredColors.BLACK),
                # Alineación
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                # Padding
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                # Aplicar negrita a los valores
                ('FONTNAME', (1, 1), (1, -1), 'Helvetica-Bold'),
            ])
            
            # Crear tabla de resumen ejecutivo
            exec_table = Table(executive_summary, colWidths=[doc.width*0.25, doc.width*0.25, doc.width*0.5])
            exec_table.setStyle(exec_table_style)
            elements.append(exec_table)
            elements.append(Spacer(1, 1*cm))
            
            # Interpretación del resumen ejecutivo
            interpretation = f"""
            <b>Interpretación:</b> Durante el período analizado, se registraron un total de {total_bookings_period} reservas
            de espacios, con un promedio de {avg_weekly_bookings} reservas semanales. El día de la semana con mayor
            ocupación fue {max_day_occupation}, y la ocupación media fue del {avg_occupation_rate}.
            """
            elements.append(Paragraph(interpretation, normal_style))
            elements.append(Spacer(1, 1*cm))
            
            # Sección de gráficos
            elements.append(Paragraph("Análisis Gráfico", title_style))
            elements.append(HRFlowable(width=doc.width, color=AlfredColors.COBALTO, thickness=2))
            elements.append(Spacer(1, 0.5*cm))
            
            # Gráfico de reservas semanales
            if weekly_img_path:
                elements.append(Paragraph("Reservas por Semana", subtitle_style))
                elements.append(Spacer(1, 0.25*cm))
                
                # Descripción del gráfico
                weekly_desc = """
                Este gráfico muestra la distribución de reservas por semana durante el período seleccionado.
                Permite identificar tendencias y patrones en el volumen de reservas a lo largo del tiempo.
                """
                elements.append(Paragraph(weekly_desc, normal_style))
                elements.append(Spacer(1, 0.25*cm))
                
                # Crear un contenedor para la imagen con un borde y sombra
                img_container = []
                
                # Añadir la imagen con mejor calidad y tamaño optimizado
                img = Image(weekly_img_path, width=doc.width*0.9, height=doc.width*0.45)
                img.hAlign = 'CENTER'
                
                # Añadir un marco alrededor de la imagen
                img_frame = Table(
                    [[img]], 
                    colWidths=[doc.width*0.9],
                    style=TableStyle([
                        ('BOX', (0, 0), (-1, -1), 0.5, AlfredColors.GREY),
                        ('BACKGROUND', (0, 0), (-1, -1), AlfredColors.WHITE),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 5),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                        ('TOPPADDING', (0, 0), (-1, -1), 5),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ])
                )
                
                # Centrar el marco en la página
                img_frame_container = Table(
                    [[img_frame]],
                    style=TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ])
                )
                
                elements.append(img_frame_container)
                elements.append(Spacer(1, 0.5*cm))
                
                # Añadir una leyenda o nota al pie del gráfico
                weekly_note = """
                <i>Nota: El gráfico muestra el número total de reservas por semana. Las semanas se representan 
                en formato ISO (AAAA-Wnn) donde AAAA es el año y nn es el número de semana.</i>
                """
                elements.append(Paragraph(weekly_note, ParagraphStyle(
                    name='ImageNote',
                    parent=normal_style,
                    fontSize=8,
                    alignment=1  # Centrado
                )))
                elements.append(Spacer(1, 1*cm))
            
            # Gráfico de ocupación diaria
            if daily_img_path:
                elements.append(Paragraph("Ocupación Media por Día", subtitle_style))
                elements.append(Spacer(1, 0.25*cm))
                
                # Descripción del gráfico
                daily_desc = """
                Este gráfico muestra la ocupación media por día de la semana. Permite identificar
                los días con mayor y menor demanda, facilitando la planificación de recursos.
                """
                elements.append(Paragraph(daily_desc, normal_style))
                elements.append(Spacer(1, 0.25*cm))
                
                # Crear un contenedor para la imagen con un borde y sombra
                img_container = []
                
                # Añadir la imagen con mejor calidad y tamaño optimizado
                img = Image(daily_img_path, width=doc.width*0.9, height=doc.width*0.45)
                img.hAlign = 'CENTER'
                
                # Añadir un marco alrededor de la imagen
                img_frame = Table(
                    [[img]], 
                    colWidths=[doc.width*0.9],
                    style=TableStyle([
                        ('BOX', (0, 0), (-1, -1), 0.5, AlfredColors.GREY),
                        ('BACKGROUND', (0, 0), (-1, -1), AlfredColors.WHITE),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 5),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                        ('TOPPADDING', (0, 0), (-1, -1), 5),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ])
                )
                
                # Centrar el marco en la página
                img_frame_container = Table(
                    [[img_frame]],
                    style=TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ])
                )
                
                elements.append(img_frame_container)
                elements.append(Spacer(1, 0.5*cm))
                
                # Añadir una leyenda o nota al pie del gráfico
                daily_note = """
                <i>Nota: El gráfico muestra el porcentaje de ocupación para cada día de la semana, 
                calculado como la proporción de reservas realizadas respecto al total.</i>
                """
                elements.append(Paragraph(daily_note, ParagraphStyle(
                    name='ImageNote',
                    parent=normal_style,
                    fontSize=8,
                    alignment=1  # Centrado
                )))
                elements.append(Spacer(1, 1*cm))
            
            # NUEVA SECCIÓN: Tabla de ocupación por semana y día
            if weekly_occupation_data and weekly_occupation_data.get('weeks') and weekly_occupation_data.get('days'):
                elements.append(Paragraph("Ocupación Semanal por Día (%)", subtitle_style))
                elements.append(Spacer(1, 0.25*cm))
                
                # Descripción de la tabla
                table_desc = """
                Esta tabla muestra el porcentaje de ocupación para cada día de la semana, desglosado por semanas.
                Los valores representan el porcentaje de espacios ocupados en cada día respecto al total de espacios
                disponibles.
                """
                elements.append(Paragraph(table_desc, normal_style))
                elements.append(Spacer(1, 0.5*cm))
                
                # Obtener datos
                weeks = weekly_occupation_data.get('weeks', [])
                days = weekly_occupation_data.get('days', [])
                data = weekly_occupation_data.get('data', {})
                
                # Crear encabezados de la tabla
                table_data = [["Semana"] + days]
                
                # Añadir filas para cada semana
                for week in weeks:
                    week_values = data.get(week, {})
                    row = [week]
                    for day in days:
                        value = week_values.get(day, 0)
                        # Formatear el valor como porcentaje
                        row.append(f"{value:.1f}%".replace(".", ","))
                    table_data.append(row)
                
                # Si no hay datos, mostrar un mensaje
                if len(weeks) == 0:
                    table_data = [["No hay datos disponibles para el período seleccionado"]]
                
                # Calcular anchos de columna
                col_widths = [doc.width*0.2] + [doc.width*0.8/len(days)]*len(days) if days else [doc.width]
                
                # Crear estilos para la tabla
                occupation_table_style = TableStyle([
                    # Encabezado
                    ('BACKGROUND', (0, 0), (-1, 0), AlfredColors.COBALTO),
                    ('TEXTCOLOR', (0, 0), (-1, 0), AlfredColors.WHITE),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    # Primera columna (semanas)
                    ('BACKGROUND', (0, 1), (0, -1), AlfredColors.LIGHT_GREY),
                    ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                    # Bordes
                    ('GRID', (0, 0), (-1, -1), 0.5, AlfredColors.GREY),
                    ('BOX', (0, 0), (-1, -1), 1, AlfredColors.BLACK),
                    # Alineación
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                    # Padding
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ])
                
                # Definir colores para los niveles de ocupación
                color_danger = colors.Color(220/255, 53/255, 69/255)  # Rojo - Bootstrap danger
                color_warning = colors.Color(255/255, 193/255, 7/255)  # Amarillo - Bootstrap warning
                color_info = colors.Color(23/255, 162/255, 184/255)    # Azul - Bootstrap info
                color_success = colors.Color(40/255, 167/255, 69/255)  # Verde - Bootstrap success
                
                # Aplicar colores según el valor de ocupación
                for i, week in enumerate(weeks, 1):
                    week_values = data.get(week, {})
                    for j, day in enumerate(days, 1):
                        value = week_values.get(day, 0)
                        
                        # Aplicar color según el valor
                        if value > 75:
                            occupation_table_style.add('BACKGROUND', (j, i), (j, i), color_danger)
                            occupation_table_style.add('TEXTCOLOR', (j, i), (j, i), colors.white)
                        elif value > 50:
                            occupation_table_style.add('BACKGROUND', (j, i), (j, i), color_warning)
                            occupation_table_style.add('TEXTCOLOR', (j, i), (j, i), colors.black)
                        elif value > 25:
                            occupation_table_style.add('BACKGROUND', (j, i), (j, i), color_info)
                            occupation_table_style.add('TEXTCOLOR', (j, i), (j, i), colors.white)
                        elif value > 0:
                            occupation_table_style.add('BACKGROUND', (j, i), (j, i), color_success)
                            occupation_table_style.add('TEXTCOLOR', (j, i), (j, i), colors.white)
                
                # Crear la tabla
                occupation_table = Table(table_data, colWidths=col_widths)
                occupation_table.setStyle(occupation_table_style)
                
                # Añadir la tabla al PDF
                elements.append(occupation_table)
                elements.append(Spacer(1, 0.5*cm))
                
                # Añadir leyenda de colores
                elements.append(Paragraph("Leyenda de colores:", ParagraphStyle(
                    name='LegendTitle',
                    parent=normal_style,
                    fontSize=10,
                    fontName='Helvetica-Bold'
                )))
                
                # Crear tabla para la leyenda
                legend_data = [
                    ["", "Ocupación > 75%", "", "Ocupación > 50%", "", "Ocupación > 25%", "", "Ocupación > 0%"]
                ]
                
                legend_style = TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    # Colores para las celdas de la leyenda
                    ('BACKGROUND', (0, 0), (0, 0), color_danger),
                    ('BACKGROUND', (2, 0), (2, 0), color_warning),
                    ('BACKGROUND', (4, 0), (4, 0), color_info),
                    ('BACKGROUND', (6, 0), (6, 0), color_success),
                    # Tamaño de las celdas de color
                    ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
                    ('LINEBELOW', (2, 0), (2, 0), 1, colors.black),
                    ('LINEBELOW', (4, 0), (4, 0), 1, colors.black),
                    ('LINEBELOW', (6, 0), (6, 0), 1, colors.black),
                ])
                
                # Crear la tabla de leyenda
                legend_table = Table(legend_data, colWidths=[0.5*cm, 3*cm, 0.5*cm, 3*cm, 0.5*cm, 3*cm, 0.5*cm, 3*cm])
                legend_table.setStyle(legend_style)
                
                elements.append(legend_table)
                elements.append(Spacer(1, 0.25*cm))
                
                # Añadir una nota al pie de la tabla
                table_note = """
                <i>Nota: Los valores representan el porcentaje de ocupación para cada día dentro de su semana.
                Las celdas vacías o con valor 0,0% indican que no hubo reservas en ese día específico.</i>
                """
                elements.append(Paragraph(table_note, ParagraphStyle(
                    name='TableNote',
                    parent=normal_style,
                    fontSize=8,
                    alignment=1  # Centrado
                )))
                elements.append(Spacer(1, 1*cm))
            
            # NUEVA SECCIÓN: Tabla de espacios por reservas
            if spaces_reservations_data and spaces_reservations_data.get('spaces'):
                elements.append(Paragraph("Espacios por Número de Reservas", subtitle_style))
                elements.append(Spacer(1, 0.25*cm))
                
                # Descripción de la tabla
                table_desc = """
                Esta tabla muestra los espacios ordenados por el número total de reservas, con el desglose por día de la semana.
                Los valores representan el número de reservas para cada espacio en cada día de la semana.
                """
                elements.append(Paragraph(table_desc, normal_style))
                elements.append(Spacer(1, 0.5*cm))
                
                # Obtener datos
                spaces = spaces_reservations_data.get('spaces', [])
                days = spaces_reservations_data.get('days', [])
                data = spaces_reservations_data.get('data', {})
                
                # Crear encabezados de la tabla
                header_row = ["Espacio", "Total"] + days
                table_data = [header_row]
                
                # Añadir filas para cada espacio
                for space in spaces:
                    space_id = space['common_area_id']
                    space_data = data.get(space_id, {})
                    
                    if not space_data:
                        continue
                    
                    # Crear fila para este espacio
                    row = [
                        space_data.get('name', 'Desconocido'),
                        space_data.get('total', 0)
                    ]
                    
                    # Añadir celdas para cada día
                    day_counts = space_data.get('days', {})
                    for day in days:
                        count = day_counts.get(day, 0)
                        row.append(count)
                    
                    table_data.append(row)
                
                # Si no hay datos, mostrar un mensaje
                if len(spaces) == 0:
                    table_data = [["No hay datos disponibles para el período seleccionado"]]
                
                # Calcular anchos de columna
                col_widths = [doc.width*0.3, doc.width*0.1] + [doc.width*0.6/len(days)]*len(days) if days else [doc.width]
                
                # Crear estilos para la tabla
                spaces_table_style = TableStyle([
                    # Encabezado
                    ('BACKGROUND', (0, 0), (-1, 0), AlfredColors.COBALTO),
                    ('TEXTCOLOR', (0, 0), (-1, 0), AlfredColors.WHITE),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    # Primera columna (espacios)
                    ('BACKGROUND', (0, 1), (0, -1), AlfredColors.LIGHT_GREY),
                    ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                    # Segunda columna (total)
                    ('FONTNAME', (1, 1), (1, -1), 'Helvetica-Bold'),
                    # Bordes
                    ('GRID', (0, 0), (-1, -1), 0.5, AlfredColors.GREY),
                    ('BOX', (0, 0), (-1, -1), 1, AlfredColors.BLACK),
                    # Alineación
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                    # Padding
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ])
                
                # Definir colores para los niveles de uso
                color_high = colors.Color(220/255, 53/255, 69/255)  # Rojo - Bootstrap danger
                color_medium = colors.Color(255/255, 193/255, 7/255)  # Amarillo - Bootstrap warning
                color_low = colors.Color(23/255, 162/255, 184/255)    # Azul - Bootstrap info
                
                # Aplicar colores según el valor
                for i, row in enumerate(table_data[1:], 1):
                    for j, value in enumerate(row[2:], 2):  # Empezar desde la tercera columna (días)
                        if value > 10:
                            spaces_table_style.add('BACKGROUND', (j, i), (j, i), color_high)
                            spaces_table_style.add('TEXTCOLOR', (j, i), (j, i), colors.white)
                        elif value > 5:
                            spaces_table_style.add('BACKGROUND', (j, i), (j, i), color_medium)
                            spaces_table_style.add('TEXTCOLOR', (j, i), (j, i), colors.black)
                        elif value > 0:
                            spaces_table_style.add('BACKGROUND', (j, i), (j, i), color_low)
                            spaces_table_style.add('TEXTCOLOR', (j, i), (j, i), colors.white)
                
                # Crear la tabla
                spaces_table = Table(table_data, colWidths=col_widths)
                spaces_table.setStyle(spaces_table_style)
                
                # Añadir la tabla al PDF
                elements.append(spaces_table)
                elements.append(Spacer(1, 0.5*cm))
                
                # Añadir leyenda de colores
                elements.append(Paragraph("Leyenda de colores:", ParagraphStyle(
                    name='LegendTitle',
                    parent=normal_style,
                    fontSize=10,
                    fontName='Helvetica-Bold'
                )))
                
                # Crear tabla para la leyenda
                legend_data = [
                    ["", "Alto (>10)", "", "Medio (>5)", "", "Bajo (>0)"]
                ]
                
                legend_style = TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    # Colores para las celdas de la leyenda
                    ('BACKGROUND', (0, 0), (0, 0), color_high),
                    ('BACKGROUND', (2, 0), (2, 0), color_medium),
                    ('BACKGROUND', (4, 0), (4, 0), color_low),
                    # Tamaño de las celdas de color
                    ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
                    ('LINEBELOW', (2, 0), (2, 0), 1, colors.black),
                    ('LINEBELOW', (4, 0), (4, 0), 1, colors.black),
                ])
                
                # Crear la tabla de leyenda
                legend_table = Table(legend_data, colWidths=[0.5*cm, 3*cm, 0.5*cm, 3*cm, 0.5*cm, 3*cm])
                legend_table.setStyle(legend_style)
                
                elements.append(legend_table)
                elements.append(Spacer(1, 0.25*cm))
                
                # Añadir una nota al pie de la tabla
                table_note = """
                <i>Nota: Los valores representan el número de reservas para cada espacio en cada día de la semana.
                Las celdas vacías o con valor 0 indican que no hubo reservas para ese espacio en ese día específico.</i>
                """
                elements.append(Paragraph(table_note, ParagraphStyle(
                    name='TableNote',
                    parent=normal_style,
                    fontSize=8,
                    alignment=1  # Centrado
                )))
                elements.append(Spacer(1, 1*cm))
            
            # Conclusiones
            elements.append(Paragraph("Conclusiones", title_style))
            elements.append(HRFlowable(width=doc.width, color=AlfredColors.COBALTO, thickness=2))
            elements.append(Spacer(1, 0.5*cm))
            
            # Texto de conclusiones
            conclusions = f"""
            <b>Análisis de Uso:</b> El análisis de las reservas durante el período {period_label} muestra patrones
            de uso que pueden ayudar a optimizar la gestión de espacios. {max_day_occupation} es el día con mayor
            demanda, lo que sugiere la necesidad de asegurar una disponibilidad adecuada en ese día.
            
            <b>Recomendaciones:</b> Con una ocupación media del {avg_occupation_rate}, se recomienda
            evaluar la posibilidad de ajustar la disponibilidad de espacios según la demanda observada.
            El promedio de {avg_weekly_bookings} reservas semanales indica un nivel de uso que debe ser
            monitoreado para identificar tendencias a largo plazo.
            
            <b>Próximos Pasos:</b> Se sugiere realizar un seguimiento continuo de estos indicadores para
            detectar cambios en los patrones de uso y ajustar la gestión de espacios en consecuencia.
            """
            elements.append(Paragraph(conclusions, normal_style))
            
            # Construir el PDF
            doc.build(
                elements,
                onFirstPage=lambda canvas, doc: create_cover_page(
                    canvas, doc, logo_path, 
                    "Informe de Reservas de Espacios",
                    "Análisis Detallado de Uso y Ocupación",
                    client_name, community_name, period_label
                ),
                onLaterPages=add_page_number
            )
            
            # Obtener el contenido del PDF
            pdf_content = buffer.getvalue()
            buffer.close()
            
            return pdf_content
    
    except Exception as e:
        logger.error(f"Error al generar el PDF: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Crear un PDF de error simple en lugar de devolver None
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []
        
        elements.append(Paragraph("Error al generar el informe", styles['Heading1']))
        elements.append(Spacer(1, 0.25*inch))
        elements.append(Paragraph(f"Se ha producido un error al generar el informe: {str(e)}", styles['Normal']))
        elements.append(Spacer(1, 0.25*inch))
        elements.append(Paragraph(f"Fecha y hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
        
        # Construir el PDF con el footer profesional incluso en caso de error
        doc.build(
            elements,
            onFirstPage=add_page_number,
            onLaterPages=add_page_number
        )
        
        pdf_content = buffer.getvalue()
        buffer.close()
        
        return pdf_content 