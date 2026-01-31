import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime
import geopandas as gpd
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

# ==========================
# CONFIGURACIÓN DE PRODUCCIÓN
# ==========================
st.set_page_config(
    page_title="Dashboard Obeya Comercial 2026",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================
# PALETA DE COLORES CORPORATIVA
# ==========================
COLORS = {
    'primary': '#1e3c72',
    'secondary': '#2a5298',
    'accent': '#7fa8e0',
    'success': '#28a745',
    'warning': '#ffc107',
    'danger': '#dc3545',
    'info': '#17a2b8',
    'light': '#f8f9fa',
    'dark': '#343a40',
    'gradient_start': '#1e3c72',
    'gradient_end': '#2a5298'
}

CHART_COLORS = ['#1e3c72', '#2a5298', '#7fa8e0', '#5080c0', '#3060a0', '#406db8']

# ==========================
# CONFIGURACIÓN DE RUTAS
# ==========================
import os

# Rutas flexibles: desarrollo local vs Streamlit Cloud
# En Streamlit Cloud el CSV va en la raíz del repositorio
# En local puede estar en una carpeta específica
CSV_PATH = os.environ.get('CSV_PATH', 'empleados_activos.csv')
GEOJSON_PATH = os.environ.get('GEODATA_PATH', 'geodata')

# ==========================
# ESTILOS CSS PERSONALIZADOS
# ==========================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .main-header p {
        font-size: 1.1rem;
        margin-top: 0.5rem;
        opacity: 0.95;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #1e3c72;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.12);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1e3c72;
        margin: 0.5rem 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 500;
    }
    
    .metric-delta {
        font-size: 0.85rem;
        color: #28a745;
        margin-top: 0.5rem;
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fa 0%, #ffffff 100%);
    }
    
    [data-testid="stSidebar"] .element-container {
        padding: 0.5rem 0;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.5rem;
        font-weight: 500;
        transition: all 0.3s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    hr {
        margin: 2rem 0;
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #1e3c72, transparent);
    }
    
    .dataframe {
        font-size: 0.9rem;
    }
    
    .dataframe thead tr th {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        padding: 1rem !important;
    }
    
    .dataframe tbody tr:hover {
        background-color: #f0f5ff !important;
    }
    
    .stSelectbox [data-baseweb="select"] {
        border-radius: 8px;
    }
    
    .js-plotly-plot {
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .stAlert {
        border-radius: 8px;
        border-left: 4px solid;
    }
    
    .footer-info {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin-top: 2rem;
        text-align: center;
        border-top: 3px solid #1e3c72;
    }
</style>
""", unsafe_allow_html=True)

# ==========================
# MAPEO DE MESES A NÚMERO
# ==========================
MES_A_NUMERO = {
    'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4,
    'MAYO': 5, 'JUNIO': 6, 'JULIO': 7, 'AGOSTO': 8,
    'SEPTIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12
}

# ==========================
# FUNCIONES DE CARGA DE DATOS
# ==========================
@st.cache_data(ttl=600, show_spinner=False)
def load_csv():
    """
    Carga el CSV una sola vez y lo cachea.
    Retorna el DataFrame completo sin filtros.
    """
    try:
        df = pd.read_csv(CSV_PATH)

        # Normalizar nombres de columna: elimina espacios y convierte a minúscula
        df.columns = df.columns.str.strip().str.lower()

        # Mapeo flexible de nombres de columna al estándar que usa el dashboard.
        # Esto permite que el CSV tenga encabezados ligeramente diferentes
        # sin que se rompa nada.
        rename_map = {}

        # Coordenadas: el CSV puede tener "longitud" o "logitud" (como en la BD original)
        if 'logitud' in df.columns and 'longitud' not in df.columns:
            rename_map['logitud'] = 'longitud'

        # Año: puede venir como "año" o "ano" (sin tilde)
        if 'ano' in df.columns and 'año' not in df.columns:
            rename_map['ano'] = 'año'

        if rename_map:
            df.rename(columns=rename_map, inplace=True)

        # Convertir tipos
        df['latitud']  = pd.to_numeric(df['latitud'],  errors='coerce')
        df['longitud'] = pd.to_numeric(df['longitud'], errors='coerce')
        df['año']      = pd.to_numeric(df['año'],      errors='coerce').astype(int)

        # Normalizar texto: mayúsculas en mes para que el filtro funcione
        df['mes'] = df['mes'].astype(str).str.strip().str.upper()

        return df

    except FileNotFoundError:
        st.error(
            "❌ No se encontró el archivo CSV.\n\n"
            f"Ruta buscada: **{CSV_PATH}**\n\n"
            "Para Streamlit Cloud: coloca `empleados_activos.csv` en la raíz del repositorio.\n"
            "Para desarrollo local: coloca el archivo en la misma carpeta que este script."
        )
        st.stop()
    except Exception as e:
        st.error(f"❌ Error al cargar el CSV: {str(e)}")
        st.stop()


@st.cache_data(ttl=600, show_spinner=False)
def process_data(df_raw, mes, año):
    """
    Aplica la misma lógica que tenía la query SQL:
    - Filtra por mes y año
    - Si el CSV ya tiene Total_activos (pre-agregado), lo usa directamente
    - Si no, agrupa por las columnas necesarias y cuenta empleados
    - Genera la columna Fecha
    - Elimina filas sin coordenadas válidas
    """
    # Filtrar por período
    df = df_raw[
        (df_raw['mes'] == mes) &
        (df_raw['año'] == año)
    ].copy()

    if df.empty:
        return df

    # Detectar si el CSV está pre-agregado o es datos crudos
    if 'total_activos' in df.columns:
        # CSV pre-agregado: ya tiene el conteo listo
        df.rename(columns={'total_activos': 'Total_activos'}, inplace=True)
    elif 'empleado' in df.columns:
        # CSV crudo: necesita agregar igual que la query SQL original
        group_cols = [
            col for col in [
                'almacen', 'nom_oficio', 'ccosto', 'gestor',
                'tipo_tienda', 'zona', 'longitud', 'latitud', 'mes', 'año'
            ] if col in df.columns
        ]
        df = (
            df.groupby(group_cols, dropna=False)
              .agg(Total_activos=('empleado', 'nunique'))
              .reset_index()
        )
    else:
        st.error(
            "❌ El CSV no tiene ni columna 'empleado' ni 'total_activos'.\n"
            "Necesita una de las dos para funcionar."
        )
        st.stop()

    # Generar columna Fecha
    df['Fecha'] = df['mes'].map(MES_A_NUMERO).astype(str) + '/' + df['año'].astype(str)

    # Eliminar filas sin coordenadas
    df = df.dropna(subset=['latitud', 'longitud'])

    return df


@st.cache_data(ttl=600, show_spinner=False)
def load_geojson(file_path=None):
    """Carga archivo GeoJSON o Shapefile para capas adicionales en el mapa"""
    try:
        if file_path is None:
            geo_path = Path(GEOJSON_PATH)
            if not geo_path.exists():
                return None
            geojson_files = list(geo_path.glob('*.geojson'))
            shp_files    = list(geo_path.glob('*.shp'))

            if geojson_files:
                file_path = geojson_files[0]
            elif shp_files:
                file_path = shp_files[0]
            else:
                return None

        file_path = Path(file_path)
        gdf = gpd.read_file(file_path)
        return gdf

    except Exception as e:
        st.warning(f"No se pudieron cargar capas geográficas: {str(e)}")
        return None


# ==========================
# HEADER PRINCIPAL
# ==========================
st.markdown("""
<div class="main-header">
    <h1>📊 Dashboard Obeya Comercial 2026</h1>
    <p>🎯 Análisis Estratégico de Cobertura Geográfica</p>
</div>
""", unsafe_allow_html=True)

# ==========================
# CARGAR CSV (una sola vez, cacheado)
# ==========================
df_raw = load_csv()

# ==========================
# SIDEBAR CON FILTROS
# ==========================
with st.sidebar:
    st.markdown("### 🎯 Panel de Control")
    st.markdown("---")

    # Filtros temporales
    st.markdown("#### 📅 Período")

    meses = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO',
             'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']
    mes = st.selectbox("Mes", meses, index=0, key="mes_select")

    # Años disponibles según los datos del CSV
    años_disponibles = sorted(df_raw['año'].dropna().unique().tolist(), reverse=True)
    año = st.selectbox("Año", años_disponibles, index=0, key="año_select")

    # Procesar datos para el período seleccionado
    with st.spinner('🔄 Procesando datos...'):
        df = process_data(df_raw, mes, int(año))

    if df.empty:
        st.warning(f"⚠️ No hay datos para **{mes} {año}**. Selecciona otro período.")
        st.stop()

    # Resumen en sidebar
    st.markdown("---")
    st.markdown("#### 📊 Resumen General")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Registros", f"{len(df):,}")
    with col2:
        st.metric("Tiendas", f"{df['almacen'].nunique()}")

    st.metric("👥 Total Activos", f"{df['Total_activos'].sum():,}")

    # Filtros adicionales
    st.markdown("---")
    st.markdown("#### 🔍 Filtros Avanzados")

    isocronas = ['TODAS'] + sorted(df['zona'].dropna().unique().tolist())
    isocrona_selected = st.selectbox("🌍 Isocrona", isocronas, key="isocrona_select")

    gestores = ['TODOS'] + sorted(df['gestor'].dropna().unique().tolist())
    gestor_selected = st.selectbox("👨‍💼 Gestor", gestores, key="gestor_select")

    tipos = ['TODOS'] + sorted(df['tipo_tienda'].dropna().unique().tolist())
    tipo_selected = st.selectbox("🏬 Tipo de Tienda", tipos, key="tipo_select")

    # Rango de activos
    st.markdown("#### 👥 Rango de Activos")
    min_activos = int(df['Total_activos'].min())
    max_activos = int(df['Total_activos'].max())
    rango_activos = st.slider(
        "Filtrar por cantidad",
        min_value=min_activos,
        max_value=max_activos,
        value=(min_activos, max_activos),
        key="rango_activos"
    )

    # Reset
    st.markdown("---")
    if st.button("🔄 Resetear Filtros", use_container_width=True):
        st.rerun()

    # Exportación
    st.markdown("---")
    st.markdown("#### 💾 Exportar Datos")

    @st.cache_data
    def convert_df_to_csv(df):
        return df.to_csv(index=False).encode('utf-8')

    csv_export = convert_df_to_csv(df)
    st.download_button(
        label="📥 Descargar CSV",
        data=csv_export,
        file_name=f"Obeya_Comercial_{mes}_{año}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

# ==========================
# APLICAR FILTROS
# ==========================
df_filtered = df.copy()

if isocrona_selected != 'TODAS':
    df_filtered = df_filtered[df_filtered['zona'] == isocrona_selected]

if gestor_selected != 'TODOS':
    df_filtered = df_filtered[df_filtered['gestor'] == gestor_selected]

if tipo_selected != 'TODOS':
    df_filtered = df_filtered[df_filtered['tipo_tienda'] == tipo_selected]

df_filtered = df_filtered[
    (df_filtered['Total_activos'] >= rango_activos[0]) &
    (df_filtered['Total_activos'] <= rango_activos[1])
]

if len(df_filtered) == 0:
    st.warning("⚠️ No hay datos para los filtros seleccionados. Ajusta los parámetros en el panel lateral.")
    st.stop()

# ==========================
# KPIs PRINCIPALES
# ==========================
st.markdown("### 📈 Indicadores Clave de Desempeño")

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_tiendas = df_filtered['almacen'].nunique()
    porcentaje = (total_tiendas / max(df['almacen'].nunique(), 1) * 100)
    delta_color = "normal" if porcentaje >= 80 else "inverse"
    st.metric(
        label="🏪 Cobertura de Tiendas",
        value=f"{total_tiendas:,}",
        delta=f"{porcentaje:.1f}% del total",
        delta_color=delta_color
    )

with col2:
    total_activos  = int(df_filtered['Total_activos'].sum())
    total_original = int(df['Total_activos'].sum())
    porcentaje = (total_activos / max(total_original, 1) * 100)
    st.metric(
        label="👥 Dotación Total",
        value=f"{total_activos:,}",
        delta=f"{porcentaje:.1f}% del total"
    )

with col3:
    promedio   = df_filtered['Total_activos'].mean()
    mediana    = df_filtered['Total_activos'].median()
    diferencia = ((promedio - mediana) / max(mediana, 1) * 100)
    st.metric(
        label="📊 Promedio por Tienda",
        value=f"{promedio:.1f}",
        delta=f"{diferencia:+.1f}% vs mediana"
    )

with col4:
    isocronas_agrupadas = df_filtered.groupby('zona')['Total_activos'].sum()
    if not isocronas_agrupadas.empty:
        top_isocrona = isocronas_agrupadas.idxmax()
        top_valor    = int(isocronas_agrupadas.max())
        st.metric(
            label="🎯 Isocrona Líder",
            value=top_isocrona,
            delta=f"{top_valor:,} activos"
        )
    else:
        st.metric(label="🎯 Isocrona Líder", value="Sin datos", delta="0")

st.markdown("---")

# ==========================
# ANÁLISIS POR ISOCRONA
# ==========================
st.markdown("### 📈 Análisis por Isocrona")

col1, col2 = st.columns(2)

with col1:
    isocronas_data = df_filtered.groupby('zona')['Total_activos'].sum().reset_index()
    isocronas_data = isocronas_data.sort_values('Total_activos', ascending=False)

    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        x=isocronas_data['zona'],
        y=isocronas_data['Total_activos'],
        text=isocronas_data['Total_activos'],
        texttemplate='%{text:,}',
        textposition='outside',
        marker=dict(
            color=isocronas_data['Total_activos'],
            colorscale=[[0, COLORS['accent']], [1, COLORS['primary']]],
            line=dict(color=COLORS['primary'], width=1.5)
        ),
        hovertemplate='<b>%{x}</b><br>Activos: %{y:,}<extra></extra>'
    ))
    fig1.update_layout(
        title={'text': '📍 Distribución de Activos por Isocrona',
               'font': {'size': 16, 'color': COLORS['dark'], 'family': 'Roboto'}},
        xaxis_title="Isocrona",
        yaxis_title="Total Activos",
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Roboto', size=12),
        hovermode='x',
        height=400
    )
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    tipo_data = df_filtered.groupby('tipo_tienda')['Total_activos'].sum().reset_index()

    fig2 = go.Figure()
    fig2.add_trace(go.Pie(
        labels=tipo_data['tipo_tienda'],
        values=tipo_data['Total_activos'],
        hole=0.4,
        marker=dict(colors=CHART_COLORS),
        textinfo='label+percent+value',
        texttemplate='<b>%{label}</b><br>%{value:,}<br>(%{percent})',
        hovertemplate='<b>%{label}</b><br>Activos: %{value:,}<br>Porcentaje: %{percent}<extra></extra>'
    ))
    fig2.update_layout(
        title={'text': '🏬 Distribución por Tipo de Tienda',
               'font': {'size': 16, 'color': COLORS['dark'], 'family': 'Roboto'}},
        font=dict(family='Roboto', size=12),
        height=400,
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5)
    )
    st.plotly_chart(fig2, use_container_width=True)

# Análisis comparativo gestor-isocrona
st.markdown("#### 📊 Análisis Comparativo por Gestor e Isocrona")

gestor_isocrona = df_filtered.groupby(['gestor', 'zona'])['Total_activos'].sum().reset_index()

fig3 = px.bar(
    gestor_isocrona,
    x='gestor',
    y='Total_activos',
    color='zona',
    title='Distribución de Activos por Gestor e Isocrona',
    color_discrete_sequence=CHART_COLORS,
    text='Total_activos',
    barmode='stack'
)
fig3.update_traces(texttemplate='%{text:,}', textposition='inside')
fig3.update_layout(
    xaxis_title="Gestor",
    yaxis_title="Total Activos",
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(family='Roboto', size=12),
    height=400,
    legend_title_text='Isocrona'
)
st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")

# ==========================
# TOP PERFORMERS
# ==========================
st.markdown("### 🏆 Top Personal Activo por Tienda")

col1, col2 = st.columns([2, 1])

with col1:
    n_top = min(15, len(df_filtered))
    top_tiendas = df_filtered.nlargest(n_top, 'Total_activos')[
        ['almacen', 'zona', 'gestor', 'tipo_tienda', 'Total_activos']
    ].copy()
    top_tiendas = top_tiendas.sort_values('Total_activos', ascending=True)

    fig4 = go.Figure()
    fig4.add_trace(go.Bar(
        y=top_tiendas['almacen'],
        x=top_tiendas['Total_activos'],
        orientation='h',
        text=top_tiendas['Total_activos'],
        texttemplate='%{text:,}',
        textposition='outside',
        marker=dict(
            color=top_tiendas['Total_activos'],
            colorscale=[[0, COLORS['accent']], [1, COLORS['success']]],
            line=dict(color=COLORS['primary'], width=1)
        ),
        customdata=top_tiendas[['zona', 'gestor', 'tipo_tienda']],
        hovertemplate='<b>%{y}</b><br>Activos: %{x:,}<br>Isocrona: %{customdata[0]}<br>Gestor: %{customdata[1]}<extra></extra>'
    ))
    fig4.update_layout(
        title={'text': f'🏆 Top {n_top} Tiendas con Mayor Dotación',
               'font': {'size': 16, 'color': COLORS['dark'], 'family': 'Roboto'}},
        xaxis_title="Total Activos",
        yaxis_title="",
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Roboto', size=11),
        height=500,
        margin=dict(l=150)
    )
    st.plotly_chart(fig4, use_container_width=True)

with col2:
    st.markdown("#### 📊 Estadísticas Clave")

    stats_data = {
        'Métrica': ['🔻 Mínimo', '📊 Mediana', '📈 Promedio', '🔺 Máximo', '💯 Total', '📉 Desv. Std'],
        'Valor': [
            f"{df_filtered['Total_activos'].min():.0f}",
            f"{df_filtered['Total_activos'].median():.1f}",
            f"{df_filtered['Total_activos'].mean():.1f}",
            f"{df_filtered['Total_activos'].max():.0f}",
            f"{df_filtered['Total_activos'].sum():,.0f}",
            f"{df_filtered['Total_activos'].std():.1f}"
        ]
    }
    stats_df = pd.DataFrame(stats_data)

    st.dataframe(
        stats_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Métrica": st.column_config.TextColumn("Métrica", width="medium"),
            "Valor":   st.column_config.TextColumn("Valor",   width="small")
        }
    )

    st.markdown("#### 📊 Distribución")
    fig5 = go.Figure()
    fig5.add_trace(go.Histogram(
        x=df_filtered['Total_activos'],
        nbinsx=20,
        marker=dict(color=COLORS['primary'], line=dict(color='white', width=1)),
        hovertemplate='Rango: %{x}<br>Frecuencia: %{y}<extra></extra>'
    ))
    fig5.update_layout(
        xaxis_title="Activos",
        yaxis_title="Frecuencia",
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Roboto', size=10),
        height=250,
        margin=dict(l=20, r=20, t=20, b=40)
    )
    st.plotly_chart(fig5, use_container_width=True)

# ==========================
# VISTA GEOGRÁFICA
# ==========================
st.markdown("### 🗺️ Vista Geográfica")

col_map, col_config = st.columns([4, 1])

with col_config:
    st.markdown("#### ⚙️ Configuración")

    tamaño_base = st.slider("Tamaño base", min_value=3, max_value=15, value=6, key="tamaño_mapa")
    factor_escala = st.slider("Escala", min_value=0.1, max_value=1.5, value=0.4, step=0.1, key="escala_mapa")

    st.markdown("---")

    mostrar_capa = st.checkbox("Mostrar capa geográfica", value=False)
    geo_files = []

    if mostrar_capa:
        try:
            geo_path = Path(GEOJSON_PATH)
            if geo_path.exists():
                geo_files = list(geo_path.glob('*.geojson')) + list(geo_path.glob('*.shp'))
        except:
            pass

        if geo_files:
            selected_geo = st.selectbox(
                "Archivo",
                options=[f.name for f in geo_files],
                key="geo_file"
            )
        else:
            st.caption("No hay archivos geográficos en la carpeta.")

    st.markdown("---")
    st.markdown("**📍 Estadísticas**")
    st.caption(f"Puntos: {len(df_filtered)}")
    st.caption(f"Isocronas: {df_filtered['zona'].nunique()}")

with col_map:
    try:
        df_mapa = df_filtered.dropna(subset=['latitud', 'longitud']).copy()

        if len(df_mapa) == 0:
            st.error("❌ No hay coordenadas válidas para mostrar en el mapa.")
        else:
            centro_lat = df_mapa['latitud'].mean()
            centro_lon = df_mapa['longitud'].mean()

            m = folium.Map(
                location=[centro_lat, centro_lon],
                zoom_start=11,
                tiles='CartoDB positron',
                control_scale=True,
                prefer_canvas=True
            )

            # Capa geográfica opcional
            if mostrar_capa and geo_files:
                try:
                    selected_file = [f for f in geo_files if f.name == selected_geo][0]
                    gdf = load_geojson(selected_file)
                    if gdf is not None:
                        folium.GeoJson(
                            gdf,
                            name='Capa Geográfica',
                            style_function=lambda x: {
                                'fillColor': '#7fa8e0',
                                'color': '#1e3c72',
                                'weight': 2,
                                'fillOpacity': 0.2
                            }
                        ).add_to(m)
                except Exception as e:
                    st.warning(f"No se pudo cargar la capa: {str(e)}")

            # Colores por isocrona
            isocronas_unicas = df_mapa['zona'].unique()
            colores_isocronas = {
                isocrona: CHART_COLORS[i % len(CHART_COLORS)]
                for i, isocrona in enumerate(isocronas_unicas)
            }

            # Marcadores
            for isocrona in isocronas_unicas:
                df_isocrona = df_mapa[df_mapa['zona'] == isocrona]

                for _, row in df_isocrona.iterrows():
                    radio = max(tamaño_base, row['Total_activos'] * factor_escala)
                    color = colores_isocronas.get(isocrona, '#1e3c72')

                    popup_html = f"""
                    <div style="font-family: 'Roboto', Arial; max-width: 280px;">
                        <div style="background: linear-gradient(135deg, {color} 0%, {COLORS['secondary']} 100%);
                                    color: white; padding: 12px; border-radius: 8px 8px 0 0;">
                            <h4 style="margin: 0; font-size: 15px; font-weight: 600;">{row['almacen']}</h4>
                        </div>
                        <div style="padding: 12px; background: white; border-radius: 0 0 8px 8px;">
                            <table style="width: 100%; font-size: 13px;">
                                <tr><td style="padding: 4px 0;"><b>📍 Isocrona:</b></td><td>{row['zona']}</td></tr>
                                <tr><td style="padding: 4px 0;"><b>👨‍💼 Gestor:</b></td><td>{row['gestor']}</td></tr>
                                <tr><td style="padding: 4px 0;"><b>🏬 Tipo:</b></td><td>{row['tipo_tienda']}</td></tr>
                                <tr><td style="padding: 4px 0;"><b>👥 Activos:</b></td>
                                    <td style="color: {COLORS['primary']}; font-weight: bold; font-size: 15px;">{row['Total_activos']}</td></tr>
                                <tr><td style="padding: 4px 0;"><b>📅 Período:</b></td><td>{row['mes']} {row['año']}</td></tr>
                            </table>
                        </div>
                    </div>
                    """

                    folium.CircleMarker(
                        location=[row['latitud'], row['longitud']],
                        radius=radio,
                        popup=folium.Popup(popup_html, max_width=320),
                        color=color,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.7,
                        weight=2,
                        tooltip=f"<b>{row['almacen']}</b><br>{row['Total_activos']} activos"
                    ).add_to(m)

            folium.LayerControl().add_to(m)
            st_folium(m, width=None, height=600, returned_objects=[])
            st.success(f"✅ Mapa cargado: {len(df_mapa)} ubicaciones de {len(isocronas_unicas)} isocronas")

    except Exception as e:
        st.error(f"❌ Error al crear el mapa: {str(e)}")

st.markdown("---")

# ==========================
# TABLA DE DATOS DETALLADA
# ==========================
st.markdown("### 📋 Datos Detallados por Tienda")

col1, col2, col3 = st.columns(3)

with col1:
    columnas_disponibles = ['almacen', 'zona', 'gestor', 'tipo_tienda', 'nom_oficio', 'Total_activos', 'ccosto', 'Fecha']
    columnas_existentes  = [col for col in columnas_disponibles if col in df_filtered.columns]
    mostrar_columnas = st.multiselect(
        "Seleccionar columnas",
        options=columnas_existentes,
        default=[c for c in ['almacen', 'zona', 'gestor', 'tipo_tienda', 'Total_activos'] if c in columnas_existentes],
        key="columnas_tabla"
    )

with col2:
    registros_mostrar = st.selectbox(
        "Registros por página",
        options=[10, 25, 50, 100, "Todos"],
        index=1,
        key="registros_tabla"
    )

with col3:
    opciones_ordenar = [c for c in ['Total_activos', 'almacen', 'zona', 'gestor'] if c in df_filtered.columns]
    ordenar_por = st.selectbox("Ordenar por", options=opciones_ordenar, index=0, key="ordenar_tabla")
    orden_ascendente = st.checkbox("Orden ascendente", value=False, key="orden_tabla")

if mostrar_columnas:
    tabla_data = df_filtered[mostrar_columnas].sort_values(ordenar_por, ascending=orden_ascendente)

    if registros_mostrar != "Todos":
        tabla_data = tabla_data.head(int(registros_mostrar))

    column_config = {
        "almacen":        st.column_config.TextColumn("🏪 Tienda",    width="medium"),
        "zona":           st.column_config.TextColumn("📍 Isocrona",  width="small"),
        "gestor":         st.column_config.TextColumn("👨‍💼 Gestor",   width="medium"),
        "tipo_tienda":    st.column_config.TextColumn("🏬 Tipo",      width="small"),
        "Total_activos":  st.column_config.NumberColumn("👥 Activos", format="%d", width="small"),
        "ccosto":         st.column_config.TextColumn("💼 C.Costo",   width="small"),
        "Fecha":          st.column_config.TextColumn("📅 Período",   width="small"),
        "nom_oficio":     st.column_config.TextColumn("💼 Oficio",    width="medium")
    }

    st.dataframe(
        tabla_data,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        height=400
    )

    st.caption(f"📊 Mostrando {len(tabla_data):,} de {len(df_filtered):,} registros filtrados | Total general: {len(df):,} registros")

# ==========================
# FOOTER
# ==========================
st.markdown("---")
st.markdown(f"""
<div class="footer-info">
    <p style="margin: 0; font-size: 0.95rem; color: {COLORS['dark']};">
        <b>📊 Dashboard Obeya Comercial 2026</b><br>
        Generado: {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')} |
        Período: <b>{mes} {año}</b> |
        Registros procesados: <b>{len(df_filtered):,}</b> de <b>{len(df):,}</b>
    </p>
    <p style="margin-top: 0.5rem; font-size: 0.85rem; color: #666;">
        Arquitectura
    </p>
</div>
""", unsafe_allow_html=True)
