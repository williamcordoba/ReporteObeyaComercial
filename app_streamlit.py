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
    'primary':        '#1e3c72',
    'secondary':      '#2a5298',
    'accent':         '#7fa8e0',
    'success':        '#28a745',
    'warning':        '#ffc107',
    'danger':         '#dc3545',
    'info':           '#17a2b8',
    'light':          '#f8f9fa',
    'dark':           '#343a40',
    'gradient_start': '#1e3c72',
    'gradient_end':   '#2a5298',
    'retiros':        '#dc3545',
    'ausentismo':     '#ffc107',
    'accidentes':     '#28a745',
    'aus_medico':     '#e74c3c',
    'aus_legal':      '#9b59b6',
    'aus_admin':      '#3498db',
}

CHART_COLORS = ['#1e3c72', '#2a5298', '#7fa8e0', '#5080c0', '#3060a0', '#406db8', '#e74c3c', '#9b59b6']

# ==========================
# CONFIGURACIÓN DE RUTAS
# ==========================
import os
CSV_PATH      = os.environ.get('CSV_PATH', 'data.csv')
GEOJSON_PATH  = os.environ.get('GEODATA_PATH', 'geodata')

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
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1e3c72;
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
# MAPEO MES → NÚMERO
# ==========================
MES_ORDEN = {
    '01. ENERO': 1,  '02. FEBRERO': 2,  '03. MARZO': 3,    '04. ABRIL': 4,
    '05. MAYO': 5,   '06. JUNIO': 6,    '07. JULIO': 7,    '08. AGOSTO': 8,
    '09. SEPTIEMBRE': 9, '10. OCTUBRE': 10, '11. NOVIEMBRE': 11, '12. DICIEMBRE': 12
}

def parse_pct(series):
    """Convierte '12,34 %' → 12.34 (float)."""
    return (
        series.astype(str)
        .str.replace('%', '', regex=False)
        .str.replace(',', '.', regex=False)
        .str.strip()
        .pipe(pd.to_numeric, errors='coerce')
        .fillna(0)
    )

def parse_num(series):
    """Convierte '1.234,56' o '1,234.56' → float."""
    return (
        series.astype(str)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False)
        .str.strip()
        .pipe(pd.to_numeric, errors='coerce')
        .fillna(0)
    )

# ==========================
# CARGA Y PROCESAMIENTO
# ==========================
@st.cache_data(ttl=600, show_spinner=False)
def load_csv():
    try:
        # CORREGIDO: Usar punto y coma como separador
        df = pd.read_csv(CSV_PATH, encoding='utf-8-sig', sep=';')
        
        # Limpiar nombres de columnas
        df.columns = (
            df.columns
            .str.strip()
            .str.upper()
            .str.replace(' ', '_', regex=False)
        )

        # Renombres de conveniencia - NUEVA ESTRUCTURA
        rename = {
            'NOM_CCOSTO':              'ALMACEN',
            'NOM_OFICIO':              'NOM_OFICIO',
            'ACTIVOS':                 'TOTAL_ACTIVOS',
            'AÑO':                     'AÑO',
            'RETIROS':                 'RETIROS',
            'CONT_TOTAL':              'TOTAL_AUSENTISMO',
            'ACCIDENTES':              'TOTAL_ACCIDENTES',
            'COLOR_AUS_MED':           'COLOR_AUS_MED',
            'CONT_AUS_LEG':            'AUS_LEG',
            'CONT_AUS_ADM':            'AUS_ADMINISTRATIVO',
            'DIAS_ADMINISTRATIVO':     'DIAS_ADMIN',
            'DIAS_LEGAL':              'DIAS_LEGAL',
            'DIAS_MEDICO':             'DIAS_MEDICO',
            'DIAS_AUSENCIA':           'DIAS_AUSENCIA',
            'HORAS_AUSENTISMO':        'HORAS_AUSENTISMO',
            'HORAS':                   'HORAS_TRABAJADAS',
            'RANGOS_DE_PERMANENCIA':   'RANGO_PERMANENCIA',
            'TASA_ROTACION_MENSUAL_ACUM': 'TASA_ROTACION_MENSUAL',
        }
        df.rename(columns={k: v for k, v in rename.items() if k in df.columns}, inplace=True)

        # Coordenadas (formato europeo con coma decimal)
        for col in ['LATITUD', 'LONGITUD']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Tasas almacenadas como texto
        if 'TASA_ROTACION_MENSUAL' in df.columns:
            df['TASA_ROTACION_MENSUAL'] = parse_pct(df['TASA_ROTACION_MENSUAL'])
        if 'TASA_ROTACION_ACT_MES_ANT' in df.columns:
            df['TASA_ROTACION_ACT_MES_ANT'] = parse_pct(df['TASA_ROTACION_ACT_MES_ANT'])
        if 'TASA_DE_ACCIDENTALIDAD' in df.columns:
            df['TASA_DE_ACCIDENTALIDAD'] = parse_pct(df['TASA_DE_ACCIDENTALIDAD'])
        if 'HORAS_TRABAJADAS' in df.columns:
            df['HORAS_TRABAJADAS'] = parse_num(df['HORAS_TRABAJADAS'])

        # Numéricas directas
        for col in ['TOTAL_ACTIVOS', 'RETIROS', 'TOTAL_AUSENTISMO', 'TOTAL_ACCIDENTES',
                    'AUS_LEG', 'AUS_ADMINISTRATIVO',
                    'DIAS_ADMIN', 'DIAS_LEGAL', 'DIAS_MEDICO', 'DIAS_AUSENCIA', 'HORAS_AUSENTISMO']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(0)

        # AUS_MEDICO viene como COLOR_AUS_MED (es un indicador visual), lo convertimos a 0/1
        if 'COLOR_AUS_MED' in df.columns:
            # Si tiene color diferente a un valor base, consideramos que tiene ausentismo
            df['AUS_MEDICO'] = df['COLOR_AUS_MED'].apply(lambda x: 1 if str(x) != '#37A794' and pd.notna(x) else 0)
        
        df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce')
        df['AÑO'] = df['AÑO'].astype('Int64')
        df['MES'] = df['MES'].astype(str).str.strip().str.upper()

        if 'RANGO_PERMANENCIA' in df.columns:
            df['RANGO_PERMANENCIA'] = df['RANGO_PERMANENCIA'].astype(str).str.strip()

        return df

    except FileNotFoundError:
        st.error(f"❌ No se encontró el archivo CSV.\n\nRuta buscada: **{CSV_PATH}**")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error al cargar el CSV: {e}")
        st.stop()


