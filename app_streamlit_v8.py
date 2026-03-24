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
    page_title="Obeya Comercial",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================
# PALETA DE COLORES CORPORATIVA
# ==========================
COLORS = {
    'primary':        '#1e3c72',   # azul oscuro
    'secondary':      '#6e6e6e',   # gris medio
    'accent':         '#7fa8e0',   # azul claro
    'success':        '#28a745',
    'warning':        '#5a5a5a',   # gris oscuro
    'danger':         '#4a4a4a',   # gris más oscuro
    'info':           '#17a2b8',
    'light':          '#f0f0f0',
    'dark':           '#343a40',
    'gradient_start': '#1e3c72',
    'gradient_end':   '#2a5298',
    'retiros':        "#9bf8d1",
    'ausentismo':     "#1335f7",
    'accidentes':     "#8a8a8a",
    'aus_medico':     '#7fa8e0',
    'aus_legal':      "#2683ee",
    'aus_admin':      "#051031",
}

CHART_COLORS = ['#1e3c72', '#6e6e6e', '#7fa8e0', '#8a8a8a', '#5a5a5a', '#4a4a4a']

# ==========================
# CONFIGURACIÓN DE RUTAS
# ==========================
import os
CSV_PATH          = os.environ.get('CSV_PATH', 'data/data.csv')
NOMINA_PATH       = os.environ.get('NOMINA_PATH', 'data/CONSOLIDADO_NOMINA.csv')
AUTORIZACION_PATH = os.environ.get('AUTORIZACION_PATH', 'data/AUTORIZACION.csv')
GEOJSON_PATH      = os.environ.get('GEODATA_PATH', 'geodata')

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
    .meta-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1rem 1.2rem;
        border-radius: 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        border-left: 5px solid #1e3c72;
        margin-bottom: 0.5rem;
    }
    .meta-card.alerta {
        border-left-color: #dc3545;
        background: linear-gradient(135deg, #fff5f5 0%, #ffe0e0 100%);
    }
    .meta-card.ok {
        border-left-color: #28a745;
        background: linear-gradient(135deg, #f0fff4 0%, #d4edda 100%);
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

# Mapeo MES plano → formato data.csv (usado por load_autorizacion)
_MES_AUTH_MAP = {
    'ENERO': '01. ENERO', 'FEBRERO': '02. FEBRERO', 'MARZO': '03. MARZO',
    'ABRIL': '04. ABRIL', 'MAYO': '05. MAYO', 'JUNIO': '06. JUNIO',
    'JULIO': '07. JULIO', 'AGOSTO': '08. AGOSTO', 'SEPTIEMBRE': '09. SEPTIEMBRE',
    'OCTUBRE': '10. OCTUBRE', 'NOVIEMBRE': '11. NOVIEMBRE', 'DICIEMBRE': '12. DICIEMBRE',
}

@st.cache_data(ttl=600, show_spinner=False)
def load_autorizacion():
    """
    Carga AUTORIZACION.csv y retorna un DataFrame con PLAZAS_AUTORIZADAS_ORIG
    sumadas por (_TIENDA, _CARGO, MES, AÑO), donde:
      - _TIENDA = CENTRO DE COSTOS normalizado (sin tildes, sin espacios extra)
      - _CARGO  = NOMBRE DEL CARGO normalizado (sin tildes, espacios internos colapsados)
      - MES     = convertido a formato '01. ENERO' para coincidir con data.csv
      - AÑO     = int

    Join con data.csv  : _TIENDA ↔ NOM_CCOSTO  |  _CARGO ↔ NOM_OFICIO
    Join con nómina.csv: _TIENDA ↔ NOM CCO     |  _CARGO ↔ OFICIO
    """
    import unicodedata, re

    def norm(s):
        """Strip, upper, quita tildes y colapsa espacios internos múltiples."""
        s = str(s).strip().upper()
        s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
        return re.sub(r'\s+', ' ', s)

    for path in [AUTORIZACION_PATH, 'AUTORIZACION.csv']:
        try:
            df = pd.read_csv(path, encoding='utf-8-sig', sep=None, engine='python')
            break
        except FileNotFoundError:
            continue
    else:
        return pd.DataFrame(columns=['_TIENDA', '_CARGO', 'MES', 'AÑO', 'PLAZAS_AUTORIZADAS_ORIG'])

    df.columns = df.columns.str.strip()

    df['_TIENDA'] = df['CENTRO DE COSTOS'].apply(norm)
    df['_CARGO']  = df['NOMBRE DEL CARGO'].apply(norm)
    df['MES']     = (df['MES'].astype(str).str.strip().str.upper()
                     .map(_MES_AUTH_MAP)
                     .fillna(df['MES'].astype(str).str.strip().str.upper()))
    df['AÑO']     = pd.to_numeric(df['AÑO'], errors='coerce').astype('Int64')
    df['PLAZAS_AUTORIZADAS_ORIG'] = pd.to_numeric(
        df['PLAZAS AUTORIZADAS Orig'].astype(str)
          .str.replace(',', '.', regex=False).str.strip(),
        errors='coerce'
    ).fillna(0)

    return (
        df.groupby(['_TIENDA', '_CARGO', 'MES', 'AÑO'], dropna=False)['PLAZAS_AUTORIZADAS_ORIG']
        .sum()
        .reset_index()
    )


def get_personal_autorizado(mes: str, año: int, almacenes_activos=None, cargos_activos=None) -> int:
    """
    Suma PLAZAS_AUTORIZADAS_ORIG filtrando por (mes, año) y opcionalmente
    por las tiendas y cargos presentes en df_f (respeta todos los filtros activos).

    - almacenes_activos : lista de ALMACEN del df_f filtrado (NOM_CCOSTO renombrado)
    - cargos_activos    : lista de NOM_OFICIO del df_raw_f filtrado
    """
    import unicodedata, re

    def norm(s):
        s = str(s).strip().upper()
        s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
        return re.sub(r'\s+', ' ', s)

    df_auth = load_autorizacion()
    if df_auth.empty:
        return 0

    mask = (df_auth['MES'] == mes) & (df_auth['AÑO'] == año)

    if almacenes_activos is not None:
        keys_tienda = {norm(a) for a in almacenes_activos}
        mask &= df_auth['_TIENDA'].isin(keys_tienda)

    if cargos_activos is not None:
        keys_cargo = {norm(c) for c in cargos_activos}
        mask &= df_auth['_CARGO'].isin(keys_cargo)

    return int(df_auth.loc[mask, 'PLAZAS_AUTORIZADAS_ORIG'].sum())

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
        df = pd.read_csv(CSV_PATH, encoding='utf-8-sig', sep=';')

        df.columns = (
            df.columns
            .str.strip()
            .str.upper()
            .str.replace(' ', '_', regex=False)
        )

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
            'CONTRATO':                'TIPO_CONTRATO',
        }
        df.rename(columns={k: v for k, v in rename.items() if k in df.columns}, inplace=True)

        # Coordenadas
        for col in ['LATITUD', 'LONGITUD']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Tasas
        if 'TASA_ROTACION_MENSUAL' in df.columns:
            df['TASA_ROTACION_MENSUAL'] = parse_pct(df['TASA_ROTACION_MENSUAL'])
        if 'TASA_ROTACION_ACT_MES_ANT' in df.columns:
            df['TASA_ROTACION_ACT_MES_ANT'] = parse_pct(df['TASA_ROTACION_ACT_MES_ANT'])
        if 'TASA_DE_ACCIDENTALIDAD' in df.columns:
            df['TASA_DE_ACCIDENTALIDAD'] = parse_pct(df['TASA_DE_ACCIDENTALIDAD'])
        if 'HORAS_TRABAJADAS' in df.columns:
            df['HORAS_TRABAJADAS'] = parse_num(df['HORAS_TRABAJADAS'])

        # Metas (almacenadas como porcentaje decimal, ej: 0,034)
        for col in ['META_ROT_GRAL', 'META_AUSENTISMO', 'META_AUSENTISMO_LEGAL',
                    'META_AUSENTISMO_MEDICO', 'META_AUSENTISMO_ADMINITRATIVO']:
            if col in df.columns:
                df[col] = parse_pct(df[col])  # convierte coma→punto, queda como float ya multiplicado x100 desde parse_pct
                # parse_pct no multiplica: 0,034 → 0.034, ya está en decimal. Lo convertimos a %
                # Actually parse_pct solo limpia texto, no multiplica. 0,034 → 0.034
                # Multiplicamos x100 para tener porcentaje
                df[col] = df[col] * 100

        # Numéricas directas
        for col in ['TOTAL_ACTIVOS', 'RETIROS', 'TOTAL_AUSENTISMO', 'TOTAL_ACCIDENTES',
                    'AUS_LEG', 'AUS_ADMINISTRATIVO',
                    'DIAS_ADMIN', 'DIAS_LEGAL', 'DIAS_MEDICO', 'DIAS_AUSENCIA', 'HORAS_AUSENTISMO']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        if 'COLOR_AUS_MED' in df.columns:
            df['AUS_MEDICO'] = df['COLOR_AUS_MED'].apply(
                lambda x: 1 if str(x) != '#37A794' and pd.notna(x) else 0
            )

        df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce').astype('Int64')
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
        'META_ROT_GRAL':            ('META_ROT_GRAL',           'mean'),
        'META_AUSENTISMO':          ('META_AUSENTISMO',         'mean'),
        'META_AUSENTISMO_LEGAL':    ('META_AUSENTISMO_LEGAL',   'mean'),
        'META_AUSENTISMO_MEDICO':   ('META_AUSENTISMO_MEDICO',  'mean'),
        'META_AUSENTISMO_ADMINITRATIVO': ('META_AUSENTISMO_ADMINITRATIVO', 'mean'),
    }
    agg_dict = {k: v for k, v in agg_dict.items() if v[0] in df.columns}

    df = df.groupby(group_cols, dropna=False).agg(**agg_dict).reset_index()

    activos = df['TOTAL_ACTIVOS'].clip(lower=1)
    df['TASA_ROTACION']      = (df['RETIROS'] / activos * 100).fillna(0)
    df['TASA_AUSENTISMO']    = (df['TOTAL_AUSENTISMO'] / activos * 100).fillna(0)
    df['TASA_ACCIDENTALIDAD']= (df['TOTAL_ACCIDENTES'] / activos * 100).fillna(0)

    df['FECHA'] = df['MES'].map(MES_ORDEN).astype(str) + '/' + df['AÑO'].astype(str)

    # ── Join con nómina (DEVENGADOS por almacén) ──────────────────────
    import unicodedata
    def _norm(s):
        s = str(s).strip().upper()
        return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')

    try:
        nomina_almacen, _ = load_nomina()
        if not nomina_almacen.empty:
            # Clave normalizada en df procesado (ALMACEN ya viene renombrado de load_csv)
            df['_KEY'] = df['ALMACEN'].apply(_norm)
            # nomina_almacen ya trae la columna ALMACEN normalizada (viene de load_nomina)
            nomina_almacen = nomina_almacen.rename(columns={'ALMACEN': '_KEY'})
            nomina_almacen['AÑO'] = nomina_almacen['AÑO'].astype('Int64')
            df = df.merge(
                nomina_almacen[['_KEY', 'MES', 'AÑO', 'DEVENGADOS_ALMACEN']],
                on=['_KEY', 'MES', 'AÑO'],
                how='left'
            )
            df['DEVENGADOS_ALMACEN'] = df['DEVENGADOS_ALMACEN'].fillna(0)
            df.drop(columns=['_KEY'], inplace=True)
    except Exception:
        df['DEVENGADOS_ALMACEN'] = 0

    # Número de tiendas (se calcula externamente)
    return df


@st.cache_data(ttl=600, show_spinner=False)
def load_nomina():
    """
    Carga CONSOLIDADO_NOMINA.csv y devuelve dos DataFrames agregados con
    DEVENGADOS sumados por (ALMACEN, MES, AÑO) y por (OFICIO, MES, AÑO).

    La columna MES ya viene en formato '01. ENERO', igual que data.csv,
    por lo que el join es directo sin transformación.

    Normalización de claves:
      - ALMACEN ← NOM CCO  (strip + upper + quitar tildes para robustecer el match)
      - OFICIO  ← OFICIO   (strip + upper)
    """
    import unicodedata

    def norm(s):
        """Strip, upper y elimina tildes/caracteres especiales para join robusto."""
        s = str(s).strip().upper()
        return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')

    try:
        df = pd.read_csv(NOMINA_PATH, encoding='utf-8-sig', sep=';')
    except FileNotFoundError:
        try:
            df = pd.read_csv('CONSOLIDADO_NOMINA.csv', encoding='utf-8-sig', sep=';')
        except FileNotFoundError:
            return pd.DataFrame(), pd.DataFrame()

    df.columns = df.columns.str.strip().str.upper()

    df['ALMACEN']    = df['NOM CCO'].apply(norm)
    df['OFICIO']     = df['OFICIO'].apply(norm)
    df['MES']        = df['MES'].astype(str).str.strip().str.upper()
    df['AÑO']        = pd.to_numeric(df['AÑO'], errors='coerce').astype('Int64')
    df['DEVENGADOS'] = pd.to_numeric(
        df['DEVENGADOS'].astype(str).str.replace(',', '.', regex=False),
        errors='coerce'
    ).fillna(0)

    # Agregado por almacén + mes + año
    nomina_almacen = (
        df.groupby(['ALMACEN', 'MES', 'AÑO'], dropna=False)['DEVENGADOS']
        .sum()
        .reset_index()
        .rename(columns={'DEVENGADOS': 'DEVENGADOS_ALMACEN'})
    )

    # Agregado por oficio + mes + año
    nomina_oficio = (
        df.groupby(['OFICIO', 'MES', 'AÑO'], dropna=False)['DEVENGADOS']
        .sum()
        .reset_index()
        .rename(columns={'DEVENGADOS': 'DEVENGADOS_OFICIO'})
    )

    return nomina_almacen, nomina_oficio


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
    <h1>📊 Obeya Comercial</h1>
    <h3>🎯 Cobertura y Gestión de Personal</h3>
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
    st.metric("🔄 Rotaciones",  f"{int(df['RETIROS'].sum()):,}")
    st.metric("😷 Ausentismo",  f"{int(df['TOTAL_AUSENTISMO'].sum()):,}")
    st.metric("🚑 Accidentes",  f"{int(df['TOTAL_ACCIDENTES'].sum()):,}")
    st.metric("📅 Días ausencia", f"{int(df['DIAS_AUSENCIA'].sum()):,}")

    st.markdown("---")
    st.markdown("#### 🔍 Filtros Avanzados")

    # Filtro de zonas
    zonas   = ['TODAS'] + sorted(df['ZONA'].dropna().unique().tolist())
    zona_sel = st.selectbox("🌍 Zona", zonas, key="zona_select")

    # Filtro de tiendas
    st.markdown("#### 🏪 Filtro de Tiendas")
    tiendas = ['TODAS'] + sorted(df['ALMACEN'].dropna().unique().tolist())
    tienda_sel = st.selectbox("Tienda/CCosto", tiendas, key="tienda_select")

    # Filtro de tipo de contrato
    st.markdown("#### 📄 Tipo de Contrato")
    CONTRATO_MAP = {
        'OBRA O LABOR': [
            'OBRA LABOR C OPERATIVO',
            'OBRA O LABOR AD/PRO/LOG',
            'OBRA O LABOR C OPERATIVO TEMPO',
        ],
        'TERMINO INDEFINIDO': [
            'TERMINO INDEFINIDO C OPERATIVO',
            'TERMINO INDEFINIDO COMERCIAL',
        ],
        'TERMINO FIJO': [
            'FIJO A 3 MESES COMERCIAL',
            'FIJO 6 MESES COMERCIAL',
            'FIJO 6 MESES C OPERATIVO',
            'FIJO OPERATIVO FINSEMANERO',
            'TERMINO FIJO ADMON/PRO/LOG 6',
        ],
    }
    tipo_contrato_opciones = ['TODOS'] + list(CONTRATO_MAP.keys())
    contrato_tipo_sel = st.multiselect(
        "Contrato",
        options=tipo_contrato_opciones,
        default=['TODOS'],
        key="contrato_tipo_sel"
    )
    # Resolver los contratos reales seleccionados
    if not contrato_tipo_sel or 'TODOS' in contrato_tipo_sel:
        contrato_sel = list({v for vals in CONTRATO_MAP.values() for v in vals})
    else:
        contrato_sel = [v for t in contrato_tipo_sel for v in CONTRATO_MAP.get(t, [])]

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
# ZONA SELECCIONADA (sin radio, siempre TODAS para el contexto del AI)
# ==========================
zona_seleccionada = "TODAS"
df_zona = df.copy()

# ==========================
# APLICAR FILTROS ADICIONALES
# ==========================
df_f = df_zona.copy()

if zona_sel != 'TODAS' and zona_seleccionada == "TODAS":
    df_f = df_f[df_f['ZONA'] == zona_sel]

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

# Filtrar df_raw para secciones que usan datos crudos
df_raw_f = df_raw[(df_raw['MES'] == mes) & (df_raw['AÑO'] == año)].copy()
if zona_seleccionada != "TODAS":
    df_raw_f = df_raw_f[df_raw_f['ZONA'] == zona_seleccionada]
if tienda_sel != 'TODAS':
    df_raw_f = df_raw_f[df_raw_f['ALMACEN'] == tienda_sel]
if contrato_sel and 'TIPO_CONTRATO' in df_raw_f.columns:
    df_raw_f = df_raw_f[df_raw_f['TIPO_CONTRATO'].isin(contrato_sel)]

# ==========================
# KPIs PRINCIPALES - INDICADORES DE RECURSOS HUMANOS
# ==========================
st.markdown("### 📈 Indicadores de Recursos Humanos")

total_act   = int(df_f['TOTAL_ACTIVOS'].sum())
total_rot   = int(df_f['RETIROS'].sum())
total_aus   = int(df_f['TOTAL_AUSENTISMO'].sum())
total_acc   = int(df_f['TOTAL_ACCIDENTES'].sum())
total_dias  = int(df_f['DIAS_AUSENCIA'].sum())
num_tiendas = int(df_f['ALMACEN'].nunique())
aus_admin   = int(df_f['AUS_ADMINISTRATIVO'].sum()) if 'AUS_ADMINISTRATIVO' in df_f.columns else 0
aus_leg     = int(df_f['AUS_LEG'].sum()) if 'AUS_LEG' in df_f.columns else 0
aus_med     = int(df_f['AUS_MEDICO'].sum()) if 'AUS_MEDICO' in df_f.columns else 0
dias_admin  = int(df_f['DIAS_ADMIN'].sum()) if 'DIAS_ADMIN' in df_f.columns else 0
dias_leg    = int(df_f['DIAS_LEGAL'].sum()) if 'DIAS_LEGAL' in df_f.columns else 0
dias_med    = int(df_f['DIAS_MEDICO'].sum()) if 'DIAS_MEDICO' in df_f.columns else 0

# ── SUBSECCIÓN 1: Fuerza laboral ─────────────────────────────
st.markdown("#### 👥 Datos Generales")
k1, k2, k3, k4 = st.columns(4)
k1.metric("🏪 Nº Tiendas",            f"{num_tiendas:,}")

# Personal autorizado — filtrado por tienda + cargo + mes + año
_almacenes_filtrados = df_f['ALMACEN'].dropna().unique().tolist()
_cargos_filtrados    = df_raw_f['NOM_OFICIO'].dropna().unique().tolist() if 'NOM_OFICIO' in df_raw_f.columns else None
_pers_aut = get_personal_autorizado(mes, int(año),
                                     almacenes_activos=_almacenes_filtrados,
                                     cargos_activos=_cargos_filtrados)
_vacantes = _pers_aut - total_act

k2.metric("✅ Personal Autorizado",
          f"{_pers_aut:,}" if _pers_aut > 0 else "Sin datos",
          help="Suma de PLAZAS AUTORIZADAS Orig desde AUTORIZACION.csv")
k3.metric("👥 Personal Activo",       f"{total_act:,}")

if _pers_aut > 0:
    k4.metric(
        "📋 Vacantes",
        f"{_vacantes:,}",
        delta=f"{'↑' if _vacantes >= 0 else '↓'} {abs(_vacantes):,} vs autorizado",
        delta_color="normal" if _vacantes >= 0 else "inverse",
        help="Personal Autorizado − Personal Activo. Rojo = exceso de personal."
    )
else:
    k4.metric("📋 Vacantes", "Sin datos",
              help="No hay plazas autorizadas definidas para este período")

st.markdown("---")

# ── SUBSECCIÓN 2: Costo de Nómina ────────────────────────────
st.markdown("#### 💰 Costo de la Nómina")

# Costo mes actual: suma de DEVENGADOS_ALMACEN del df filtrado
costo_mes = int(df_f['DEVENGADOS_ALMACEN'].sum()) if 'DEVENGADOS_ALMACEN' in df_f.columns else 0

# Acumulado año: sumar todos los meses del mismo año en df_raw con join nómina
costo_acum = 0
try:
    nomina_almacen_raw, _ = load_nomina()
    if not nomina_almacen_raw.empty:
        import unicodedata
        def _norm(s):
            s = str(s).strip().upper()
            return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
        nomina_almacen_raw['AÑO'] = nomina_almacen_raw['AÑO'].astype('Int64')
        costo_acum = int(
            nomina_almacen_raw[nomina_almacen_raw['AÑO'] == int(año)]['DEVENGADOS_ALMACEN'].sum()
        )
except Exception:
    costo_acum = 0

cn1, cn2, cn3 = st.columns(3)
cn1.metric("🎯 Meta",               "🚧")
if costo_mes > 0:
    cn2.metric("📅 Costo Mes Actual",
               f"${costo_mes / 1_000_000:,.0f} Mill",
               help="Suma de DEVENGADOS del período seleccionado")
else:
    cn2.metric("📅 Costo Mes Actual", "Sin datos")
if costo_acum > 0:
    cn3.metric("📆 Acumulado Año",
               f"${costo_acum / 1_000_000:,.0f} Mill",
               help=f"Suma de DEVENGADOS todos los meses disponibles en {año}")
else:
    cn3.metric("📆 Acumulado Año", "Sin datos")

st.markdown("---")

# ── SUBSECCIÓN 4: Ausentismo ─────────────────────────────────
st.markdown("#### 😷 Ausentismo")
a1, a2, a3, a4, a5, a6, a7 = st.columns(7)
a1.metric("📊 Nº Ausencias",         f"{total_aus:,}")
a2.metric("🗂️ Administrativo",       f"{aus_admin:,}")
a3.metric("⚖️ Legal",                f"{aus_leg:,}")
a4.metric("🏥 Médico",               f"{aus_med:,}")
a5.metric("📅 Días (Admin)",         f"{dias_admin:,}")
a6.metric("📅 Días (Legal)",         f"{dias_leg:,}")
a7.metric("📅 Días (Médico)",        f"{dias_med:,}")

st.markdown("---")

# ── SUBSECCIÓN 5: Accidentalidad ─────────────────────────────
st.markdown("#### 🚑 Accidentalidad")
acc1, acc2, acc3 = st.columns(3)
acc1.metric("🚑 Nº Accidentes",  f"{total_acc:,}")
# Frecuencia = accidentes / horas trabajadas * 240000 (estándar)
horas_trab = df_f['HORAS_TRABAJADAS'].sum() if 'HORAS_TRABAJADAS' in df_f.columns else 0
if horas_trab > 0:
    frecuencia = (total_acc / horas_trab) * 240000
    severidad  = (total_dias / horas_trab) * 240000
else:
    frecuencia = 0.0
    severidad  = 0.0
acc2.metric("📈 Frecuencia",     f"{frecuencia:.2f}",
            help="Accidentes / Horas trabajadas × 240.000")
acc3.metric("📉 Severidad",      f"{severidad:.2f}",
            help="Días de ausencia / Horas trabajadas × 240.000")

st.markdown("---")

# ==========================
# TARJETAS DE METAS
# ==========================
st.markdown("### 🎯 Seguimiento de Metas")
st.caption("Metas definidas en la base de datos. Verde = dentro de meta | Rojo = supera la meta")

# Obtener metas (son globales, tomamos promedio del df_f)
meta_cols = ['META_ROT_GRAL', 'META_AUSENTISMO', 'META_AUSENTISMO_LEGAL',
             'META_AUSENTISMO_MEDICO', 'META_AUSENTISMO_ADMINITRATIVO']
metas_disponibles = {c: df_f[c].mean() for c in meta_cols if c in df_f.columns}

if metas_disponibles:
    # Valores actuales
    activos_base = max(total_act, 1)
    indicadores_meta = {}

    if 'META_ROT_GRAL' in metas_disponibles:
        indicadores_meta['Rotación'] = {
            'actual': total_rot,
            'meta_pct': metas_disponibles['META_ROT_GRAL'],
            'meta_cant': round(metas_disponibles['META_ROT_GRAL'] / 100 * activos_base),
            'icon': '🔄',
            'color_indicador': COLORS['retiros']
        }
    if 'META_AUSENTISMO' in metas_disponibles:
        indicadores_meta['Ausentismo Total'] = {
            'actual': total_aus,
            'meta_pct': metas_disponibles['META_AUSENTISMO'],
            'meta_cant': round(metas_disponibles['META_AUSENTISMO'] / 100 * activos_base),
            'icon': '😷',
            'color_indicador': COLORS['ausentismo']
        }
    if 'META_AUSENTISMO_LEGAL' in metas_disponibles:
        indicadores_meta['Aus. Legal'] = {
            'actual': int(df_f['AUS_LEG'].sum()) if 'AUS_LEG' in df_f.columns else 0,
            'meta_pct': metas_disponibles['META_AUSENTISMO_LEGAL'],
            'meta_cant': round(metas_disponibles['META_AUSENTISMO_LEGAL'] / 100 * activos_base),
            'icon': '⚖️',
            'color_indicador': COLORS['aus_legal']
        }
    if 'META_AUSENTISMO_MEDICO' in metas_disponibles:
        indicadores_meta['Aus. Médico'] = {
            'actual': int(df_f['AUS_MEDICO'].sum()) if 'AUS_MEDICO' in df_f.columns else 0,
            'meta_pct': metas_disponibles['META_AUSENTISMO_MEDICO'],
            'meta_cant': round(metas_disponibles['META_AUSENTISMO_MEDICO'] / 100 * activos_base),
            'icon': '🏥',
            'color_indicador': COLORS['aus_medico']
        }
    if 'META_AUSENTISMO_ADMINITRATIVO' in metas_disponibles:
        indicadores_meta['Aus. Administrativo'] = {
            'actual': int(df_f['AUS_ADMINISTRATIVO'].sum()) if 'AUS_ADMINISTRATIVO' in df_f.columns else 0,
            'meta_pct': metas_disponibles['META_AUSENTISMO_ADMINITRATIVO'],
            'meta_cant': round(metas_disponibles['META_AUSENTISMO_ADMINITRATIVO'] / 100 * activos_base),
            'icon': '🗂️',
            'color_indicador': COLORS['aus_admin']
        }

    # Filtro de vista para metas
    vista_meta = st.radio(
        "Ver metas por:",
        ["📊 Consolidado","🌍 Por Isócrona / Zona", "🏪 Por Tienda" ],
        horizontal=True,
        key="vista_meta"
    )

    if vista_meta == "📊 Consolidado":
        cols_m = st.columns(len(indicadores_meta))
        for i, (nombre, info) in enumerate(indicadores_meta.items()):
            superado = info['actual'] > info['meta_cant']
            estado = "🔴 Supera meta" if superado else "🟢 Dentro de meta"
            delta_val = info['actual'] - info['meta_cant']
            cols_m[i].metric(
                label=f"{info['icon']} {nombre}",
                value=f"{info['actual']:,}",
                delta=f"Meta: {info['meta_cant']:,} ({info['meta_pct']:.1f}%) | {'↑ +' if delta_val > 0 else '↓ '}{abs(delta_val):,}",
                delta_color="inverse" if superado else "normal"
            )
        st.caption(f"*Activos base para cálculo de meta: {activos_base:,}*")

    elif vista_meta == "🏪 Por Tienda":
        tiendas_meta = sorted(df_f['ALMACEN'].dropna().unique().tolist())
        tienda_meta_sel = st.selectbox("Seleccionar tienda:", tiendas_meta, key="tienda_meta_sel")
        df_tienda_meta = df_f[df_f['ALMACEN'] == tienda_meta_sel]

        if not df_tienda_meta.empty:
            act_tienda = max(int(df_tienda_meta['TOTAL_ACTIVOS'].sum()), 1)
            cols_m = st.columns(len(indicadores_meta))
            meta_base = {c: df_tienda_meta[c].mean() for c in meta_cols if c in df_tienda_meta.columns}
            for i, (nombre, info) in enumerate(indicadores_meta.items()):
                meta_key = [k for k in meta_cols if nombre.lower().replace(' ', '') in k.lower().replace('_', '')]
                # Mapeo nombre → columna meta
                nombre_meta_map = {
                    'Rotación':            'META_ROT_GRAL',
                    'Ausentismo Total':    'META_AUSENTISMO',
                    'Aus. Legal':          'META_AUSENTISMO_LEGAL',
                    'Aus. Médico':         'META_AUSENTISMO_MEDICO',
                    'Aus. Administrativo': 'META_AUSENTISMO_ADMINITRATIVO',
                }
                meta_col = nombre_meta_map.get(nombre)
                meta_pct_tienda = meta_base.get(meta_col, info['meta_pct']) if meta_col else info['meta_pct']
                meta_cant_tienda = round(meta_pct_tienda / 100 * act_tienda)

                # Actual por tienda
                actual_tienda_map = {
                    'Rotación':            int(df_tienda_meta['RETIROS'].sum()),
                    'Ausentismo Total':    int(df_tienda_meta['TOTAL_AUSENTISMO'].sum()),
                    'Aus. Legal':          int(df_tienda_meta['AUS_LEG'].sum()) if 'AUS_LEG' in df_tienda_meta.columns else 0,
                    'Aus. Médico':         int(df_tienda_meta['AUS_MEDICO'].sum()) if 'AUS_MEDICO' in df_tienda_meta.columns else 0,
                    'Aus. Administrativo': int(df_tienda_meta['AUS_ADMINISTRATIVO'].sum()) if 'AUS_ADMINISTRATIVO' in df_tienda_meta.columns else 0,
                }
                actual_t = actual_tienda_map.get(nombre, 0)
                superado = actual_t > meta_cant_tienda
                delta_val = actual_t - meta_cant_tienda
                cols_m[i].metric(
                    label=f"{info['icon']} {nombre}",
                    value=f"{actual_t:,}",
                    delta=f"Meta: {meta_cant_tienda:,} ({meta_pct_tienda:.1f}%) | {'↑ +' if delta_val > 0 else '↓ '}{abs(delta_val):,}",
                    delta_color="inverse" if superado else "normal"
                )
            st.caption(f"*Activos en {tienda_meta_sel}: {act_tienda:,}*")

    else:  # Por Zona / Isócrona
        zona_meta_sel = st.selectbox("Seleccionar Zona:", sorted(df_f['ZONA'].dropna().unique().tolist()), key="zona_meta_sel")
        df_zona_meta = df_f[df_f['ZONA'] == zona_meta_sel]

        if not df_zona_meta.empty:
            act_zona = max(int(df_zona_meta['TOTAL_ACTIVOS'].sum()), 1)
            n_tiendas_zona = int(df_zona_meta['ALMACEN'].nunique())
            st.caption(f"**{zona_meta_sel}** — {n_tiendas_zona} tiendas | {act_zona:,} activos")
            cols_m = st.columns(len(indicadores_meta))
            nombre_meta_map = {
                'Rotación':            ('META_ROT_GRAL',           'RETIROS',          None),
                'Ausentismo Total':    ('META_AUSENTISMO',         'TOTAL_AUSENTISMO',  None),
                'Aus. Legal':          ('META_AUSENTISMO_LEGAL',   'AUS_LEG',           None),
                'Aus. Médico':         ('META_AUSENTISMO_MEDICO',  'AUS_MEDICO',        None),
                'Aus. Administrativo': ('META_AUSENTISMO_ADMINITRATIVO', 'AUS_ADMINISTRATIVO', None),
            }
            for i, (nombre, info) in enumerate(indicadores_meta.items()):
                meta_col, act_col, _ = nombre_meta_map.get(nombre, (None, None, None))
                meta_pct_zona = df_zona_meta[meta_col].mean() if meta_col and meta_col in df_zona_meta.columns else info['meta_pct']
                meta_cant_zona = round(meta_pct_zona / 100 * act_zona)
                actual_z = int(df_zona_meta[act_col].sum()) if act_col and act_col in df_zona_meta.columns else 0
                superado = actual_z > meta_cant_zona
                delta_val = actual_z - meta_cant_zona
                cols_m[i].metric(
                    label=f"{info['icon']} {nombre}",
                    value=f"{actual_z:,}",
                    delta=f"Meta: {meta_cant_zona:,} ({meta_pct_zona:.1f}%) | {'↑ +' if delta_val > 0 else '↓ '}{abs(delta_val):,}",
                    delta_color="inverse" if superado else "normal"
                )

st.markdown("---")

# ==========================
# ANÁLISIS COMPARATIVO DE INDICADORES
# ==========================
st.markdown("### 📊 Análisis Comparativo de Indicadores")
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 General", "🔄 Rotación", "😷 Ausentismo", "🚑 Accidentes", "📅 Tendencia"
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
        for trace_name, col, color in [
            ('👥 Activos',   'TOTAL_ACTIVOS',   COLORS['primary']),
            ('🔄 Rotación',  'RETIROS',          COLORS['retiros']),
            ('😷 Ausentismo','TOTAL_AUSENTISMO', COLORS['ausentismo']),
            ('🚑 Accidentes','TOTAL_ACCIDENTES', COLORS['accidentes']),
        ]:
            fig.add_trace(go.Bar(
                name=trace_name, x=zona_m['ZONA'], y=zona_m[col],
                marker_color=color,
                text=zona_m[col].astype(int),
                texttemplate='%{text:,}',
                textposition='outside',
                textfont=dict(size=12)  # Cambiado a 20
            ))
        fig.update_layout(title='Métricas por Zona', barmode='group',
                          plot_bgcolor='white', paper_bgcolor='white', height=420)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        tiendas_gen = df_f.nlargest(10, 'TOTAL_ACTIVOS')[['ALMACEN','TOTAL_ACTIVOS','RETIROS','TOTAL_AUSENTISMO','TOTAL_ACCIDENTES']].copy()
        tiendas_gen = tiendas_gen.sort_values('TOTAL_ACTIVOS', ascending=False)
        fig2 = go.Figure()
        for trace_name, col, color in [
            ('👥 Activos',    'TOTAL_ACTIVOS',   COLORS['primary']),
            ('🔄 Rotación',   'RETIROS',          COLORS['retiros']),
            ('😷 Ausentismo', 'TOTAL_AUSENTISMO', COLORS['ausentismo']),
            ('🚑 Accidentes', 'TOTAL_ACCIDENTES', COLORS['accidentes']),
        ]:
            fig2.add_trace(go.Bar(
                name=trace_name,
                y=tiendas_gen['ALMACEN'],   # ← ahora va en Y
                x=tiendas_gen[col],         # ← ahora va en X
                orientation='h',            # ← esto las vuelve horizontales
                marker_color=color,
                text=tiendas_gen[col].astype(int),
                texttemplate='%{text:,}',
                textposition='outside',
                textfont=dict(size=12)  # Cambiado a 20
            ))
        fig2.update_layout(
            title='Top 10 Tiendas – Métricas Generales', barmode='group',
            xaxis_tickangle=-45, plot_bgcolor='white', paper_bgcolor='white', height=520
        )
        st.plotly_chart(fig2, use_container_width=True, config={'scrollZoom': True})

# ── TAB 2: ROTACIÓN ─────────────────────────────────────────
with tab2:
    c1, c2 = st.columns([2, 1])

    with c1:
        top_rot = df_f.nlargest(10, 'RETIROS')[
            ['ALMACEN','ZONA','TOTAL_ACTIVOS','RETIROS',
             'TASA_ROTACION','TASA_ROTACION_MENSUAL','TASA_ROTACION_ACT_MES_ANT']
        ].copy()
        top_rot = top_rot.sort_values('RETIROS', ascending=False)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=top_rot['ALMACEN'], x=top_rot['RETIROS'],
            orientation='h', name='Rotaciones',
            text=top_rot['RETIROS'].astype(int),
            texttemplate='%{text:,}', textposition='outside',
            marker=dict(color=top_rot['RETIROS'],
                        colorscale=[[0, COLORS['warning']], [1, COLORS['danger']]]),
            customdata=top_rot[['TOTAL_ACTIVOS','ZONA']],
            hovertemplate=(
                '<b>%{y}</b><br>'
                'Rotaciones: %{x:,}<br>'
                'Activos: %{customdata[0]:,}<br>'
                'Zona: %{customdata[1]}<extra></extra>'
            )
        ))
        fig.update_layout(
            title='🔄 Top 10 Tiendas – Mayor Rotación',
            xaxis_title='Total Rotaciones', yaxis_title='',
            plot_bgcolor='white', paper_bgcolor='white',
            height=500, margin=dict(l=200)
        )
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

        # Comparativa mes actual vs mes anterior
        if 'TASA_ROTACION_ACT_MES_ANT' in top_rot.columns and 'TASA_ROTACION_MENSUAL' in top_rot.columns:
            fig_cmp = go.Figure()
            fig_cmp.add_trace(go.Bar(
                name='Rotación mes anterior',
                x=top_rot['ALMACEN'], y=top_rot['TASA_ROTACION_ACT_MES_ANT'],
                marker_color=COLORS['accent'],
                text=top_rot['TASA_ROTACION_ACT_MES_ANT'].round(1),
                texttemplate='%{text:.1f}%', textposition='outside'
            ))
            fig_cmp.add_trace(go.Bar(
                name='Rotación mes actual',
                x=top_rot['ALMACEN'], y=top_rot['TASA_ROTACION_MENSUAL'],
                marker_color=COLORS['retiros'],
                text=top_rot['TASA_ROTACION_MENSUAL'].round(1),
                texttemplate='%{text:.1f}%', textposition='outside'
            ))
            fig_cmp.update_layout(
                title='Comparativa Rotación: Mes Anterior vs Actual (Top 10)',
                barmode='group', xaxis_tickangle=-45,
                plot_bgcolor='white', paper_bgcolor='white', height=400
            )
            st.plotly_chart(fig_cmp, use_container_width=True, config={'scrollZoom': True})

    with c2:
        st.markdown("#### 📊 Estadísticas de Rotación")
        st.metric("Total rotaciones",   f"{int(df_f['RETIROS'].sum()):,}")
        st.metric("Máx. en tienda",     f"{int(df_f['RETIROS'].max()):,}")
        st.metric("Tiendas con retiro", f"{len(df_f[df_f['RETIROS'] > 0])}")

