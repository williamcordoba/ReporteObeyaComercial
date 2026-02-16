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
    'gradient_end': '#2a5298',
    'retiros': '#dc3545',      # Rojo para retiros
    'ausentismo': '#ffc107',   # Amarillo para ausentismo
    'accidentes': '#ff6b6b'    # Rojo claro para accidentes
}

CHART_COLORS = ['#1e3c72', '#2a5298', '#7fa8e0', '#5080c0', '#3060a0', '#406db8']

# ==========================
# CONFIGURACIÓN DE RUTAS
# ==========================
import os

CSV_PATH = os.environ.get('CSV_PATH', 'empleados_activos.csv')
GEOJSON_PATH = os.environ.get('GEODATA_PATH', 'geodata')

# ==========================
# ESTILOS CSS PERSONALIZADOS
# ==========================
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #1e3c72;
    }
    
    .alert-card {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .danger-card {
        background: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
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
    """Carga el CSV con todas las métricas"""
    try:
        df = pd.read_csv(CSV_PATH)
        df.columns = df.columns.str.strip().str.lower()
        
        # Mapeo de columnas
        rename_map = {}
        if 'logitud' in df.columns and 'longitud' not in df.columns:
            rename_map['logitud'] = 'longitud'
        if 'ano' in df.columns and 'año' not in df.columns:
            rename_map['ano'] = 'año'
        
        if rename_map:
            df.rename(columns=rename_map, inplace=True)
        
        # Convertir tipos
        df['latitud'] = pd.to_numeric(df['latitud'], errors='coerce')
        df['longitud'] = pd.to_numeric(df['longitud'], errors='coerce')
        df['año'] = pd.to_numeric(df['año'], errors='coerce').astype(int)
        
        # Nuevas columnas numéricas
        df['total_retiros'] = pd.to_numeric(df.get('total_retiros', 0), errors='coerce').fillna(0)
        df['total_ausentismo'] = pd.to_numeric(df.get('total_ausentismo', 0), errors='coerce').fillna(0)
        df['total_accidentes'] = pd.to_numeric(df.get('total_accidentes', 0), errors='coerce').fillna(0)
        
        # Normalizar texto
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
    """Procesa y filtra los datos por período"""
    df = df_raw[
        (df_raw['mes'] == mes) & 
        (df_raw['año'] == año)
    ].copy()
    
    if df.empty:
        return df
    
    # Si no tiene total_activos, agregarlo
    if 'total_activos' not in df.columns and 'empleado' in df.columns:
        group_cols = [
            col for col in [
                'almacen', 'nom_oficio', 'ccosto', 'gestor', 'tipo_tienda',
                'zona', 'longitud', 'latitud', 'mes', 'año'
            ] if col in df.columns
        ]
        
        df = (
            df.groupby(group_cols, dropna=False)
            .agg(
                total_activos=('empleado', 'nunique'),
                total_retiros=('total_retiros', 'sum'),
                total_ausentismo=('total_ausentismo', 'sum'),
                total_accidentes=('total_accidentes', 'sum')
            )
            .reset_index()
        )
    
    # Generar columna Fecha
    df['fecha'] = df['mes'].map(MES_A_NUMERO).astype(str) + '/' + df['año'].astype(str)
    
    # Calcular métricas derivadas
    df['tasa_rotacion'] = (df['total_retiros'] / df['total_activos'] * 100).fillna(0)
    df['tasa_ausentismo'] = (df['total_ausentismo'] / df['total_activos'] * 100).fillna(0)
    df['tasa_accidentalidad'] = (df['total_accidentes'] / df['total_activos'] * 100).fillna(0)
    
    # Eliminar filas sin coordenadas
    df = df.dropna(subset=['latitud', 'longitud'])
    
    return df

@st.cache_data(ttl=600, show_spinner=False)
def load_geojson(file_path=None):
    """Carga archivo GeoJSON o Shapefile"""
    try:
        if file_path is None:
            geo_path = Path(GEOJSON_PATH)
            if not geo_path.exists():
                return None
            
            geojson_files = list(geo_path.glob('*.geojson'))
            shp_files = list(geo_path.glob('*.shp'))
            
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
    <h3>🎯 Análisis Estratégico de Cobertura Geográfica y Gestión de Personal</h3>
</div>
""", unsafe_allow_html=True)

# ==========================
# CARGAR DATOS
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
    
    años_disponibles = sorted(df_raw['año'].dropna().unique().tolist(), reverse=True)
    año = st.selectbox("Año", años_disponibles, index=0, key="año_select")
    
    # Procesar datos
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
    
    st.metric("👥 Total Activos", f"{int(df['total_activos'].sum()):,}")
    
    # Métricas críticas
    st.markdown("---")
    st.markdown("#### ⚠️ Indicadores Críticos")
    st.metric("🚪 Total Retiros", f"{int(df['total_retiros'].sum()):,}", 
              delta=f"{df['tasa_rotacion'].mean():.1f}% rotación", delta_color="inverse")
    st.metric("😷 Total Ausentismo", f"{int(df['total_ausentismo'].sum()):,}",
              delta=f"{df['tasa_ausentismo'].mean():.1f}% tasa", delta_color="inverse")
    st.metric("🚑 Total Accidentes", f"{int(df['total_accidentes'].sum()):,}",
              delta=f"{df['tasa_accidentalidad'].mean():.1f}% tasa", delta_color="inverse")
    
    # Filtros adicionales
    st.markdown("---")
    st.markdown("#### 🔍 Filtros Avanzados")
    
    isocronas = ['TODAS'] + sorted(df['zona'].dropna().unique().tolist())
    isocrona_selected = st.selectbox("🌍 Isocrona", isocronas, key="isocrona_select")
    
    gestores = ['TODOS'] + sorted(df['gestor'].dropna().unique().tolist())
    gestor_selected = st.selectbox("👨‍💼 Gestor", gestores, key="gestor_select")
    
    tipos = ['TODOS'] + sorted(df['tipo_tienda'].dropna().unique().tolist())
    tipo_selected = st.selectbox("🏬 Tipo de Tienda", tipos, key="tipo_select")
    
    # Filtros de alertas
    st.markdown("#### 🚨 Filtros de Alerta")
    
    mostrar_alertas = st.checkbox("🔔 Solo tiendas con alertas", value=False)
    
    if mostrar_alertas:
        umbral_rotacion = st.slider("Umbral rotación (%)", 0, 50, 10, key="umbral_rot")
        umbral_ausentismo = st.slider("Umbral ausentismo (%)", 0, 50, 15, key="umbral_aus")
        umbral_accidentes = st.slider("Umbral accidentes (%)", 0, 20, 5, key="umbral_acc")
    
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

if mostrar_alertas:
    df_filtered = df_filtered[
        (df_filtered['tasa_rotacion'] >= umbral_rotacion) |
        (df_filtered['tasa_ausentismo'] >= umbral_ausentismo) |
        (df_filtered['tasa_accidentalidad'] >= umbral_accidentes)
    ]

if len(df_filtered) == 0:
    st.warning("⚠️ No hay datos para los filtros seleccionados. Ajusta los parámetros en el panel lateral.")
    st.stop()

# ==========================
# KPIs PRINCIPALES
# ==========================
st.markdown("### 📈 Indicadores Clave de Desempeño")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_activos = int(df_filtered['total_activos'].sum())
    total_original = int(df['total_activos'].sum())
    porcentaje = (total_activos / max(total_original, 1) * 100)
    st.metric(
        label="👥 Dotación Total",
        value=f"{total_activos:,}",
        delta=f"{porcentaje:.1f}% del total"
    )

with col2:
    total_retiros = int(df_filtered['total_retiros'].sum())
    tasa_global_retiros = (total_retiros / max(total_activos, 1) * 100)
    st.metric(
        label="🚪 Retiros",
        value=f"{total_retiros:,}",
        delta=f"{tasa_global_retiros:.1f}% rotación",
        delta_color="inverse"
    )

with col3:
    total_ausentismo = int(df_filtered['total_ausentismo'].sum())
    tasa_global_ausentismo = (total_ausentismo / max(total_activos, 1) * 100)
    st.metric(
        label="😷 Ausentismo",
        value=f"{total_ausentismo:,}",
        delta=f"{tasa_global_ausentismo:.1f}% tasa",
        delta_color="inverse"
    )

with col4:
    total_accidentes = int(df_filtered['total_accidentes'].sum())
    tasa_global_accidentes = (total_accidentes / max(total_activos, 1) * 100)
    st.metric(
        label="🚑 Accidentes",
        value=f"{total_accidentes:,}",
        delta=f"{tasa_global_accidentes:.1f}% tasa",
        delta_color="inverse"
    )

with col5:
    total_tiendas = df_filtered['almacen'].nunique()
    tiendas_alertas = len(df_filtered[
        (df_filtered['tasa_rotacion'] >= 10) |
        (df_filtered['tasa_ausentismo'] >= 15) |
        (df_filtered['tasa_accidentalidad'] >= 5)
    ])
    st.metric(
        label="🚨 Tiendas con Alertas",
        value=f"{tiendas_alertas}",
        delta=f"{(tiendas_alertas/max(total_tiendas,1)*100):.1f}% del total",
        delta_color="inverse"
    )

st.markdown("---")

# ==========================
# ANÁLISIS COMPARATIVO
# ==========================
st.markdown("### 📊 Análisis Comparativo de Indicadores")

tab1, tab2, tab3, tab4 = st.tabs(["📈 General", "🚪 Retiros", "😷 Ausentismo", "🚑 Accidentes"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        # Comparativa por isocrona
        isocrona_metrics = df_filtered.groupby('zona').agg({
            'total_activos': 'sum',
            'total_retiros': 'sum',
            'total_ausentismo': 'sum',
            'total_accidentes': 'sum'
        }).reset_index()
        
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(name='👥 Activos', x=isocrona_metrics['zona'], 
                              y=isocrona_metrics['total_activos'], marker_color=COLORS['primary']))
        fig1.add_trace(go.Bar(name='🚪 Retiros', x=isocrona_metrics['zona'], 
                              y=isocrona_metrics['total_retiros'], marker_color=COLORS['retiros']))
        fig1.add_trace(go.Bar(name='😷 Ausentismo', x=isocrona_metrics['zona'], 
                              y=isocrona_metrics['total_ausentismo'], marker_color=COLORS['ausentismo']))
        fig1.add_trace(go.Bar(name='🚑 Accidentes', x=isocrona_metrics['zona'], 
                              y=isocrona_metrics['total_accidentes'], marker_color=COLORS['accidentes']))
        
        fig1.update_layout(
            title='Métricas por Isocrona',
            xaxis_title="Isocrona",
            yaxis_title="Total",
            barmode='group',
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=400
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Tasas promedio por tipo de tienda
        tipo_metrics = df_filtered.groupby('tipo_tienda').agg({
            'tasa_rotacion': 'mean',
            'tasa_ausentismo': 'mean',
            'tasa_accidentalidad': 'mean'
        }).reset_index()
        
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name='% Rotación', x=tipo_metrics['tipo_tienda'], 
                              y=tipo_metrics['tasa_rotacion'], marker_color=COLORS['retiros']))
        fig2.add_trace(go.Bar(name='% Ausentismo', x=tipo_metrics['tipo_tienda'], 
                              y=tipo_metrics['tasa_ausentismo'], marker_color=COLORS['ausentismo']))
        fig2.add_trace(go.Bar(name='% Accidentalidad', x=tipo_metrics['tipo_tienda'], 
                              y=tipo_metrics['tasa_accidentalidad'], marker_color=COLORS['accidentes']))
        
        fig2.update_layout(
            title='Tasas Promedio por Tipo de Tienda',
            xaxis_title="Tipo de Tienda",
            yaxis_title="Porcentaje (%)",
            barmode='group',
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=400
        )
        st.plotly_chart(fig2, use_container_width=True)

with tab2:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Top tiendas con mayor rotación
        top_rotacion = df_filtered.nlargest(15, 'tasa_rotacion')[
            ['almacen', 'zona', 'total_activos', 'total_retiros', 'tasa_rotacion']
        ].copy()
        
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(
            y=top_rotacion['almacen'],
            x=top_rotacion['tasa_rotacion'],
            orientation='h',
            text=top_rotacion['tasa_rotacion'].round(1),
            texttemplate='%{text}%',
            textposition='outside',
            marker=dict(
                color=top_rotacion['tasa_rotacion'],
                colorscale=[[0, COLORS['warning']], [1, COLORS['danger']]],
                line=dict(color=COLORS['retiros'], width=1)
            ),
            customdata=top_rotacion[['total_activos', 'total_retiros', 'zona']],
            hovertemplate='<b>%{y}</b><br>Rotación: %{x:.1f}%<br>Activos: %{customdata[0]}<br>Retiros: %{customdata[1]}<br>Zona: %{customdata[2]}<extra></extra>'
        ))
        
        fig3.update_layout(
            title='🚪 Top 15 Tiendas con Mayor Tasa de Rotación',
            xaxis_title="Tasa de Rotación (%)",
            yaxis_title="",
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=500,
            margin=dict(l=150)
        )
        st.plotly_chart(fig3, use_container_width=True)
    
    with col2:
        st.markdown("#### 📊 Estadísticas de Rotación")
        st.metric("Promedio", f"{df_filtered['tasa_rotacion'].mean():.1f}%")
        st.metric("Mediana", f"{df_filtered['tasa_rotacion'].median():.1f}%")
        st.metric("Máxima", f"{df_filtered['tasa_rotacion'].max():.1f}%")
        st.metric("Tiendas >10%", f"{len(df_filtered[df_filtered['tasa_rotacion'] >= 10])}")
        
        # Distribución
        fig_dist = go.Figure()
        fig_dist.add_trace(go.Histogram(
            x=df_filtered['tasa_rotacion'],
            nbinsx=20,
            marker_color=COLORS['retiros']
        ))
        fig_dist.update_layout(
            title="Distribución Tasa Rotación",
            xaxis_title="Tasa (%)",
            yaxis_title="Frecuencia",
            height=250,
            margin=dict(l=20, r=20, t=40, b=40)
        )
        st.plotly_chart(fig_dist, use_container_width=True)

with tab3:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Top tiendas con mayor ausentismo
        top_ausentismo = df_filtered.nlargest(15, 'tasa_ausentismo')[
            ['almacen', 'zona', 'total_activos', 'total_ausentismo', 'tasa_ausentismo']
        ].copy()
        
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(
            y=top_ausentismo['almacen'],
            x=top_ausentismo['tasa_ausentismo'],
            orientation='h',
            text=top_ausentismo['tasa_ausentismo'].round(1),
            texttemplate='%{text}%',
            textposition='outside',
            marker=dict(
                color=top_ausentismo['tasa_ausentismo'],
                colorscale=[[0, '#fff3cd'], [1, COLORS['warning']]],
                line=dict(color=COLORS['warning'], width=1)
            ),
            customdata=top_ausentismo[['total_activos', 'total_ausentismo', 'zona']],
            hovertemplate='<b>%{y}</b><br>Ausentismo: %{x:.1f}%<br>Activos: %{customdata[0]}<br>Ausentes: %{customdata[1]}<br>Zona: %{customdata[2]}<extra></extra>'
        ))
        
        fig4.update_layout(
            title='😷 Top 15 Tiendas con Mayor Tasa de Ausentismo',
            xaxis_title="Tasa de Ausentismo (%)",
            yaxis_title="",
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=500,
            margin=dict(l=150)
        )
        st.plotly_chart(fig4, use_container_width=True)
    
    with col2:
        st.markdown("#### 📊 Estadísticas de Ausentismo")
        st.metric("Promedio", f"{df_filtered['tasa_ausentismo'].mean():.1f}%")
        st.metric("Mediana", f"{df_filtered['tasa_ausentismo'].median():.1f}%")
        st.metric("Máxima", f"{df_filtered['tasa_ausentismo'].max():.1f}%")
        st.metric("Tiendas >15%", f"{len(df_filtered[df_filtered['tasa_ausentismo'] >= 15])}")
        
        # Distribución
        fig_dist = go.Figure()
        fig_dist.add_trace(go.Histogram(
            x=df_filtered['tasa_ausentismo'],
            nbinsx=20,
            marker_color=COLORS['ausentismo']
        ))
        fig_dist.update_layout(
            title="Distribución Tasa Ausentismo",
            xaxis_title="Tasa (%)",
            yaxis_title="Frecuencia",
            height=250,
            margin=dict(l=20, r=20, t=40, b=40)
        )
        st.plotly_chart(fig_dist, use_container_width=True)

with tab4:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Top tiendas con mayor accidentalidad
        top_accidentes = df_filtered.nlargest(15, 'tasa_accidentalidad')[
            ['almacen', 'zona', 'total_activos', 'total_accidentes', 'tasa_accidentalidad']
        ].copy()
        
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(
            y=top_accidentes['almacen'],
            x=top_accidentes['tasa_accidentalidad'],
            orientation='h',
            text=top_accidentes['tasa_accidentalidad'].round(1),
            texttemplate='%{text}%',
            textposition='outside',
            marker=dict(
                color=top_accidentes['tasa_accidentalidad'],
                colorscale=[[0, '#ffcccc'], [1, COLORS['accidentes']]],
                line=dict(color=COLORS['accidentes'], width=1)
            ),
            customdata=top_accidentes[['total_activos', 'total_accidentes', 'zona']],
            hovertemplate='<b>%{y}</b><br>Accidentalidad: %{x:.1f}%<br>Activos: %{customdata[0]}<br>Accidentes: %{customdata[1]}<br>Zona: %{customdata[2]}<extra></extra>'
        ))
        
        fig5.update_layout(
            title='🚑 Top 15 Tiendas con Mayor Tasa de Accidentalidad',
            xaxis_title="Tasa de Accidentalidad (%)",
            yaxis_title="",
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=500,
            margin=dict(l=150)
        )
        st.plotly_chart(fig5, use_container_width=True)
    
    with col2:
        st.markdown("#### 📊 Estadísticas de Accidentalidad")
        st.metric("Promedio", f"{df_filtered['tasa_accidentalidad'].mean():.1f}%")
        st.metric("Mediana", f"{df_filtered['tasa_accidentalidad'].median():.1f}%")
        st.metric("Máxima", f"{df_filtered['tasa_accidentalidad'].max():.1f}%")
        st.metric("Tiendas >5%", f"{len(df_filtered[df_filtered['tasa_accidentalidad'] >= 5])}")
        
        # Distribución
        fig_dist = go.Figure()
        fig_dist.add_trace(go.Histogram(
            x=df_filtered['tasa_accidentalidad'],
            nbinsx=20,
            marker_color=COLORS['accidentes']
        ))
        fig_dist.update_layout(
            title="Distribución Tasa Accidentalidad",
            xaxis_title="Tasa (%)",
            yaxis_title="Frecuencia",
            height=250,
            margin=dict(l=20, r=20, t=40, b=40)
        )
        st.plotly_chart(fig_dist, use_container_width=True)

st.markdown("---")

# ==========================
# VISTA GEOGRÁFICA
# ==========================
st.markdown("### 🗺️ Vista Geográfica")

col_map, col_config = st.columns([4, 1])

with col_config:
    st.markdown("#### ⚙️ Configuración")
    
    metrica_mapa = st.selectbox(
        "Métrica a visualizar",
        options=[
            'Total Activos',
            'Tasa Rotación',
            'Tasa Ausentismo',
            'Tasa Accidentalidad'
        ],
        key="metrica_mapa"
    )
    
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
            
            # Capa geográfica
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
            
            # Determinar columna y color según métrica
            if metrica_mapa == 'Total Activos':
                columna_valor = 'total_activos'
                color_base = COLORS['primary']
            elif metrica_mapa == 'Tasa Rotación':
                columna_valor = 'tasa_rotacion'
                color_base = COLORS['retiros']
            elif metrica_mapa == 'Tasa Ausentismo':
                columna_valor = 'tasa_ausentismo'
                color_base = COLORS['ausentismo']
            else:  # Tasa Accidentalidad
                columna_valor = 'tasa_accidentalidad'
                color_base = COLORS['accidentes']
            
            # Colores por zona
            zonas_unicas = df_mapa['zona'].unique()
            colores_zonas = {
                zona: CHART_COLORS[i % len(CHART_COLORS)]
                for i, zona in enumerate(zonas_unicas)
            }
            
            # Marcadores
            for zona in zonas_unicas:
                df_zona = df_mapa[df_mapa['zona'] == zona]
                
                for _, row in df_zona.iterrows():
                    valor = row[columna_valor]
                    radio = max(tamaño_base, valor * factor_escala)
                    color = colores_zonas.get(zona, color_base)
                    
                    # Determinar si es alerta
                    es_alerta = (
                        row['tasa_rotacion'] >= 10 or
                        row['tasa_ausentismo'] >= 15 or
                        row['tasa_accidentalidad'] >= 5
                    )
                    
                    icono_alerta = "🚨" if es_alerta else ""
                    
                    popup_html = f"""
                    <div style="font-family: Arial; min-width: 250px;">
                        <h4 style="margin:0; color: {COLORS['primary']};">
                            {icono_alerta} {row['almacen']}
                        </h4>
                        <hr style="margin: 5px 0;">
                        <table style="width:100%; font-size: 12px;">
                            <tr><td>📍 Isocrona:</td><td><b>{row['zona']}</b></td></tr>
                            <tr><td>👨‍💼 Gestor:</td><td><b>{row['gestor']}</b></td></tr>
                            <tr><td>🏬 Tipo:</td><td><b>{row['tipo_tienda']}</b></td></tr>
                            <tr><td colspan="2" style="padding-top:8px;"><hr style="margin:2px 0;"></td></tr>
                            <tr><td>👥 Activos:</td><td><b>{int(row['total_activos'])}</b></td></tr>
                            <tr><td>🚪 Retiros:</td><td><b>{int(row['total_retiros'])} ({row['tasa_rotacion']:.1f}%)</b></td></tr>
                            <tr><td>😷 Ausentismo:</td><td><b>{int(row['total_ausentismo'])} ({row['tasa_ausentismo']:.1f}%)</b></td></tr>
                            <tr><td>🚑 Accidentes:</td><td><b>{int(row['total_accidentes'])} ({row['tasa_accidentalidad']:.1f}%)</b></td></tr>
                            <tr><td colspan="2" style="padding-top:5px;">📅 <i>{row['mes']} {row['año']}</i></td></tr>
                        </table>
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
                        tooltip=f"{row['almacen']} - {metrica_mapa}: {valor:.1f}"
                    ).add_to(m)
            
            folium.LayerControl().add_to(m)
            st_folium(m, width=None, height=600, returned_objects=[])
            
            st.success(f"✅ Mapa cargado: {len(df_mapa)} ubicaciones | Métrica: {metrica_mapa}")
    
    except Exception as e:
        st.error(f"❌ Error al crear el mapa: {str(e)}")

st.markdown("---")

# ==========================
# TABLA DE DATOS DETALLADA
# ==========================
st.markdown("### 📋 Datos Detallados por Tienda")

col1, col2, col3 = st.columns(3)

with col1:
    columnas_disponibles = [
        'almacen', 'zona', 'gestor', 'tipo_tienda', 'nom_oficio',
        'total_activos', 'total_retiros', 'total_ausentismo', 'total_accidentes',
        'tasa_rotacion', 'tasa_ausentismo', 'tasa_accidentalidad', 'fecha'
    ]
    columnas_existentes = [col for col in columnas_disponibles if col in df_filtered.columns]
    
    mostrar_columnas = st.multiselect(
        "Seleccionar columnas",
        options=columnas_existentes,
        default=[c for c in ['almacen', 'zona', 'total_activos', 'total_retiros', 
                             'total_ausentismo', 'total_accidentes'] if c in columnas_existentes],
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
    opciones_ordenar = [c for c in ['total_activos', 'tasa_rotacion', 'tasa_ausentismo', 
                                     'tasa_accidentalidad', 'almacen'] if c in df_filtered.columns]
    ordenar_por = st.selectbox("Ordenar por", options=opciones_ordenar, index=0, key="ordenar_tabla")
    orden_ascendente = st.checkbox("Orden ascendente", value=False, key="orden_tabla")

if mostrar_columnas:
    tabla_data = df_filtered[mostrar_columnas].sort_values(ordenar_por, ascending=orden_ascendente)
    
    if registros_mostrar != "Todos":
        tabla_data = tabla_data.head(int(registros_mostrar))
    
    column_config = {
        "almacen": st.column_config.TextColumn("🏪 Tienda", width="medium"),
        "zona": st.column_config.TextColumn("📍 Isocrona", width="small"),
        "gestor": st.column_config.TextColumn("👨‍💼 Gestor", width="medium"),
        "tipo_tienda": st.column_config.TextColumn("🏬 Tipo", width="small"),
        "total_activos": st.column_config.NumberColumn("👥 Activos", format="%d", width="small"),
        "total_retiros": st.column_config.NumberColumn("🚪 Retiros", format="%d", width="small"),
        "total_ausentismo": st.column_config.NumberColumn("😷 Ausentismo", format="%d", width="small"),
        "total_accidentes": st.column_config.NumberColumn("🚑 Accidentes", format="%d", width="small"),
        "tasa_rotacion": st.column_config.NumberColumn("% Rotación", format="%.1f%%", width="small"),
        "tasa_ausentismo": st.column_config.NumberColumn("% Ausentismo", format="%.1f%%", width="small"),
        "tasa_accidentalidad": st.column_config.NumberColumn("% Accidentes", format="%.1f%%", width="small"),
        "fecha": st.column_config.TextColumn("📅 Período", width="small"),
        "nom_oficio": st.column_config.TextColumn("💼 Oficio", width="medium")
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
<div style="text-align: center; padding: 20px; background: linear-gradient(135deg, {COLORS['gradient_start']} 0%, {COLORS['gradient_end']} 100%); color: white; border-radius: 10px;">
    <h4>📊 Dashboard Obeya Comercial 2026</h4>
    <p style="margin: 5px 0;">
        <b>Generado:</b> {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')} | 
        <b>Período:</b> {mes} {año} | 
        <b>Registros:</b> {len(df_filtered):,} de {len(df):,}
    </p>
    <p style="margin: 5px 0; font-size: 0.9em;">
        Arquitectura: CSV → Procesamiento → Visualización Interactiva
    </p>
</div>
""", unsafe_allow_html=True)