@st.cache_data(ttl=600, show_spinner=False)
def process_data(df_raw, mes, año):
    """Agrega datos por tienda (CCOSTO) para el período seleccionado."""
    df = df_raw[(df_raw['MES'] == mes) & (df_raw['AÑO'] == año)].copy()
    if df.empty:
        return df

    # Agregar por ALMACEN manteniendo ZONA y coordenadas
    group_cols = [c for c in ['ALMACEN', 'ZONA', 'LATITUD', 'LONGITUD', 'MES', 'AÑO']
                  if c in df.columns]

    agg_dict = {
        'TOTAL_ACTIVOS':            ('TOTAL_ACTIVOS',           'sum'),
        'RETIROS':                  ('RETIROS',                 'sum'),
        'TOTAL_AUSENTISMO':         ('TOTAL_AUSENTISMO',        'sum'),
        'TOTAL_ACCIDENTES':         ('TOTAL_ACCIDENTES',        'sum'),
        'AUS_MEDICO':               ('AUS_MEDICO',              'sum'),
        'AUS_LEG':                  ('AUS_LEG',                 'sum'),
        'AUS_ADMINISTRATIVO':       ('AUS_ADMINISTRATIVO',      'sum'),
        'DIAS_AUSENCIA':            ('DIAS_AUSENCIA',           'sum'),
        'DIAS_ADMIN':               ('DIAS_ADMIN',              'sum'),
        'DIAS_LEGAL':               ('DIAS_LEGAL',              'sum'),
        'DIAS_MEDICO':              ('DIAS_MEDICO',             'sum'),
        'HORAS_AUSENTISMO':         ('HORAS_AUSENTISMO',        'sum'),
        'HORAS_TRABAJADAS':         ('HORAS_TRABAJADAS',        'sum'),
        'TASA_ROTACION_MENSUAL':    ('TASA_ROTACION_MENSUAL',   'mean'),
        'TASA_ROTACION_ACT_MES_ANT':('TASA_ROTACION_ACT_MES_ANT','mean'),
        'TASA_DE_ACCIDENTALIDAD':   ('TASA_DE_ACCIDENTALIDAD',  'mean'),
    }
    agg_dict = {k: v for k, v in agg_dict.items() if v[0] in df.columns}

    df = df.groupby(group_cols, dropna=False).agg(**agg_dict).reset_index()

    # Calcular tasas
    activos = df['TOTAL_ACTIVOS'].clip(lower=1)
    df['TASA_ROTACION']      = (df['RETIROS'] / activos * 100)
    df['TASA_ROTACION']      = df['TASA_ROTACION'].fillna(0)
    df['TASA_AUSENTISMO']    = (df['TOTAL_AUSENTISMO'] / activos * 100)
    df['TASA_AUSENTISMO']    = df['TASA_AUSENTISMO'].fillna(0)
    df['TASA_ACCIDENTALIDAD']= (df['TOTAL_ACCIDENTES'] / activos * 100)
    df['TASA_ACCIDENTALIDAD']= df['TASA_ACCIDENTALIDAD'].fillna(0)

    df['FECHA'] = df['MES'].map(MES_ORDEN).astype(str) + '/' + df['AÑO'].astype(str)
    
    return df


@st.cache_data(ttl=600, show_spinner=False)
def load_geojson(file_path=None):
    try:
        if file_path is None:
            geo_path = Path(GEOJSON_PATH)
            if not geo_path.exists():
                return None
            files = list(geo_path.glob('*.geojson')) + list(geo_path.glob('*.shp'))
            if not files:
                return None
            file_path = files[0]
        return gpd.read_file(file_path)
    except Exception as e:
        st.warning(f"No se pudieron cargar capas geográficas: {e}")
        return None


# ==========================
# HEADER
# ==========================
st.markdown("""
<div class="main-header">
    <h1>📊 Dashboard Obeya Comercial 2026</h1>
    <h3>🎯 Análisis Estratégico de Cobertura y Gestión de Personal</h3>
</div>
""", unsafe_allow_html=True)

# ==========================
# CARGAR DATOS
# ==========================
df_raw = load_csv()

meses_disponibles = sorted(
    df_raw['MES'].dropna().unique().tolist(),
    key=lambda m: MES_ORDEN.get(m, 99)
)

# ==========================
# SIDEBAR
# ==========================
with st.sidebar:
    st.markdown("### 🎯 Panel de Control")
    st.markdown("---")

    st.markdown("#### 📅 Período")
    mes  = st.selectbox("Mes",  meses_disponibles, key="mes_select")
    años = sorted(df_raw['AÑO'].dropna().unique().tolist(), reverse=True)
    año  = st.selectbox("Año",  años, index=0, key="año_select")

    with st.spinner('🔄 Procesando datos...'):
        df = process_data(df_raw, mes, int(año))

    if df.empty:
        st.warning(f"⚠️ No hay datos para **{mes} {año}**. Selecciona otro período.")
        st.stop()

    st.markdown("---")
    st.markdown("#### 📊 Resumen General")
    c1, c2 = st.columns(2)
    c1.metric("Registros",  f"{len(df):,}")
    c2.metric("Tiendas",    f"{df['ALMACEN'].nunique()}")
    st.metric("👥 Total Activos", f"{int(df['TOTAL_ACTIVOS'].sum()):,}")

    st.markdown("---")
    st.markdown("#### ⚠️ Indicadores Críticos")
    st.metric("🚪 Retiros",     f"{int(df['RETIROS'].sum()):,}",
              delta=f"{df['TASA_ROTACION'].mean():.1f}% rotación", delta_color="inverse")
    st.metric("😷 Ausentismo",  f"{int(df['TOTAL_AUSENTISMO'].sum()):,}",
              delta=f"{df['TASA_AUSENTISMO'].mean():.1f}% tasa", delta_color="inverse")
    st.metric("🚑 Accidentes",  f"{int(df['TOTAL_ACCIDENTES'].sum()):,}",
              delta=f"{df['TASA_ACCIDENTALIDAD'].mean():.1f}% tasa", delta_color="inverse")
    st.metric("📅 Días ausencia", f"{int(df['DIAS_AUSENCIA'].sum()):,}")
    st.metric("⏱️ Horas ausentismo", f"{int(df['HORAS_AUSENTISMO'].sum()):,}")

    st.markdown("---")
    st.markdown("#### 🔍 Filtros Avanzados")
    
    # Filtro de zonas
    zonas   = ['TODAS'] + sorted(df['ZONA'].dropna().unique().tolist())
    zona_sel = st.selectbox("🌍 Zona", zonas, key="zona_select")
    
    # Filtro de tiendas
    st.markdown("#### 🏪 Filtro de Tiendas")
    tiendas = ['TODAS'] + sorted(df['ALMACEN'].dropna().unique().tolist())
    tienda_sel = st.selectbox("Tienda/CCosto", tiendas, key="tienda_select")

    st.markdown("#### 🚨 Filtros de Alerta")
    mostrar_alertas = st.checkbox("🔔 Solo tiendas con alertas", value=False)
    if mostrar_alertas:
        umbral_rotacion   = st.slider("Umbral rotación (%)",     0, 50, 10, key="umbral_rot")
        umbral_ausentismo = st.slider("Umbral ausentismo (%)",   0, 50, 15, key="umbral_aus")
        umbral_accidentes = st.slider("Umbral accidentes (%)",   0, 20,  5, key="umbral_acc")

    st.markdown("---")
    if st.button("🔄 Resetear Filtros", use_container_width=True):
        st.rerun()

    st.markdown("---")
    st.markdown("#### 💾 Exportar Datos")

    csv_bytes = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Descargar CSV",
        data=csv_bytes,
        file_name=f"Obeya_{mes}_{año}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

# ==========================
# BOTONES DE ZONA (PRINCIPAL)
# ==========================
zonas_disponibles = sorted(df['ZONA'].dropna().unique().tolist())

st.markdown("### 🌍 Filtrar por Zona")
st.markdown("*Selecciona una zona para ver el análisis detallado, o deja sin selección para ver la totalidad*")

# Usar radio buttons para selección de zona
zona_seleccionada = st.radio(
    "Seleccionar Zona:",
    options=["TODAS"] + zonas_disponibles,
    index=0,
    horizontal=True,
    key="zona_radio"
)

# Aplicar filtro de zona principal
if zona_seleccionada != "TODAS":
    df_zona = df[df['ZONA'] == zona_seleccionada].copy()
    st.info(f"📍 Mostrando datos para: **{zona_seleccionada}** ({len(df_zona)} registros)")
else:
    df_zona = df.copy()
    st.info(f"📊 Mostrando la **totalidad** de datos ({len(df_zona)} registros)")

# ==========================
# APLICAR FILTROS ADICIONALES
# ==========================
df_f = df_zona.copy()

# Filtro de zona del sidebar (filtro adicional)
if zona_sel != 'TODAS' and zona_seleccionada == "TODAS":
    df_f = df_f[df_f['ZONA'] == zona_sel]