# ── TAB 3: AUSENTISMO ───────────────────────────────────────
with tab3:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🏥 Médico",        f"{int(df_f['AUS_MEDICO'].sum()):,}")
    k2.metric("⚖️ Legal",         f"{int(df_f['AUS_LEG'].sum()):,}")
    k3.metric("🗂️ Administrativo", f"{int(df_f['AUS_ADMINISTRATIVO'].sum()):,}")
    k4.metric("📅 Días totales",  f"{int(df_f['DIAS_AUSENCIA'].sum()):,}")

    c1, c2 = st.columns([2, 1])

    with c1:
        top_aus = df_f.nlargest(10, 'TOTAL_AUSENTISMO')[
            ['ALMACEN','ZONA','TOTAL_ACTIVOS','TOTAL_AUSENTISMO',
             'AUS_MEDICO','AUS_LEG','AUS_ADMINISTRATIVO','DIAS_AUSENCIA']
        ].copy()
        top_aus = top_aus.sort_values('TOTAL_AUSENTISMO', ascending=False)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=top_aus['ALMACEN'], x=top_aus['TOTAL_AUSENTISMO'],
            orientation='h',
            text=top_aus['TOTAL_AUSENTISMO'].astype(int),
            texttemplate='%{text:,}', textposition='outside',
            marker=dict(color=top_aus['TOTAL_AUSENTISMO'],
                        colorscale=[[0, '#fff3cd'], [1, COLORS['warning']]]),
            customdata=top_aus[['TOTAL_ACTIVOS','ZONA','AUS_MEDICO','AUS_LEG','AUS_ADMINISTRATIVO','DIAS_AUSENCIA']],
            hovertemplate=(
                '<b>%{y}</b><br>'
                'Ausentismo total: %{x:,}<br>'
                'Activos: %{customdata[0]:,}<br>'
                'Zona: %{customdata[1]}<br>'
                '🏥 Médico: %{customdata[2]:,}<br>'
                '⚖️ Legal: %{customdata[3]:,}<br>'
                '🗂️ Admin: %{customdata[4]:,}<br>'
                '📅 Días: %{customdata[5]:,}<extra></extra>'
            )
        ))
        fig.update_layout(
            title='😷 Top 10 Tiendas – Mayor Ausentismo',
            xaxis_title='Total Ausentes', yaxis_title='',
            plot_bgcolor='white', paper_bgcolor='white',
            height=500, margin=dict(l=200)
        )
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

        zona_aus = df_f.groupby('ZONA').agg(
            AUS_MEDICO=('AUS_MEDICO','sum'),
            AUS_LEG=('AUS_LEG','sum'),
            AUS_ADMINISTRATIVO=('AUS_ADMINISTRATIVO','sum'),
        ).reset_index()

        fig2 = go.Figure()
        for trace_name, col, color in [
            ('🏥 Médico',        'AUS_MEDICO',        COLORS['aus_medico']),
            ('⚖️ Legal',         'AUS_LEG',           COLORS['aus_legal']),
            ('🗂️ Administrativo','AUS_ADMINISTRATIVO', COLORS['aus_admin']),
        ]:
            fig2.add_trace(go.Bar(
                name=trace_name, x=zona_aus['ZONA'], y=zona_aus[col],
                marker_color=color,
                text=zona_aus[col].astype(int),
                texttemplate='%{text:,}', textposition='inside'
            ))
        fig2.update_layout(
            title='Composición del Ausentismo por Zona',
            barmode='stack', plot_bgcolor='white', paper_bgcolor='white', height=380
        )
        st.plotly_chart(fig2, use_container_width=True)

    with c2:
        st.markdown("#### 📊 Estadísticas")
        st.metric("Total ausentes",         f"{int(df_f['TOTAL_AUSENTISMO'].sum()):,}")
        st.metric("Días ausencia totales",  f"{int(df_f['DIAS_AUSENCIA'].sum()):,}")
        st.metric("Tiendas con ausentismo", f"{len(df_f[df_f['TOTAL_AUSENTISMO'] > 0])}")

        vals = [df_f['AUS_MEDICO'].sum(), df_f['AUS_LEG'].sum(), df_f['AUS_ADMINISTRATIVO'].sum()]
        lbs  = ['Médico', 'Legal', 'Admin']
        fig_pie = go.Figure(go.Pie(
            labels=lbs, values=vals,
            marker_colors=[COLORS['aus_medico'], COLORS['aus_legal'], COLORS['aus_admin']],
            hole=0.4,
            text=[f"{int(v):,}" for v in vals],
            textinfo='label+text'
        ))
        fig_pie.update_layout(title="Composición", height=300,
                               margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_pie, use_container_width=True)

