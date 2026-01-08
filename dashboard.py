import streamlit as st
import pandas as pd
import plotly.express as px
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
import tempfile
import os

st.set_page_config(page_title="Dashboard de Mantenimiento", layout="wide")

# --- Cargar datos ---
@st.cache_data
def load_data():
    return pd.read_excel("datos de mantenimiento.xlsx")

df = load_data()

# --- Normalizar nombres de columnas ---
df.columns = (
    df.columns.str.strip()
             .str.replace(" ", "_")
             .str.upper()
)

# --- Editor interactivo ---
st.subheader("✏️ Editor de datos en tiempo real")
df_editado = st.data_editor(df, num_rows="dynamic", use_container_width=True)

# --- Filtros ---
st.sidebar.header("Filtros")
ciudades = st.sidebar.multiselect("Selecciona ciudad:", options=df_editado['CIUDAD'].unique(), default=df_editado['CIUDAD'].unique())
estatus = st.sidebar.multiselect("Selecciona estatus:", options=df_editado['ESTATUS'].unique(), default=df_editado['ESTATUS'].unique())

df_filtered = df_editado[(df_editado['CIUDAD'].isin(ciudades)) & (df_editado['ESTATUS'].isin(estatus))]

# --- KPIs ---
total_mantenimientos = len(df_filtered)
no_ejecutados = len(df_filtered[df_filtered['ESTADO_DE_MANTENIMIENTO'].str.contains("NO EJECUTADO", case=False)])
porcentaje_no_ejecutados = (no_ejecutados / total_mantenimientos * 100) if total_mantenimientos > 0 else 0
tiempo_promedio = df_filtered['TIEMPO_DEMORA(DÍAS)'].mean() if 'TIEMPO_DEMORA(DÍAS)' in df_filtered else 0

col1, col2, col3 = st.columns(3)
col1.metric("Total mantenimientos", total_mantenimientos)
col2.metric("No ejecutados (%)", f"{porcentaje_no_ejecutados:.2f}%")
col3.metric("Tiempo promedio demora (días)", f"{tiempo_promedio:.2f}")

# --- Gráfico de barras por ciudad ---
st.subheader("📊 Mantenimientos por ciudad")
df_ciudad = df_filtered.groupby("CIUDAD").size().reset_index(name="Cantidad")
fig_ciudad = px.bar(df_ciudad, x="CIUDAD", y="Cantidad", color="CIUDAD", title="Cantidad de mantenimientos por ciudad")
st.plotly_chart(fig_ciudad, use_container_width=True)

# --- Gráfico de barras por C.O simple ---
st.subheader("📊 Mantenimientos por C.O (simple)")
df_co_simple = df_filtered.groupby("C.O").size().reset_index(name="Cantidad")
fig_co_simple = px.bar(df_co_simple, x="C.O", y="Cantidad", title="Cantidad de mantenimientos por C.O")
st.plotly_chart(fig_co_simple, use_container_width=True)

# --- Gráfico de barras por C.O con colores por ciudad ---
st.subheader("📊 Mantenimientos por C.O y Ciudad")
df_co_color = df_filtered.groupby(["C.O", "CIUDAD"]).size().reset_index(name="Cantidad")
fig_co_color = px.bar(df_co_color, x="C.O", y="Cantidad", color="CIUDAD", title="Cantidad de mantenimientos por C.O y Ciudad")
st.plotly_chart(fig_co_color, use_container_width=True)

# --- Gráfico circular por estatus ---
st.subheader("📊 Distribución por estatus")
fig_estatus = px.pie(df_filtered, names="ESTATUS", title="Distribución de estatus")
st.plotly_chart(fig_estatus, use_container_width=True)

# --- Línea de tiempo por mes ---
st.subheader("📊 Mantenimientos por mes")
fig_mes = px.histogram(df_filtered, x="MES_TEXTO", color="CIUDAD", title="Mantenimientos por mes")
st.plotly_chart(fig_mes, use_container_width=True)

# --- Tabla final ---
st.subheader("📋 Detalle de mantenimientos filtrados")
st.dataframe(df_filtered[['C.O','ALMACEN','CIUDAD','MES_TEXTO','SEMESTRE','EQUIPOS',
                          'ACTIVIDADES_A_REALIZAR','ESTATUS','ESTADO_DE_MANTENIMIENTO',
                          'FRECUENCIA_M.P.','DÍA_INICIO','FECHA_FINAL','DIAGNOSTICO',
                          'TIEMPO_DEMORA(DÍAS)']])

# --- Informe PDF con ReportLab + Gráficas ---
def generar_pdf(df):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(temp_file.name, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # Título
    titulo = Paragraph("Informe de Mantenimientos Pendientes", styles['Title'])
    elements.append(titulo)
    elements.append(Spacer(1, 12))

    # Tabla
    col_names = ["C.O","ALMACEN","CIUDAD","MES_TEXTO","SEMESTRE","ESTATUS","ESTADO_DE_MANTENIMIENTO"]
    data = [col_names]
    for _, row in df.iterrows():
        fila = [str(row[col])[:20] for col in col_names]
        data.append(fila)

    tabla = Table(data, repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#004080")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    elements.append(tabla)
    elements.append(Spacer(1, 20))

    # Guardar gráficas como imágenes temporales
    img_ciudad = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fig_ciudad.write_image(img_ciudad.name)
    elements.append(Paragraph("Gráfico: Mantenimientos por Ciudad", styles['Heading2']))
    elements.append(Image(img_ciudad.name, width=400, height=250))
    elements.append(Spacer(1, 20))

    img_co_color = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fig_co_color.write_image(img_co_color.name)
    elements.append(Paragraph("Gráfico: Mantenimientos por C.O y Ciudad", styles['Heading2']))
    elements.append(Image(img_co_color.name, width=400, height=250))

    # Construir PDF
    doc.build(elements)
    return temp_file.name

if st.button("📤 Exportar informe a PDF"):
    pendientes = df_filtered[df_filtered['ESTADO_DE_MANTENIMIENTO'].str.contains("NO EJECUTADO", case=False)]
    pdf_file = generar_pdf(pendientes)
    with open(pdf_file, "rb") as f:
        st.download_button("⬇️ Descargar PDF", f, file_name="informe_pendientes.pdf", mime="application/pdf")
    os.remove(pdf_file)