# Filtro de tienda
if tienda_sel != 'TODAS':
    df_f = df_f[df_f['ALMACEN'] == tienda_sel]

if mostrar_alertas:
    df_f = df_f[
        (df_f['TASA_ROTACION']      >= umbral_rotacion) |
        (df_f['TASA_AUSENTISMO']    >= umbral_ausentismo) |
        (df_f['TASA_ACCIDENTALIDAD']>= umbral_accidentes)
    ]

if df_f.empty:
    st.warning("⚠️ No hay datos para los filtros seleccionados.")
    st.stop()

# ==========================
# KPIs PRINCIPALES
# ==========================
st.markdown("### 📈 Indicadores Clave de Desempeño")
k1, k2, k3, k4, k5, k6 = st.columns(6)

total_act  = int(df_f['TOTAL_ACTIVOS'].sum())
total_ret  = int(df_f['RETIROS'].sum())
total_aus  = int(df_f['TOTAL_AUSENTISMO'].sum())
total_acc  = int(df_f['TOTAL_ACCIDENTES'].sum())
total_dias = int(df_f['DIAS_AUSENCIA'].sum())
total_hrs  = int(df_f['HORAS_AUSENTISMO'].sum())
pct_tot    = total_act / max(int(df['TOTAL_ACTIVOS'].sum()), 1) * 100

k1.metric("👥 Activos",          f"{total_act:,}",   f"{pct_tot:.1f}% del total")
k2.metric("🚪 Retiros",          f"{total_ret:,}",   f"{total_ret/max(total_act,1)*100:.1f}% rot.", delta_color="inverse")
k3.metric("😷 Ausentismo",       f"{total_aus:,}",   f"{total_aus/max(total_act,1)*100:.1f}% tasa", delta_color="inverse")
k4.metric("🚑 Accidentes",       f"{total_acc:,}",   f"{total_acc/max(total_act,1)*100:.1f}% tasa", delta_color="inverse")
k5.metric("📅 Días Ausencia",    f"{total_dias:,}")
k6.metric("⏱️ Horas Ausentismo", f"{total_hrs:,}")

st.markdown("---")

# ==========================
# ANÁLISIS COMPARATIVO DE INDICADORES (PRIMERO)
# ==========================
st.markdown("### 📊 Análisis Comparativo de Indicadores")
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 General", "🚪 Rotación", "😷 Ausentismo", "🚑 Accidentes", "📅 Tendencia"
])

# ── TAB 1: GENERAL ──────────────────────────────────────────
with tab1:
    c1, c2 = st.columns(2)

    with c1:
        zona_m = df_f.groupby('ZONA').agg(
            TOTAL_ACTIVOS=('TOTAL_ACTIVOS','sum'),
            RETIROS=('RETIROS','sum'),
            TOTAL_AUSENTISMO=('TOTAL_AUSENTISMO','sum'),
            TOTAL_ACCIDENTES=('TOTAL_ACCIDENTES','sum'),
        ).reset_index()

        fig = go.Figure()
        fig.add_trace(go.Bar(name='👥 Activos',   x=zona_m['ZONA'], y=zona_m['TOTAL_ACTIVOS'],   marker_color=COLORS['primary']))
        fig.add_trace(go.Bar(name='🚪 Retiros',   x=zona_m['ZONA'], y=zona_m['RETIROS'],   marker_color=COLORS['retiros']))
        fig.add_trace(go.Bar(name='😷 Ausentismo',x=zona_m['ZONA'], y=zona_m['TOTAL_AUSENTISMO'],marker_color=COLORS['ausentismo']))
        fig.add_trace(go.Bar(name='🚑 Accidentes',x=zona_m['ZONA'], y=zona_m['TOTAL_ACCIDENTES'],marker_color=COLORS['accidentes']))
        fig.update_layout(title='Métricas por Zona', barmode='group',
                          plot_bgcolor='white', paper_bgcolor='white', height=400)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        zona_t = df_f.groupby('ZONA').agg(
            TASA_ROTACION=('TASA_ROTACION','mean'),
            TASA_AUSENTISMO=('TASA_AUSENTISMO','mean'),
            TASA_ACCIDENTALIDAD=('TASA_ACCIDENTALIDAD','mean'),
        ).reset_index()

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name='% Rotación',      x=zona_t['ZONA'], y=zona_t['TASA_ROTACION'],      marker_color=COLORS['retiros']))
        fig2.add_trace(go.Bar(name='% Ausentismo',    x=zona_t['ZONA'], y=zona_t['TASA_AUSENTISMO'],    marker_color=COLORS['ausentismo']))
        fig2.add_trace(go.Bar(name='% Accidentalidad',x=zona_t['ZONA'], y=zona_t['TASA_ACCIDENTALIDAD'],marker_color=COLORS['accidentes']))
        fig2.update_layout(title='Tasas Promedio por Zona', barmode='group',
                           yaxis_title='%', plot_bgcolor='white', paper_bgcolor='white', height=400)
        st.plotly_chart(fig2, use_container_width=True)