# ── TAB 4: ACCIDENTES ───────────────────────────────────────
with tab4:
    c1, c2 = st.columns([2, 1])

    with c1:
        top_acc = df_f.nlargest(10, 'TOTAL_ACCIDENTES')[
            ['ALMACEN','ZONA','TOTAL_ACTIVOS','TOTAL_ACCIDENTES']
        ].copy()
        top_acc = top_acc.sort_values('TOTAL_ACCIDENTES', ascending=False)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=top_acc['ALMACEN'], x=top_acc['TOTAL_ACCIDENTES'],
            orientation='h',
            text=top_acc['TOTAL_ACCIDENTES'].astype(int),
            texttemplate='%{text:,}', textposition='outside',
            marker=dict(color=top_acc['TOTAL_ACCIDENTES'],
                        colorscale=[[0, '#c8f7c5'], [1, COLORS['accidentes']]]),
            customdata=top_acc[['TOTAL_ACTIVOS','ZONA']],
            hovertemplate=(
                '<b>%{y}</b><br>'
                'Accidentes: %{x:,}<br>'
                'Activos: %{customdata[0]:,}<br>'
                'Zona: %{customdata[1]}<extra></extra>'
            )
        ))
        fig.update_layout(
            title='🚑 Top 10 Tiendas – Mayor Accidentalidad',
            xaxis_title='Total Accidentes', yaxis_title='',
            plot_bgcolor='white', paper_bgcolor='white',
            height=500, margin=dict(l=200)
        )
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

        zona_acc = df_f.groupby('ZONA').agg(
            TOTAL_ACCIDENTES=('TOTAL_ACCIDENTES','sum'),
            TOTAL_ACTIVOS=('TOTAL_ACTIVOS','sum'),
        ).reset_index()

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=zona_acc['ZONA'], y=zona_acc['TOTAL_ACCIDENTES'],
            marker_color=COLORS['accidentes'],
            text=zona_acc['TOTAL_ACCIDENTES'].astype(int),
            texttemplate='%{text:,}', textposition='outside'
        ))
        fig2.update_layout(
            title='Total Accidentes por Zona',
            xaxis_title='Zona', yaxis_title='Accidentes',
            plot_bgcolor='white', paper_bgcolor='white', height=360
        )
        st.plotly_chart(fig2, use_container_width=True)

    with c2:
        st.markdown("#### 📊 Estadísticas")
        st.metric("Total accidentes",       f"{int(df_f['TOTAL_ACCIDENTES'].sum()):,}")
        st.metric("Máx. en tienda",         f"{int(df_f['TOTAL_ACCIDENTES'].max()):,}")
        st.metric("Tiendas con accidentes", f"{len(df_f[df_f['TOTAL_ACCIDENTES'] > 0])}")

# ── TAB 5: TENDENCIA ────────────────────────────────────────
with tab5:
    st.markdown("#### 📈 Evolución Mensual (todos los períodos disponibles)")

    df_trend = df_raw.copy() if zona_seleccionada == "TODAS" else df_raw[df_raw['ZONA'] == zona_seleccionada].copy()

    trend = df_trend.groupby(['MES','AÑO']).agg(
        TOTAL_ACTIVOS=('TOTAL_ACTIVOS','sum'),
        RETIROS=('RETIROS','sum'),
        TOTAL_AUSENTISMO=('TOTAL_AUSENTISMO','sum'),
        TOTAL_ACCIDENTES=('TOTAL_ACCIDENTES','sum'),
    ).reset_index()
    trend['MES_NUM'] = trend['MES'].map(MES_ORDEN).fillna(0)
    trend = trend.sort_values(['AÑO','MES_NUM'])
    trend['PERIODO'] = trend['MES'].str.replace(r'^\d+\.\s*', '', regex=True) + ' ' + trend['AÑO'].astype(str)

    fig_t = go.Figure()
    for trace_name, col, color in [
        ('🔄 Rotación',  'RETIROS',          COLORS['retiros']),
        ('😷 Ausentismo','TOTAL_AUSENTISMO', COLORS['ausentismo']),
        ('🚑 Accidentes','TOTAL_ACCIDENTES', COLORS['accidentes']),
        ('👥 Activos',   'TOTAL_ACTIVOS',   COLORS['primary']),
    ]:
        fig_t.add_trace(go.Scatter(
            x=trend['PERIODO'], y=trend[col],
            mode='lines+markers+text',
            name=trace_name,
            line=dict(color=color, width=2),
            text=trend[col].astype(int),
            texttemplate='%{text:,}',
            textposition='top center'
        ))
    fig_t.update_layout(
        title='Evolución por Período',
        xaxis_title='Período', yaxis_title='Cantidad',
        plot_bgcolor='white', paper_bgcolor='white',
        height=480, xaxis_tickangle=-45,
        legend=dict(orientation='h', y=1.1)
    )
    st.plotly_chart(fig_t, use_container_width=True)

    fig_act = go.Figure()
    for anio in sorted(trend['AÑO'].unique()):
        d = trend[trend['AÑO'] == anio]
        fig_act.add_trace(go.Scatter(
            x=d['MES'].str.replace(r'^\d+\.\s*','',regex=True),
            y=d['TOTAL_ACTIVOS'],
            mode='lines+markers+text', name=str(anio),
            text=d['TOTAL_ACTIVOS'].astype(int),
            texttemplate='%{text:,}',
            textposition='top center'
        ))
    fig_act.update_layout(
        title='Personal Activo por Mes y Año',
        xaxis_title='Mes', yaxis_title='Total Activos',
        plot_bgcolor='white', paper_bgcolor='white', height=380
    )
    st.plotly_chart(fig_act, use_container_width=True)