# ── TAB 2: ROTACIÓN ─────────────────────────────────────────
with tab2:
    c1, c2 = st.columns([2, 1])

    with c1:
        top_rot = df_f.nlargest(15, 'TASA_ROTACION')[
            ['ALMACEN','ZONA','TOTAL_ACTIVOS','RETIROS',
             'TASA_ROTACION','TASA_ROTACION_MENSUAL','TASA_ROTACION_ACT_MES_ANT']
        ].copy()

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=top_rot['ALMACEN'], x=top_rot['TASA_ROTACION'],
            orientation='h', name='Tasa actual',
            text=top_rot['TASA_ROTACION'].round(1),
            texttemplate='%{text}%', textposition='outside',
            marker=dict(
                color=top_rot['TASA_ROTACION'],
                colorscale=[[0, COLORS['warning']], [1, COLORS['danger']]]
            ),
            customdata=top_rot[['TOTAL_ACTIVOS','RETIROS','ZONA',
                                 'TASA_ROTACION_MENSUAL','TASA_ROTACION_ACT_MES_ANT']],
            hovertemplate=(
                '<b>%{y}</b><br>'
                'Tasa rotación: %{x:.1f}%<br>'
                'Activos: %{customdata[0]}<br>'
                'Retiros: %{customdata[1]}<br>'
                'Zona: %{customdata[2]}<br>'
                'Tasa mensual: %{customdata[3]:.1f}%<br>'
                'Tasa mes ant.: %{customdata[4]:.1f}%<extra></extra>'
            )
        ))
        fig.update_layout(
            title='🚪 Top 15 Tiendas – Mayor Tasa de Rotación',
            xaxis_title='Tasa de Rotación (%)', yaxis_title='',
            plot_bgcolor='white', paper_bgcolor='white',
            height=500, margin=dict(l=200)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Comparativa mes actual vs mes anterior
        fig_cmp = go.Figure()
        fig_cmp.add_trace(go.Bar(
            name='Tasa mes anterior',
            x=top_rot['ALMACEN'], y=top_rot['TASA_ROTACION_ACT_MES_ANT'],
            marker_color=COLORS['accent']
        ))
        fig_cmp.add_trace(go.Bar(
            name='Tasa mes actual',
            x=top_rot['ALMACEN'], y=top_rot['TASA_ROTACION_MENSUAL'],
            marker_color=COLORS['retiros']
        ))
        fig_cmp.update_layout(
            title='Comparativa Tasa Rotación: Mes Anterior vs Actual (Top 15)',
            barmode='group', xaxis_tickangle=-45,
            plot_bgcolor='white', paper_bgcolor='white', height=400
        )
        st.plotly_chart(fig_cmp, use_container_width=True)

    with c2:
        st.markdown("#### 📊 Estadísticas de Rotación")
        st.metric("Promedio",     f"{df_f['TASA_ROTACION'].mean():.1f}%")
        st.metric("Mediana",      f"{df_f['TASA_ROTACION'].median():.1f}%")
        st.metric("Máxima",       f"{df_f['TASA_ROTACION'].max():.1f}%")
        st.metric("Tiendas >10%", f"{len(df_f[df_f['TASA_ROTACION'] >= 10])}")
        st.metric("Total retiros",f"{int(df_f['RETIROS'].sum()):,}")

        fig_d = go.Figure(go.Histogram(x=df_f['TASA_ROTACION'], nbinsx=20,
                                        marker_color=COLORS['retiros']))
        fig_d.update_layout(title="Distribución", xaxis_title="Tasa (%)",
                             yaxis_title="Frecuencia", height=250,
                             margin=dict(l=20, r=20, t=40, b=40))
        st.plotly_chart(fig_d, use_container_width=True)

# ── TAB 3: AUSENTISMO ───────────────────────────────────────
with tab3:
    # KPIs de desglose
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🏥 Médico",       f"{int(df_f['AUS_MEDICO'].sum()):,}",
              f"{df_f['AUS_MEDICO'].sum()/max(df_f['TOTAL_AUSENTISMO'].sum(),1)*100:.0f}%")
    k2.metric("⚖️ Legal",        f"{int(df_f['AUS_LEG'].sum()):,}",
              f"{df_f['AUS_LEG'].sum()/max(df_f['TOTAL_AUSENTISMO'].sum(),1)*100:.0f}%")
    k3.metric("🗂️ Administrativo",f"{int(df_f['AUS_ADMINISTRATIVO'].sum()):,}",
              f"{df_f['AUS_ADMINISTRATIVO'].sum()/max(df_f['TOTAL_AUSENTISMO'].sum(),1)*100:.0f}%")
    k4.metric("📅 Días totales", f"{int(df_f['DIAS_AUSENCIA'].sum()):,}")

    c1, c2 = st.columns([2, 1])

    with c1:
        top_aus = df_f.nlargest(15, 'TASA_AUSENTISMO')[
            ['ALMACEN','ZONA','TOTAL_ACTIVOS','TOTAL_AUSENTISMO',
             'AUS_MEDICO','AUS_LEG','AUS_ADMINISTRATIVO',
             'DIAS_AUSENCIA','HORAS_AUSENTISMO','TASA_AUSENTISMO']
        ].copy()

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=top_aus['ALMACEN'], x=top_aus['TASA_AUSENTISMO'],
            orientation='h',
            text=top_aus['TASA_AUSENTISMO'].round(1),
            texttemplate='%{text}%', textposition='outside',
            marker=dict(
                color=top_aus['TASA_AUSENTISMO'],
                colorscale=[[0, '#fff3cd'], [1, COLORS['warning']]]
            ),
            customdata=top_aus[['TOTAL_ACTIVOS','TOTAL_AUSENTISMO','ZONA',
                                  'AUS_MEDICO','AUS_LEG','AUS_ADMINISTRATIVO',
                                  'DIAS_AUSENCIA','HORAS_AUSENTISMO']],
            hovertemplate=(
                '<b>%{y}</b><br>'
                'Tasa: %{x:.1f}%<br>'
                'Activos: %{customdata[0]}<br>'
                'Total ausentes: %{customdata[1]}<br>'
                'Zona: %{customdata[2]}<br>'
                '🏥 Médico: %{customdata[3]}<br>'
                '⚖️ Legal: %{customdata[4]}<br>'
                '🗂️ Admin: %{customdata[5]}<br>'
                '📅 Días: %{customdata[6]}<br>'
                '⏱️ Horas: %{customdata[7]:.0f}<extra></extra>'
            )
        ))
        fig.update_layout(
            title='😷 Top 15 Tiendas – Mayor Tasa de Ausentismo',
            xaxis_title='Tasa (%)', yaxis_title='',
            plot_bgcolor='white', paper_bgcolor='white',
            height=500, margin=dict(l=200)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Composición ausentismo por zona
        zona_aus = df_f.groupby('ZONA').agg(
            AUS_MEDICO=('AUS_MEDICO','sum'),
            AUS_LEG=('AUS_LEG','sum'),
            AUS_ADMINISTRATIVO=('AUS_ADMINISTRATIVO','sum'),
        ).reset_index()

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name='🏥 Médico',        x=zona_aus['ZONA'], y=zona_aus['AUS_MEDICO'],        marker_color=COLORS['aus_medico']))
        fig2.add_trace(go.Bar(name='⚖️ Legal',         x=zona_aus['ZONA'], y=zona_aus['AUS_LEG'],         marker_color=COLORS['aus_legal']))
        fig2.add_trace(go.Bar(name='🗂️ Administrativo',x=zona_aus['ZONA'], y=zona_aus['AUS_ADMINISTRATIVO'],marker_color=COLORS['aus_admin']))
        fig2.update_layout(
            title='Composición del Ausentismo por Zona',
            barmode='stack', plot_bgcolor='white', paper_bgcolor='white', height=380
        )
        st.plotly_chart(fig2, use_container_width=True)

    with c2:
        st.markdown("#### 📊 Estadísticas")
        st.metric("Promedio",      f"{df_f['TASA_AUSENTISMO'].mean():.1f}%")
        st.metric("Mediana",       f"{df_f['TASA_AUSENTISMO'].median():.1f}%")
        st.metric("Máxima",        f"{df_f['TASA_AUSENTISMO'].max():.1f}%")
        st.metric("Tiendas >15%",  f"{len(df_f[df_f['TASA_AUSENTISMO'] >= 15])}")
        st.metric("⏱️ Horas totales", f"{int(df_f['HORAS_AUSENTISMO'].sum()):,}")

        # Pie ausentismo por tipo
        vals = [df_f['AUS_MEDICO'].sum(), df_f['AUS_LEG'].sum(), df_f['AUS_ADMINISTRATIVO'].sum()]
        lbs  = ['Médico', 'Legal', 'Admin']
        fig_pie = go.Figure(go.Pie(labels=lbs, values=vals,
                                    marker_colors=[COLORS['aus_medico'], COLORS['aus_legal'], COLORS['aus_admin']],
                                    hole=0.4))
        fig_pie.update_layout(title="Composición", height=280,
                               margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_pie, use_container_width=True)

        fig_d = go.Figure(go.Histogram(x=df_f['TASA_AUSENTISMO'], nbinsx=20,
                                        marker_color=COLORS['ausentismo']))
        fig_d.update_layout(title="Distribución", xaxis_title="Tasa (%)",
                             yaxis_title="Frecuencia", height=230,
                             margin=dict(l=20, r=20, t=40, b=40))
        st.plotly_chart(fig_d, use_container_width=True)