st.markdown("---")

# ==========================
# ANÁLISIS DE ROTACIÓN - CARGOS Y MOTIVOS
# ==========================
st.markdown("### 🔄 Análisis de Rotación - Cargos y Motivos")

df_oficio = df_raw_f.copy()

if not df_oficio.empty and 'NOM_OFICIO' in df_oficio.columns and 'MOTIVO' in df_oficio.columns:
    
    # Preparar datos para cargos
    cargo_rot = df_oficio.groupby('NOM_OFICIO').agg(
        TOTAL_ACTIVOS=('TOTAL_ACTIVOS', 'sum'),
        RETIROS=('RETIROS', 'sum'),
    ).reset_index()
    cargo_rot = cargo_rot[cargo_rot['RETIROS'] > 0].sort_values('RETIROS', ascending=False).head(10)
    
    # Preparar datos para motivos - EXCLUYENDO MOTIVOS ESPECÍFICOS
    df_motivos = df_oficio[df_oficio['RETIROS'] >= 1].copy()
    
    # Filtrar para excluir los motivos no deseados
    motivos_excluir = [
        'Terminación de contrato con justa causa', 
        'Terminación de contrato sin justa causa'
    ]
    
    df_motivos_filtrado = df_motivos[~df_motivos['MOTIVO'].isin(motivos_excluir)].copy()
    
    if not cargo_rot.empty and not df_motivos_filtrado.empty:
        motivo_agg = df_motivos_filtrado.groupby('MOTIVO')['RETIROS'].sum().reset_index()
        motivo_agg.columns = ['Motivo', 'Total Rotaciones']
        motivo_agg = motivo_agg.sort_values('Total Rotaciones', ascending=False)
        
        # Crear columnas para las dos gráficas
        col_cargos, col_motivos = st.columns([3, 2])
        
        with col_cargos:
            # Gráfica de barras - Top cargos
            fig_top_cargo = go.Figure()
            fig_top_cargo.add_trace(go.Bar(
                y=cargo_rot['NOM_OFICIO'],
                x=cargo_rot['RETIROS'],
                orientation='h',
                text=cargo_rot['RETIROS'].astype(int),
                texttemplate='%{text:,}',
                textposition='outside',
                textfont=dict(size=12),
                marker=dict(color=cargo_rot['RETIROS'],
                          colorscale=[[0, COLORS['accent']], [1, COLORS['danger']]]),
                customdata=cargo_rot['TOTAL_ACTIVOS'],
                hovertemplate='<b>%{y}</b><br>Rotaciones: %{x:,}<br>Activos: %{customdata:,}<extra></extra>'
            ))
            fig_top_cargo.update_layout(
                title='Top 10 Cargos por Rotaciones',
                xaxis_title='Total Rotaciones',
                yaxis_title='',
                yaxis=dict(categoryorder='total ascending'),
                plot_bgcolor='white', 
                paper_bgcolor='white',
                height=380, 
                margin=dict(l=200, r=20, t=50, b=50)
            )
            st.plotly_chart(fig_top_cargo, use_container_width=True, config={'scrollZoom': True})
        
        with col_motivos:
            # Gráfica de torta - Distribución de motivos (más pequeña)
            def wrap_label(s, width=20):
                words = str(s).split()
                lines, cur = [], ''
                for w in words:
                    if len(cur) + len(w) + 1 <= width:
                        cur = (cur + ' ' + w).strip()
                    else:
                        if cur:
                            lines.append(cur)
                        cur = w
                if cur:
                    lines.append(cur)
                return '<br>'.join(lines[:2])
            
            motivo_labels_wrapped = [wrap_label(m) for m in motivo_agg['Motivo']]
            
            fig_pie_mot = go.Figure(go.Pie(
                labels=motivo_labels_wrapped,
                values=motivo_agg['Total Rotaciones'],
                hole=0.35,
                text=[f"{int(v):,}" for v in motivo_agg['Total Rotaciones']],
                textinfo='label+text',
                textfont=dict(size=10),  # Reducido tamaño de fuente
                marker=dict(colors=px.colors.qualitative.Set3)  # Colores variados
            ))
            fig_pie_mot.update_layout(
                title='Distribución de Motivos',
                height=280,  # Reducido de 350 a 280
                margin=dict(l=5, r=5, t=40, b=5),  # Márgenes más pequeños
                showlegend=True,
                legend=dict(orientation='v', x=1.01, y=0.5, font=dict(size=9)),  # Leyenda más pequeña
                plot_bgcolor='white', 
                paper_bgcolor='white'
            )
            st.plotly_chart(fig_pie_mot, use_container_width=True)
    else:
        if cargo_rot.empty:
            st.warning("⚠️ No hay datos de rotación por cargo para los filtros seleccionados.")
        if df_motivos_filtrado.empty:
            st.warning("⚠️ No hay datos de motivos de retiro (excluyendo terminaciones de contrato) para los filtros seleccionados.")
else:
    st.info("ℹ️ No se encontraron las columnas necesarias (NOM_OFICIO y/o MOTIVO) en los datos.")

st.markdown("---")

# ==========================
# TASAS POR ZONA
# ==========================
st.markdown("### 📊 Comparación de Indicadores por Zona")

zonas_tasas = df_f.groupby('ZONA').agg({
    'TOTAL_ACTIVOS': 'sum',
    'RETIROS': 'sum',
    'TOTAL_AUSENTISMO': 'sum',
    'TOTAL_ACCIDENTES': 'sum',
    'DIAS_AUSENCIA': 'sum',
}).reset_index()
zonas_tasas['NUM_TIENDAS'] = df_f.groupby('ZONA')['ALMACEN'].nunique().values

fig_zonas = go.Figure()
for trace_name, col, color in [
    ('🔄 Rotación',  'RETIROS',          COLORS['retiros']),
    ('😷 Ausentismo','TOTAL_AUSENTISMO', COLORS['ausentismo']),
    ('🚑 Accidentes','TOTAL_ACCIDENTES', COLORS['accidentes']),
]:
    fig_zonas.add_trace(go.Bar(
        name=trace_name,
        x=zonas_tasas['ZONA'],
        y=zonas_tasas[col],
        marker_color=color,
        text=zonas_tasas[col].astype(int),
        texttemplate='%{text:,}',
        textposition='outside'
    ))