# ── TAB 4: ACCIDENTES ───────────────────────────────────────
with tab4:
    c1, c2 = st.columns([2, 1])

    with c1:
        top_acc = df_f.nlargest(15, 'TASA_ACCIDENTALIDAD')[
            ['ALMACEN','ZONA','TOTAL_ACTIVOS','TOTAL_ACCIDENTES','TASA_ACCIDENTALIDAD']
        ].copy()

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=top_acc['ALMACEN'], x=top_acc['TASA_ACCIDENTALIDAD'],
            orientation='h',
            text=top_acc['TASA_ACCIDENTALIDAD'].round(1),
            texttemplate='%{text}%', textposition='outside',
            marker=dict(
                color=top_acc['TASA_ACCIDENTALIDAD'],
                colorscale=[[0, '#c8f7c5'], [1, COLORS['accidentes']]]
            ),
            customdata=top_acc[['TOTAL_ACTIVOS','TOTAL_ACCIDENTES','ZONA']],
            hovertemplate=(
                '<b>%{y}</b><br>'
                'Accidentalidad: %{x:.1f}%<br>'
                'Activos: %{customdata[0]}<br>'
                'Accidentes: %{customdata[1]}<br>'
                'Zona: %{customdata[2]}<extra></extra>'
            )
        ))
        fig.update_layout(
            title='🚑 Top 15 Tiendas – Mayor Tasa de Accidentalidad',
            xaxis_title='Tasa (%)', yaxis_title='',
            plot_bgcolor='white', paper_bgcolor='white',
            height=500, margin=dict(l=200)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Accidentes por zona
        zona_acc = df_f.groupby('ZONA').agg(
            TOTAL_ACCIDENTES=('TOTAL_ACCIDENTES','sum'),
            TOTAL_ACTIVOS=('TOTAL_ACTIVOS','sum'),
        ).reset_index()
        zona_acc['TASA'] = zona_acc['TOTAL_ACCIDENTES'] / zona_acc['TOTAL_ACTIVOS'].clip(1) * 100

        fig2 = px.bar(zona_acc, x='ZONA', y='TOTAL_ACCIDENTES', color='TASA',
                      color_continuous_scale=['#c8f7c5', COLORS['accidentes']],
                      title='Total Accidentes por Zona',
                      labels={'TOTAL_ACCIDENTES':'Accidentes','ZONA':'Zona','TASA':'Tasa %'})
        fig2.update_layout(plot_bgcolor='white', paper_bgcolor='white', height=360)
        st.plotly_chart(fig2, use_container_width=True)

    with c2:
        st.markdown("#### 📊 Estadísticas")
        st.metric("Promedio",     f"{df_f['TASA_ACCIDENTALIDAD'].mean():.1f}%")
        st.metric("Mediana",      f"{df_f['TASA_ACCIDENTALIDAD'].median():.1f}%")
        st.metric("Máxima",       f"{df_f['TASA_ACCIDENTALIDAD'].max():.1f}%")
        st.metric("Tiendas >5%",  f"{len(df_f[df_f['TASA_ACCIDENTALIDAD'] >= 5])}")
        st.metric("Total accidentes", f"{int(df_f['TOTAL_ACCIDENTES'].sum()):,}")

        fig_d = go.Figure(go.Histogram(x=df_f['TASA_ACCIDENTALIDAD'], nbinsx=20,
                                        marker_color=COLORS['accidentes']))
        fig_d.update_layout(title="Distribución", xaxis_title="Tasa (%)",
                             yaxis_title="Frecuencia", height=280,
                             margin=dict(l=20, r=20, t=40, b=40))
        st.plotly_chart(fig_d, use_container_width=True)

# ── TAB 5: TENDENCIA ────────────────────────────────────────
with tab5:
    st.markdown("#### 📈 Evolución Mensual (todos los períodos disponibles)")

    # Filtrar zona si aplica
    df_trend = df_raw.copy() if zona_seleccionada == "TODAS" else df_raw[df_raw['ZONA'] == zona_seleccionada].copy()

    # Parsear columnas en df_raw también
    for col in ['TASA_ROTACION_MENSUAL', 'TASA_ROTACION_ACT_MES_ANT', 'TASA_DE_ACCIDENTALIDAD']:
        if col in df_trend.columns:
            df_trend[col] = parse_pct(df_trend[col])

    trend = df_trend.groupby(['MES','AÑO']).agg(
        TOTAL_ACTIVOS=('TOTAL_ACTIVOS','sum'),
        RETIROS=('RETIROS','sum'),
        TOTAL_AUSENTISMO=('TOTAL_AUSENTISMO','sum'),
        TOTAL_ACCIDENTES=('TOTAL_ACCIDENTES','sum'),
    ).reset_index()
    trend['MES_NUM'] = trend['MES'].map(MES_ORDEN).fillna(0)
    trend = trend.sort_values(['AÑO','MES_NUM'])
    trend['PERIODO'] = trend['MES'].str.replace(r'^\d+\.\s*', '', regex=True) + ' ' + trend['AÑO'].astype(str)
    trend['TASA_ROT'] = (trend['RETIROS']    / trend['TOTAL_ACTIVOS'].clip(1) * 100).round(2)
    trend['TASA_AUS'] = (trend['TOTAL_AUSENTISMO'] / trend['TOTAL_ACTIVOS'].clip(1) * 100).round(2)
    trend['TASA_ACC'] = (trend['TOTAL_ACCIDENTES'] / trend['TOTAL_ACTIVOS'].clip(1) * 100).round(2)

    fig_t = go.Figure()
    fig_t.add_trace(go.Scatter(x=trend['PERIODO'], y=trend['TASA_ROT'],
                                mode='lines+markers', name='% Rotación',   line=dict(color=COLORS['retiros'],    width=2)))
    fig_t.add_trace(go.Scatter(x=trend['PERIODO'], y=trend['TASA_AUS'],
                                mode='lines+markers', name='% Ausentismo', line=dict(color=COLORS['ausentismo'], width=2)))
    fig_t.add_trace(go.Scatter(x=trend['PERIODO'], y=trend['TASA_ACC'],
                                mode='lines+markers', name='% Accidentalidad', line=dict(color=COLORS['accidentes'], width=2)))
    fig_t.update_layout(
        title='Evolución de Tasas por Período',
        xaxis_title='Período', yaxis_title='Tasa (%)',
        plot_bgcolor='white', paper_bgcolor='white',
        height=450, xaxis_tickangle=-45,
        legend=dict(orientation='h', y=1.1)
    )
    st.plotly_chart(fig_t, use_container_width=True)

    # Activos en el tiempo
    fig_act = go.Figure()
    for anio in sorted(trend['AÑO'].unique()):
        d = trend[trend['AÑO'] == anio]
        fig_act.add_trace(go.Scatter(
            x=d['MES'].str.replace(r'^\d+\.\s*','',regex=True),
            y=d['TOTAL_ACTIVOS'],
            mode='lines+markers', name=str(anio)
        ))
    fig_act.update_layout(
        title='Personal Activo por Mes y Año',
        xaxis_title='Mes', yaxis_title='Total Activos',
        plot_bgcolor='white', paper_bgcolor='white', height=380
    )
    st.plotly_chart(fig_act, use_container_width=True)

st.markdown("---")

# ==========================
# ANÁLISIS POR OFICIO (NUEVO)
# ==========================
st.markdown("### 👔 Análisis por Cargo (NOM_OFICIO)")

# Obtener datos de oficio del período seleccionado
df_oficio = df_raw[(df_raw['MES'] == mes) & (df_raw['AÑO'] == año)].copy()
if zona_seleccionada != "TODAS":
    df_oficio = df_oficio[df_oficio['ZONA'] == zona_seleccionada]

if not df_oficio.empty and 'NOM_OFICIO' in df_oficio.columns:
    # Agregar por cargo
    cargo_agg = df_oficio.groupby('NOM_OFICIO').agg({
        'TOTAL_ACTIVOS': 'sum',
        'RETIROS': 'sum',
        'TOTAL_AUSENTISMO': 'sum',
        'TOTAL_ACCIDENTES': 'sum'
    }).reset_index()
    
    # Filtrar solo cargos con activos > 0
    cargo_agg = cargo_agg[cargo_agg['TOTAL_ACTIVOS'] > 0]
    
    cargo_agg['TASA_ROTACION'] = (cargo_agg['RETIROS'] / cargo_agg['TOTAL_ACTIVOS'].clip(lower=1) * 100).fillna(0)
    cargo_agg['TASA_AUSENTISMO'] = (cargo_agg['TOTAL_AUSENTISMO'] / cargo_agg['TOTAL_ACTIVOS'].clip(lower=1) * 100).fillna(0)
    cargo_agg['TASA_ACCIDENTALIDAD'] = (cargo_agg['TOTAL_ACCIDENTES'] / cargo_agg['TOTAL_ACTIVOS'].clip(lower=1) * 100).fillna(0)
    
    cargo_agg = cargo_agg.sort_values('TOTAL_ACTIVOS', ascending=False)
    
    # Top 15 cargos por activos
    c1, c2 = st.columns(2)
    
    with c1:
        top_cargo = cargo_agg.nlargest(15, 'TOTAL_ACTIVOS')
        
        fig_cargo = go.Figure()
        fig_cargo.add_trace(go.Bar(
            y=top_cargo['NOM_OFICIO'],
            x=top_cargo['TOTAL_ACTIVOS'],
            orientation='h',
            text=top_cargo['TOTAL_ACTIVOS'],
            texttemplate='%{text:,}',
            textposition='outside',
            marker=dict(color=COLORS['primary']),
            hovertemplate='<b>%{y}</b><br>Activos: %{x:,}<extra></extra>'
        ))
        fig_cargo.update_layout(
            title='🏆 Top 15 Cargos por Cantidad de Activos',
            xaxis_title='Total Activos',
            yaxis_title='',
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=450,
            margin=dict(l=250)
        )
        st.plotly_chart(fig_cargo, use_container_width=True)
    
    with c2:
        # Navegación entre variables para distribución
        st.markdown("#### 📊 Distribución por Variable")
        variable_sel = st.selectbox(
            "Seleccionar variable:",
            options=['TOTAL_ACTIVOS', 'TASA_ROTACION', 'TASA_AUSENTISMO', 'TASA_ACCIDENTALIDAD'],
            format_func=lambda x: {
                'TOTAL_ACTIVOS': '👥 Total Activos',
                'TASA_ROTACION': '🚪 Tasa de Rotación (%)',
                'TASA_AUSENTISMO': '😷 Tasa de Ausentismo (%)',
                'TASA_ACCIDENTALIDAD': '🚑 Tasa de Accidentalidad (%)'
            }[x],
            key="variable_cargo"
        )
        
        # Treemap según variable seleccionada
        top_20 = cargo_agg.nlargest(20, variable_sel)
        
        # Color según la variable
        if variable_sel == 'TOTAL_ACTIVOS':
            color_scale = ['#7fa8e0', '#1e3c72']
            titulo = 'Distribución de Activos por Cargo'
        elif variable_sel == 'TASA_ROTACION':
            color_scale = ['#fff3cd', '#dc3545']
            titulo = 'Distribución de Rotación por Cargo'
        elif variable_sel == 'TASA_AUSENTISMO':
            color_scale = ['#fff3cd', '#ffc107']
            titulo = 'Distribución de Ausentismo por Cargo'
        else:
            color_scale = ['#c8f7c5', '#28a745']
            titulo = 'Distribución de Accidentalidad por Cargo'
        
        fig_treemap = px.treemap(
            top_20,
            path=['NOM_OFICIO'],
            values=variable_sel,
            title=titulo,
            color=variable_sel,
            color_continuous_scale=color_scale
        )
        fig_treemap.update_layout(height=450)
        st.plotly_chart(fig_treemap, use_container_width=True)
    
    # Tabla de cargos
    st.markdown("#### 📋 Detalle de Cargos")
    cargo_table = cargo_agg.sort_values('TOTAL_ACTIVOS', ascending=False).head(20)
    st.dataframe(
        cargo_table.style.format({
            'TOTAL_ACTIVOS': '{:,.0f}',
            'RETIROS': '{:,.0f}',
            'TOTAL_AUSENTISMO': '{:,.0f}',
            'TOTAL_ACCIDENTES': '{:,.0f}',
            'TASA_ROTACION': '{:.1f}%',
            'TASA_AUSENTISMO': '{:.1f}%',
            'TASA_ACCIDENTALIDAD': '{:.1f}%'
        }),
        use_container_width=True,
        height=300
    )

st.markdown("---")

# ==========================
# TASAS POR ZONA
# ==========================
st.markdown("### 📊 Comparación de Tasas por Zona")

# Agregar por zona
zonas_tasas = df_f.groupby('ZONA').agg({
    'TOTAL_ACTIVOS': 'sum',
    'RETIROS': 'sum',
    'TOTAL_AUSENTISMO': 'sum',
    'TOTAL_ACCIDENTES': 'sum'
}).reset_index()

zonas_tasas['TASA_ROTACION'] = (zonas_tasas['RETIROS'] / zonas_tasas['TOTAL_ACTIVOS'].clip(lower=1) * 100).fillna(0)
zonas_tasas['TASA_AUSENTISMO'] = (zonas_tasas['TOTAL_AUSENTISMO'] / zonas_tasas['TOTAL_ACTIVOS'].clip(lower=1) * 100).fillna(0)
zonas_tasas['TASA_ACCIDENTALIDAD'] = (zonas_tasas['TOTAL_ACCIDENTES'] / zonas_tasas['TOTAL_ACTIVOS'].clip(lower=1) * 100).fillna(0)

# Gráfico comparativo de tasas por zona
fig_zonas = go.Figure()
fig_zonas.add_trace(go.Bar(
    name='Rotación %',
    x=zonas_tasas['ZONA'],
    y=zonas_tasas['TASA_ROTACION'],
    marker_color=COLORS['retiros'],
    text=zonas_tasas['TASA_ROTACION'].round(1),
    texttemplate='%{text}%',
    textposition='outside'
))
fig_zonas.add_trace(go.Bar(
    name='Ausentismo %',
    x=zonas_tasas['ZONA'],
    y=zonas_tasas['TASA_AUSENTISMO'],
    marker_color=COLORS['ausentismo'],
    text=zonas_tasas['TASA_AUSENTISMO'].round(1),
    texttemplate='%{text}%',
    textposition='outside'
))
fig_zonas.add_trace(go.Bar(
    name='Accidentalidad %',
    x=zonas_tasas['ZONA'],
    y=zonas_tasas['TASA_ACCIDENTALIDAD'],
    marker_color=COLORS['accidentes'],
    text=zonas_tasas['TASA_ACCIDENTALIDAD'].round(1),
    texttemplate='%{text}%',
    textposition='outside'
))
fig_zonas.update_layout(
    title='📈 Comparación de Tasas por Zona',
    barmode='group',
    xaxis_title='Zona',
    yaxis_title='Tasa (%)',
    plot_bgcolor='white',
    paper_bgcolor='white',
    height=450
)
st.plotly_chart(fig_zonas, use_container_width=True)

st.markdown("---")

# ==========================
# RETIROS POR RANGO DE PERMANENCIA
# ==========================
st.markdown("### 🔄 Retiros por Rango de Permanencia")
st.caption("*Solo se incluyen registros donde RETIROS >= 1*")

# Obtener datos con retiros
df_retiros = df_raw[(df_raw['MES'] == mes) & (df_raw['AÑO'] == año) & (df_raw['RETIROS'] >= 1)].copy()

if zona_seleccionada != "TODAS":
    df_retiros = df_retiros[df_retiros['ZONA'] == zona_seleccionada]

if not df_retiros.empty and 'RANGO_PERMANENCIA' in df_retiros.columns:
    # Agrupar por rango de permanencia
    rango_agg = df_retiros.groupby('RANGO_PERMANENCIA').agg({
        'RETIROS': 'sum',
        'TOTAL_ACTIVOS': 'sum',
        'ALMACEN': 'nunique'
    }).reset_index()
    
    rango_agg.columns = ['Rango de Permanencia', 'Total Retiros', 'Total Activos', 'Num Tiendas']
    
    # Ordenar rangos lógicamente
    orden_rangos = ['0-2 MESES', '2-4 MESES', '4-6 MESES', '6-12 MESES', 
                    'A1-2 AÑOS', 'A2-3 AÑOS', 'A3-4 AÑOS', 'A4-5 AÑOS', 'A5+ AÑOS']
    rango_agg['Orden'] = rango_agg['Rango de Permanencia'].map(
        {r: i for i, r in enumerate(orden_rangos) if r in rango_agg['Rango de Permanencia'].values}
    )
    rango_agg = rango_agg.dropna(subset=['Orden'])
    rango_agg = rango_agg.sort_values('Orden', ascending=True).drop('Orden', axis=1)
    
    # Solo gráfico de barras horizontales
    fig_rango = go.Figure()
    fig_rango.add_trace(go.Bar(
        y=rango_agg['Rango de Permanencia'],
        x=rango_agg['Total Retiros'],
        orientation='h',
        text=rango_agg['Total Retiros'],
        texttemplate='%{text:,}',
        textposition='outside',
        marker=dict(
            color=rango_agg['Total Retiros'],
            colorscale=[[0, COLORS['accent']], [1, COLORS['danger']]]
        ),
        hovertemplate='<b>%{y}</b><br>Retiros: %{x:,}<extra></extra>'
    ))
    fig_rango.update_layout(
        title='📊 Retiros por Rango de Permanencia',
        xaxis_title='Total Retiros',
        yaxis_title='Rango de Permanencia',
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=400,
        margin=dict(l=120)
    )
    st.plotly_chart(fig_rango, use_container_width=True)
    
    # Análisis por cargo y rango de permanencia
    st.markdown("#### 👔 Top 10 Cargos con Más Retiros por Rango de Permanencia")
    rango_cargo = df_retiros.groupby(['NOM_OFICIO', 'RANGO_PERMANENCIA']).agg({
        'RETIROS': 'sum'
    }).reset_index()
    
    if not rango_cargo.empty:
        top_cargos_retiro = rango_cargo.groupby('NOM_OFICIO')['RETIROS'].sum().nlargest(10).index
        rango_cargo_top = rango_cargo[rango_cargo['NOM_OFICIO'].isin(top_cargos_retiro)]
        
        # Pivot para visualización más clara
        rango_pivot = rango_cargo_top.pivot(index='NOM_OFICIO', columns='RANGO_PERMANENCIA', values='RETIROS').fillna(0)
        
        # Reordenar columnas según orden lógico
        cols_orden = [c for c in orden_rangos if c in rango_pivot.columns]
        rango_pivot = rango_pivot[cols_orden]
        
        # Gráfico de barras apiladas horizontal
        fig_rango_cargo = go.Figure()
        
        colores_rango = px.colors.qualitative.Set3[:len(cols_orden)]
        
        for i, rango in enumerate(cols_orden):
            fig_rango_cargo.add_trace(go.Bar(
                name=rango,
                y=rango_pivot.index,
                x=rango_pivot[rango],
                orientation='h',
                marker_color=colores_rango[i],
                text=rango_pivot[rango].astype(int),
                texttemplate='%{text}' if rango_pivot[rango].max() > 0 else '',
                textposition='inside'
            ))
        
        fig_rango_cargo.update_layout(
            title='Distribución de Retiros por Cargo y Rango de Permanencia',
            barmode='stack',
            xaxis_title='Total Retiros',
            yaxis_title='Cargo',
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=500,
            margin=dict(l=250),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        st.plotly_chart(fig_rango_cargo, use_container_width=True)
        
        # Tabla resumen
        st.markdown("#### 📊 Resumen por Cargo y Permanencia")
        rango_cargo_display = rango_cargo_top.copy()
        rango_cargo_display = rango_cargo_display.sort_values(['NOM_OFICIO', 'RETIROS'], ascending=[True, False])
        st.dataframe(
            rango_cargo_display.style.format({'RETIROS': '{:,.0f}'}),
            use_container_width=True,
            height=250
        )
else:
    st.info("ℹ️ No hay retiros registrados para el período y zona seleccionados.")

st.markdown("---")

# ==========================
# MAPA GEOGRÁFICO
# ==========================
st.markdown("### 🗺️ Vista Geográfica")

# Filtrar solo datos con coordenadas válidas para el mapa
df_map_full = df_f.copy()
df_map = df_map_full.dropna(subset=['LATITUD', 'LONGITUD'])

# Verificar que las coordenadas estén en rangos válidos (Colombia aprox)
df_map = df_map[
    (df_map['LATITUD'] > -5) & (df_map['LATITUD'] < 15) &
    (df_map['LONGITUD'] > -80) & (df_map['LONGITUD'] < -65)
]

if len(df_map) == 0:
    st.warning("⚠️ No hay coordenadas válidas para mostrar en el mapa.")
else:
    st.success(f"✅ Mostrando {len(df_map)} ubicaciones con coordenadas válidas")
    
    col_map, col_cfg = st.columns([4, 1])

    with col_cfg:
        st.markdown("#### ⚙️ Configuración")
        metrica_mapa = st.selectbox(
            "Métrica",
            ['Total Activos','Tasa Rotación','Tasa Ausentismo','Tasa Accidentalidad',
             'Días Ausencia','Horas Ausentismo'],
            key="metrica_mapa"
        )
        tamaño_base   = st.slider("Tamaño base", 3, 15, 6,  key="tam_mapa")
        factor_escala = st.slider("Escala",      0.1, 2.0, 0.4, step=0.1, key="esc_mapa")
        mostrar_capa  = st.checkbox("Mostrar capa geográfica", value=False)

        st.markdown("---")
        st.caption(f"📍 Puntos: {len(df_map)}")
        st.caption(f"🌍 Zonas: {df_map['ZONA'].nunique()}")

    with col_map:
        COL_MAP = {
            'Total Activos':       ('TOTAL_ACTIVOS',      COLORS['primary']),
            'Tasa Rotación':       ('TASA_ROTACION',      COLORS['retiros']),
            'Tasa Ausentismo':     ('TASA_AUSENTISMO',    COLORS['ausentismo']),
            'Tasa Accidentalidad': ('TASA_ACCIDENTALIDAD',COLORS['accidentes']),
            'Días Ausencia':       ('DIAS_AUSENCIA',      COLORS['aus_medico']),
            'Horas Ausentismo':    ('HORAS_AUSENTISMO',   COLORS['info']),
        }
        col_val, color_base = COL_MAP[metrica_mapa]

        # Centro del mapa basado en coordenadas promedio
        centro_lat = df_map['LATITUD'].mean()
        centro_lon = df_map['LONGITUD'].mean()
        
        m = folium.Map(
            location=[centro_lat, centro_lon], 
            zoom_start=6,
            tiles='CartoDB positron', 
            control_scale=True, 
            prefer_canvas=True
        )

        if mostrar_capa:
            gdf = load_geojson()
            if gdf is not None:
                folium.GeoJson(gdf, name='Capa Geográfica',
                               style_function=lambda x: {
                                   'fillColor': '#7fa8e0', 'color': '#1e3c72',
                                   'weight': 2, 'fillOpacity': 0.2
                               }).add_to(m)

        zonas_u = df_map['ZONA'].dropna().unique()
        col_zona = {z: CHART_COLORS[i % len(CHART_COLORS)] for i, z in enumerate(zonas_u)}

        for _, row in df_map.iterrows():
            valor  = row.get(col_val, 0)
            radio  = max(tamaño_base, float(valor) * factor_escala)
            color  = col_zona.get(row['ZONA'], color_base)
            alerta = (row['TASA_ROTACION'] >= 10 or
                      row['TASA_AUSENTISMO'] >= 15 or
                      row['TASA_ACCIDENTALIDAD'] >= 5)

            popup_html = f"""
            <div style="font-family:Arial; min-width:270px;">
                <h4 style="margin:0;color:{COLORS['primary']};">{'🚨 ' if alerta else ''}{row['ALMACEN']}</h4>
                <hr style="margin:5px 0;">
                <table style="width:100%;font-size:12px;">
                    <tr><td>📍 Zona:</td>   <td><b>{row['ZONA']}</b></td></tr>
                    <tr><td colspan=2><hr style="margin:2px 0;"></td></tr>
                    <tr><td>👥 Activos:</td>  <td><b>{int(row['TOTAL_ACTIVOS'])}</b></td></tr>
                    <tr><td>🚪 Retiros:</td>  <td><b>{int(row['RETIROS'])} ({row['TASA_ROTACION']:.1f}%)</b></td></tr>
                    <tr><td>😷 Ausentismo:</td><td><b>{int(row['TOTAL_AUSENTISMO'])} ({row['TASA_AUSENTISMO']:.1f}%)</b></td></tr>
                    <tr><td>  ↳ Médico:</td>  <td>{int(row.get('AUS_MEDICO',0))}</td></tr>
                    <tr><td>  ↳ Legal:</td>   <td>{int(row.get('AUS_LEG',0))}</td></tr>
                    <tr><td>  ↳ Admin:</td>   <td>{int(row.get('AUS_ADMINISTRATIVO',0))}</td></tr>
                    <tr><td>📅 Días aus.:</td> <td><b>{int(row.get('DIAS_AUSENCIA',0))}</b></td></tr>
                    <tr><td>⏱️ Horas aus.:</td><td><b>{int(row.get('HORAS_AUSENTISMO',0))}</b></td></tr>
                    <tr><td>🚑 Accidentes:</td><td><b>{int(row['TOTAL_ACCIDENTES'])} ({row['TASA_ACCIDENTALIDAD']:.1f}%)</b></td></tr>
                    <tr><td colspan=2 style="padding-top:5px;">📅 <i>{row['MES']} {row['AÑO']}</i></td></tr>
                </table>
            </div>"""

            folium.CircleMarker(
                location=[row['LATITUD'], row['LONGITUD']],
                radius=radio,
                popup=folium.Popup(popup_html, max_width=320),
                color=color, fill=True, fill_color=color,
                fill_opacity=0.7, weight=2,
                tooltip=f"{row['ALMACEN']} – {metrica_mapa}: {valor:.1f}"
            ).add_to(m)

        folium.LayerControl().add_to(m)
        st_folium(m, width=None, height=600, returned_objects=[])

st.markdown("---")

# ==========================
# TABLA DE DATOS DETALLADA
# ==========================
st.markdown("### 📋 Datos Detallados por Tienda")

all_cols = [
    'ALMACEN','ZONA','TOTAL_ACTIVOS','RETIROS','TOTAL_AUSENTISMO',
    'AUS_MEDICO','AUS_LEG','AUS_ADMINISTRATIVO',
    'DIAS_AUSENCIA','HORAS_AUSENTISMO',
    'TOTAL_ACCIDENTES','TASA_ROTACION','TASA_AUSENTISMO','TASA_ACCIDENTALIDAD',
    'TASA_ROTACION_MENSUAL','TASA_ROTACION_ACT_MES_ANT','FECHA'
]
existing_cols = [c for c in all_cols if c in df_f.columns]
default_cols  = [c for c in ['ALMACEN','ZONA','TOTAL_ACTIVOS','RETIROS',
                              'TOTAL_AUSENTISMO','AUS_MEDICO','AUS_LEG',
                              'AUS_ADMINISTRATIVO','DIAS_AUSENCIA','TOTAL_ACCIDENTES']
                 if c in existing_cols]

tc1, tc2, tc3 = st.columns(3)
with tc1:
    mostrar_cols = st.multiselect("Columnas", options=existing_cols,
                                   default=default_cols, key="cols_tabla")
with tc2:
    n_reg = st.selectbox("Registros", [10, 25, 50, 100, "Todos"], index=1, key="n_tabla")
with tc3:
    sort_opts = [c for c in ['TOTAL_ACTIVOS','TASA_ROTACION','TASA_AUSENTISMO',
                               'TASA_ACCIDENTALIDAD','ALMACEN'] if c in df_f.columns]
    sort_col  = st.selectbox("Ordenar por", sort_opts, key="sort_tabla")
    asc       = st.checkbox("Ascendente", value=False, key="asc_tabla")

if mostrar_cols:
    tabla = df_f[mostrar_cols].sort_values(sort_col, ascending=asc)
    if n_reg != "Todos":
        tabla = tabla.head(int(n_reg))

    col_cfg_table = {
        "ALMACEN":               st.column_config.TextColumn("🏪 Tienda",         width="medium"),
        "ZONA":                  st.column_config.TextColumn("📍 Zona",            width="small"),
        "TOTAL_ACTIVOS":         st.column_config.NumberColumn("👥 Activos",       format="%d"),
        "RETIROS":               st.column_config.NumberColumn("🚪 Retiros",       format="%d"),
        "TOTAL_AUSENTISMO":      st.column_config.NumberColumn("😷 Aus. Total",    format="%d"),
        "AUS_MEDICO":            st.column_config.NumberColumn("🏥 Médico",        format="%d"),
        "AUS_LEG":               st.column_config.NumberColumn("⚖️ Legal",         format="%d"),
        "AUS_ADMINISTRATIVO":    st.column_config.NumberColumn("🗂️ Admin",         format="%d"),
        "DIAS_AUSENCIA":         st.column_config.NumberColumn("📅 Días",          format="%d"),
        "HORAS_AUSENTISMO":      st.column_config.NumberColumn("⏱️ Horas",         format="%.0f"),
        "TOTAL_ACCIDENTES":      st.column_config.NumberColumn("🚑 Accidentes",    format="%d"),
        "TASA_ROTACION":         st.column_config.NumberColumn("% Rotación",       format="%.1f%%"),
        "TASA_AUSENTISMO":       st.column_config.NumberColumn("% Ausentismo",     format="%.1f%%"),
        "TASA_ACCIDENTALIDAD":   st.column_config.NumberColumn("% Accidentalidad", format="%.1f%%"),
        "TASA_ROTACION_MENSUAL": st.column_config.NumberColumn("% Rot. Mensual",   format="%.1f%%"),
        "TASA_ROTACION_ACT_MES_ANT": st.column_config.NumberColumn("% Rot. Mes Ant.", format="%.1f%%"),
        "FECHA":                 st.column_config.TextColumn("📅 Período"),
    }

    st.dataframe(tabla, use_container_width=True, hide_index=True,
                 column_config=col_cfg_table, height=400)
    st.caption(f"📊 Mostrando {len(tabla):,} de {len(df_f):,} registros filtrados | Total general: {len(df):,}")

# ==========================
# FOOTER
# ==========================
st.markdown("---")
st.markdown(f"""
<div style="text-align:center; padding:20px;
            background:linear-gradient(135deg,{COLORS['gradient_start']} 0%,{COLORS['gradient_end']} 100%);
            color:white; border-radius:10px;">
    <h4>📊 Dashboard Obeya Comercial 2026</h4>
    <p style="margin:5px 0;">
        <b>Generado:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} |
        <b>Período:</b> {mes} {año} |
        <b>Zona:</b> {zona_seleccionada} |
        <b>Registros:</b> {len(df_f):,} de {len(df):,}
    </p>
    <p style="margin:5px 0; font-size:0.9em;">
        CSV → Procesamiento → Visualización Interactiva
    </p>
</div>
""", unsafe_allow_html=True)