fig_zonas.update_layout(
    title='Indicadores por Zona',
    barmode='group',
    xaxis_title='Zona', yaxis_title='Cantidad',
    plot_bgcolor='white', paper_bgcolor='white',
    height=450
)
st.plotly_chart(fig_zonas, use_container_width=True)

st.markdown("---")

# ==========================
# RETIROS POR RANGO DE PERMANENCIA
# ==========================
st.markdown("### 🔄 Rotación por Rango de Permanencia")
st.caption("*Solo se incluyen registros donde RETIROS >= 1*")

df_retiros = df_raw_f[df_raw_f['RETIROS'] >= 1].copy() if 'RETIROS' in df_raw_f.columns else pd.DataFrame()

orden_rangos = ['0-2 MESES', '2-4 MESES', '4-6 MESES', '6-12 MESES',
                'A1-2 AÑOS', 'A2-3 AÑOS', 'A3-4 AÑOS', 'A4-5 AÑOS', 'A5+ AÑOS']

if not df_retiros.empty and 'RANGO_PERMANENCIA' in df_retiros.columns:
    rango_agg = df_retiros.groupby('RANGO_PERMANENCIA').agg(
        Total_Rotaciones=('RETIROS', 'sum'),
    ).reset_index()
    rango_agg.columns = ['Rango de Permanencia', 'Total Rotaciones']
    rango_agg['Orden'] = rango_agg['Rango de Permanencia'].map(
        {r: i for i, r in enumerate(orden_rangos)}
    )
    rango_agg = rango_agg.dropna(subset=['Orden']).sort_values('Orden').drop('Orden', axis=1)

    fig_rango = go.Figure()
    fig_rango.add_trace(go.Bar(
        y=rango_agg['Rango de Permanencia'],
        x=rango_agg['Total Rotaciones'],
        orientation='h',
        text=rango_agg['Total Rotaciones'].astype(int),
        texttemplate='%{text:,}',
        textposition='outside',
        marker=dict(color=rango_agg['Total Rotaciones'],
                    colorscale=[[0, COLORS['accent']], [1, COLORS['danger']]]),
        hovertemplate='<b>%{y}</b><br>Rotaciones: %{x:,}<extra></extra>'
    ))
    fig_rango.update_layout(
        title='📊 Rotaciones por Rango de Permanencia',
        xaxis_title='Total Rotaciones',
        yaxis_title='Rango de Permanencia',
        plot_bgcolor='white', paper_bgcolor='white',
        height=400, margin=dict(l=120)
    )
    st.plotly_chart(fig_rango, use_container_width=True)

# ==========================
# MAPA GEOGRÁFICO
# ==========================
st.markdown("### 🗺️ Vista Geográfica")

df_map_full = df_f.copy()
df_map = df_map_full.dropna(subset=['LATITUD', 'LONGITUD'])
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
            ['Total Activos','Total Rotación','Total Ausentismo','Total Accidentes','Días Ausencia'],
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
            'Total Activos':    ('TOTAL_ACTIVOS',   COLORS['primary']),
            'Total Rotación':   ('RETIROS',          COLORS['retiros']),
            'Total Ausentismo': ('TOTAL_AUSENTISMO', COLORS['ausentismo']),
            'Total Accidentes': ('TOTAL_ACCIDENTES', COLORS['accidentes']),
            'Días Ausencia':    ('DIAS_AUSENCIA',    COLORS['aus_medico']),
        }
        col_val, color_base = COL_MAP[metrica_mapa]

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
            valor = row.get(col_val, 0)
            radio = max(tamaño_base, float(valor) * factor_escala)
            color = col_zona.get(row['ZONA'], color_base)

            popup_html = f"""
            <div style="font-family:Arial; min-width:260px;">
                <h4 style="margin:0;color:{COLORS['primary']};">{row['ALMACEN']}</h4>
                <hr style="margin:5px 0;">
                <table style="width:100%;font-size:12px;">
                    <tr><td>📍 Zona:</td><td><b>{row['ZONA']}</b></td></tr>
                    <tr><td>👥 Activos:</td><td><b>{int(row['TOTAL_ACTIVOS'])}</b></td></tr>
                    <tr><td>🔄 Rotación:</td><td><b>{int(row['RETIROS'])}</b></td></tr>
                    <tr><td>😷 Ausentismo:</td><td><b>{int(row['TOTAL_AUSENTISMO'])}</b></td></tr>
                    <tr><td>📅 Días aus.:</td><td><b>{int(row.get('DIAS_AUSENCIA',0))}</b></td></tr>
                    <tr><td>🚑 Accidentes:</td><td><b>{int(row['TOTAL_ACCIDENTES'])}</b></td></tr>
                    <tr><td colspan=2 style="padding-top:5px;">📅 <i>{row['MES']} {row['AÑO']}</i></td></tr>
                </table>
            </div>"""

            folium.CircleMarker(
                location=[row['LATITUD'], row['LONGITUD']],
                radius=radio,
                popup=folium.Popup(popup_html, max_width=300),
                color=color, fill=True, fill_color=color,
                fill_opacity=0.7, weight=2,
                tooltip=f"{row['ALMACEN']} – {metrica_mapa}: {int(valor):,}"
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
    'DIAS_AUSENCIA','TOTAL_ACCIDENTES','FECHA'
]
existing_cols = [c for c in all_cols if c in df_f.columns]

col_cfg_table = {
    "ALMACEN":            st.column_config.TextColumn("🏪 Tienda",      width="medium"),
    "ZONA":               st.column_config.TextColumn("📍 Zona",         width="small"),
    "TOTAL_ACTIVOS":      st.column_config.NumberColumn("👥 Activos",    format="%d"),
    "RETIROS":            st.column_config.NumberColumn("🔄 Rotación",   format="%d"),
    "TOTAL_AUSENTISMO":   st.column_config.NumberColumn("😷 Ausentismo", format="%d"),
    "AUS_MEDICO":         st.column_config.NumberColumn("🏥 Médico",     format="%d"),
    "AUS_LEG":            st.column_config.NumberColumn("⚖️ Legal",      format="%d"),
    "AUS_ADMINISTRATIVO": st.column_config.NumberColumn("🗂️ Admin",      format="%d"),
    "DIAS_AUSENCIA":      st.column_config.NumberColumn("📅 Días",       format="%d"),
    "TOTAL_ACCIDENTES":   st.column_config.NumberColumn("🚑 Accidentes", format="%d"),
    "FECHA":              st.column_config.TextColumn("📅 Período"),
}

tabla = df_f[existing_cols].sort_values('TOTAL_ACTIVOS', ascending=False)
st.dataframe(tabla, use_container_width=True, hide_index=True,
             column_config=col_cfg_table, height=450)
st.caption(f"📊 {len(tabla):,} registros | Período: {mes} {año}")

# ==========================
# CHAT IA CON GROQ
# ==========================
st.markdown("---")
st.markdown("### 🤖 Asistente IA — Consultas de Negocio")
st.markdown(
    "Haz preguntas sobre los datos del período seleccionado. "
    "El asistente tiene acceso al resumen estadístico de la data filtrada."
)

# Leer API Key desde Streamlit Secrets (con fallback a variable de entorno)
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
GROQ_MODEL   = "llama-3.3-70b-versatile"
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"

if not GROQ_API_KEY:
    st.warning("⚠️ No se encontró **GROQ_API_KEY**. Configúrala en Streamlit Cloud → Settings → Secrets como:\n```\nGROQ_API_KEY = \"tu_clave_aqui\"\n```")
    st.stop()

def build_data_context(df_filtrado: pd.DataFrame) -> str:
    """Genera un resumen compacto del DataFrame filtrado para el contexto del LLM."""
    try:
        num_cols = [
            'TOTAL_ACTIVOS', 'RETIROS', 'TOTAL_AUSENTISMO', 'TOTAL_ACCIDENTES',
            'DIAS_AUSENCIA', 'AUS_MEDICO', 'AUS_LEG', 'AUS_ADMINISTRATIVO',
            'TASA_ROTACION', 'TASA_AUSENTISMO', 'TASA_ACCIDENTALIDAD',
        ]
        existing = [c for c in num_cols if c in df_filtrado.columns]

        totales = df_filtrado[existing].sum().to_dict()
        resumen_num = "\n".join([f"  - {k}: {v:,.2f}" for k, v in totales.items()])

        top_rotacion = ""
        if 'RETIROS' in df_filtrado.columns and 'ALMACEN' in df_filtrado.columns:
            top5 = (
                df_filtrado.groupby('ALMACEN')['RETIROS']
                .sum().nlargest(5).reset_index()
            )
            top_rotacion = "\nTop 5 tiendas con mayor rotación:\n" + top5.to_string(index=False)

        top_ausentismo = ""
        if 'TOTAL_AUSENTISMO' in df_filtrado.columns and 'ALMACEN' in df_filtrado.columns:
            top5a = (
                df_filtrado.groupby('ALMACEN')['TOTAL_AUSENTISMO']
                .sum().nlargest(5).reset_index()
            )
            top_ausentismo = "\nTop 5 tiendas con mayor ausentismo:\n" + top5a.to_string(index=False)

        por_zona = ""
        if 'ZONA' in df_filtrado.columns:
            zona_grp = df_filtrado.groupby('ZONA')[existing].sum()
            por_zona = "\nResumen por zona:\n" + zona_grp.to_string()

        context = f"""
Datos del dashboard — Período: {mes} {año} | Zona: {zona_seleccionada}
Número de registros: {len(df_filtrado)} | Tiendas únicas: {df_filtrado['ALMACEN'].nunique() if 'ALMACEN' in df_filtrado.columns else 'N/A'}

TOTALES GENERALES:
{resumen_num}
{top_rotacion}
{top_ausentismo}
{por_zona}
"""
        return context.strip()
    except Exception as e:
        return f"(No se pudo generar el resumen de datos: {e})"


def ask_groq(messages_history: list) -> str:
    try:
        from groq import Groq
    except ImportError:
        return "❌ Librería 'groq' no instalada. Agrégala a requirements.txt"

    try:
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages_history,
            temperature=0.4,
            max_tokens=1024,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"❌ Error al contactar Groq: {e}"


# Inicializar historial de chat en session_state
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "chat_data_context" not in st.session_state:
    st.session_state.chat_data_context = ""

# Regenerar contexto cuando cambia el período o filtros
current_ctx = build_data_context(df_f)
if current_ctx != st.session_state.chat_data_context:
    st.session_state.chat_data_context = current_ctx
    # Limpiar historial al cambiar período (opcional)
    if st.session_state.chat_messages:
        st.info("ℹ️ Se detectó un cambio en el período/filtros. El contexto del asistente fue actualizado.")

# Mostrar historial de conversación
chat_container = st.container()
with chat_container:
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# Input del usuario
user_input = st.chat_input("Pregunta algo sobre los datos... ej: ¿Cuál tienda tiene mayor rotación?")

if user_input:
    # Agregar mensaje del usuario al historial visible
    st.session_state.chat_messages.append({"role": "user", "content": user_input})

    with chat_container:
        with st.chat_message("user"):
            st.markdown(user_input)

    # Construir mensajes para la API (system + historial + nuevo mensaje)
    system_prompt = f"""Eres un asistente de análisis de negocio experto en gestión de personal para retail.
Tienes acceso al siguiente resumen de datos del dashboard Obeya Comercial 2026:

---
{st.session_state.chat_data_context}
---

Responde en español de forma clara, concisa y orientada a decisiones de negocio.
Cuando menciones números, sé preciso. Si la pregunta no se puede responder con los datos disponibles, indícalo amablemente.
"""

    api_messages = [{"role": "system", "content": system_prompt}]
    # Agregar historial (últimas 10 interacciones para no exceder tokens)
    for m in st.session_state.chat_messages[-10:]:
        api_messages.append({"role": m["role"], "content": m["content"]})

    with chat_container:
        with st.chat_message("assistant"):
            with st.spinner("🤔 Pensando..."):
                response = ask_groq(api_messages)
            st.markdown(response)

    st.session_state.chat_messages.append({"role": "assistant", "content": response})

# Botón para limpiar chat
if st.session_state.chat_messages:
    if st.button("🗑️ Limpiar conversación", key="clear_chat"):
        st.session_state.chat_messages = []
        st.rerun()

# ==========================
# FOOTER
# ==========================
st.markdown("---")
st.markdown(f"""
<div style="text-align:center; padding:20px;
            background:linear-gradient(135deg,{COLORS['gradient_start']} 0%,{COLORS['gradient_end']} 100%);
            color:white; border-radius:10px;">
    <h4>📊 Obeya Comercial 2026 — Cobertura y Gestión de Personal</h4>
    <p style="margin:5px 0;">
        <b>Generado:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} |
        <b>Período:</b> {mes} {año} |
        <b>Zona:</b> {zona_seleccionada} |
        <b>Registros:</b> {len(df_f):,} de {len(df):,}
    </p>
</div>
""", unsafe_allow_html=True)