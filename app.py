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

st.set_page_config(
    page_title="Dashboard Obeya Comercial 2026",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

COLORS = {
    'primary': '#1e3c72', 'secondary': '#2a5298', 'accent': '#7fa8e0',
    'success': '#28a745', 'warning': '#ffc107', 'danger': '#dc3545',
    'info': '#17a2b8', 'light': '#f8f9fa', 'dark': '#343a40',
    'gradient_start': '#1e3c72', 'gradient_end': '#2a5298',
    'retiros': '#dc3545', 'ausentismo': '#ffc107', 'accidentes': '#28a745',
    'aus_medico': '#e74c3c', 'aus_legal': '#9b59b6', 'aus_admin': '#3498db',
}

CHART_COLORS = ['#1e3c72','#2a5298','#7fa8e0','#5080c0','#3060a0','#406db8',
                '#e67e22','#27ae60','#8e44ad','#16a085']

MES_ORDEN = {
    '01. ENERO':1,'02. FEBRERO':2,'03. MARZO':3,'04. ABRIL':4,
    '05. MAYO':5,'06. JUNIO':6,'07. JULIO':7,'08. AGOSTO':8,
    '09. SEPTIEMBRE':9,'10. OCTUBRE':10,'11. NOVIEMBRE':11,'12. DICIEMBRE':12
}

RANGO_ORDEN = [
    '0-2 MESES','2-4 MESES','4-6 MESES','6-12 MESES',
    'A1-2 AÑOS','A2-3 AÑOS','A3-4 AÑOS','A4-5 AÑOS',
    'A5-6 AÑOS','A6-7 AÑOS','A7-8 AÑOS','A8-9 AÑOS',
    'A9-10 AÑOS','AA10-11 AÑOS','AA11-12 AÑOS','MAS DE 12 AÑOS'
]

import os
CSV_PATH = os.environ.get('CSV_PATH', 'data.csv')
GEOJSON_PATH = os.environ.get('GEODATA_PATH', 'geodata')

st.markdown("""
<style>
.main-header{background:linear-gradient(135deg,#1e3c72 0%,#2a5298 100%);padding:2rem;border-radius:10px;color:white;text-align:center;margin-bottom:1.5rem;box-shadow:0 4px 6px rgba(0,0,0,0.1);}
div[data-testid="stHorizontalBlock"] .stButton button{border-radius:20px;font-size:0.82rem;padding:0.3rem 0.8rem;width:100%;transition:all 0.2s ease;}
.stMetric{background-color:white;padding:12px;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.05);}
.section-title{font-size:1.1rem;font-weight:700;color:#1e3c72;border-left:4px solid #1e3c72;padding-left:10px;margin:1.2rem 0 0.6rem 0;}
</style>
""", unsafe_allow_html=True)

def parse_pct(series):
    return (series.astype(str).str.replace('%','',regex=False)
            .str.replace(',','.',regex=False).str.strip()
            .pipe(pd.to_numeric,errors='coerce').fillna(0))

def parse_num(series):
    return (series.astype(str).str.replace('.','',regex=False)
            .str.replace(',','.',regex=False).str.strip()
            .pipe(pd.to_numeric,errors='coerce').fillna(0))

@st.cache_data(ttl=600,show_spinner=False)
def load_csv():
    try:
        df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
        df.columns = df.columns.str.strip().str.upper()
        rename = {
            'NOM_CCOSTO':'ALMACEN','NOM OFICIO':'NOM_OFICIO',
            '#ACTIVOS':'TOTAL_ACTIVOS','RETIROS':'TOTAL_RETIROS',
            'AUS_TOTAL':'TOTAL_AUSENTISMO','#ACCIDENTES':'TOTAL_ACCIDENTES',
            '#DIAS_ADMINISTRATIVO':'DIAS_ADMIN','#DIAS_LEGAL':'DIAS_LEGAL',
            '#DIAS_MEDICO':'DIAS_MEDICO','#HORAS_AUSENTISMO':'HORAS_AUSENTISMO',
            '#HORAS':'HORAS_TRABAJADAS','RANGOS DE PERMANENCIA':'RANGO_PERMANENCIA',
        }
        df.rename(columns={k:v for k,v in rename.items() if k in df.columns},inplace=True)
        for col in ['LATITUD','LONGITUD']:
            df[col] = df[col].astype(str).str.replace(',','.',regex=False)
            df[col] = pd.to_numeric(df[col],errors='coerce')
        df['TASA_ROTACION_MENSUAL'] = parse_pct(df['TASA_ROTACION_MENSUAL'])
        df['TASA_ROTACION_ACT_MES_ANT'] = parse_pct(df['TASA_ROTACION_ACT_MES_ANT'])
        df['TASA_DE_ACCIDENTALIDAD'] = parse_pct(df['TASA_DE_ACCIDENTALIDAD'])
        df['HORAS_TRABAJADAS'] = parse_num(df['HORAS_TRABAJADAS'])
        for col in ['TOTAL_ACTIVOS','TOTAL_RETIROS','TOTAL_AUSENTISMO','TOTAL_ACCIDENTES',
                    'AUS_MEDICO','AUS_LEGAL','AUS_ADMINISTRATIVO',
                    'DIAS_ADMIN','DIAS_LEGAL','DIAS_MEDICO','DIAS_AUSENCIA','HORAS_AUSENTISMO']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col],errors='coerce').fillna(0)
        df['AÑO'] = pd.to_numeric(df['AÑO'],errors='coerce').astype('Int64')
        df['MES'] = df['MES'].astype(str).str.strip().str.upper()
        df['RANGO_PERMANENCIA'] = df['RANGO_PERMANENCIA'].astype(str).str.strip().str.upper()
        return df
    except FileNotFoundError:
        st.error(f"❌ No se encontró el archivo CSV.\n\nRuta buscada: **{CSV_PATH}**")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error al cargar el CSV: {e}")
        st.stop()

@st.cache_data(ttl=600,show_spinner=False)
def process_data(df_raw,mes,año,zona_filtro):
    df = df_raw[(df_raw['MES']==mes)&(df_raw['AÑO']==año)].copy()
    if zona_filtro != 'TODAS':
        df = df[df['ZONA']==zona_filtro]
    if df.empty: return df
    group_cols = [c for c in ['ALMACEN','CCOSTO','ZONA','LATITUD','LONGITUD','MES','AÑO'] if c in df.columns]
    agg_dict = {k:v for k,v in {
        'TOTAL_ACTIVOS':('TOTAL_ACTIVOS','sum'),'TOTAL_RETIROS':('TOTAL_RETIROS','sum'),
        'TOTAL_AUSENTISMO':('TOTAL_AUSENTISMO','sum'),'TOTAL_ACCIDENTES':('TOTAL_ACCIDENTES','sum'),
        'AUS_MEDICO':('AUS_MEDICO','sum'),'AUS_LEGAL':('AUS_LEGAL','sum'),
        'AUS_ADMINISTRATIVO':('AUS_ADMINISTRATIVO','sum'),'DIAS_AUSENCIA':('DIAS_AUSENCIA','sum'),
        'DIAS_ADMIN':('DIAS_ADMIN','sum'),'DIAS_LEGAL':('DIAS_LEGAL','sum'),
        'DIAS_MEDICO':('DIAS_MEDICO','sum'),'HORAS_AUSENTISMO':('HORAS_AUSENTISMO','sum'),
        'HORAS_TRABAJADAS':('HORAS_TRABAJADAS','sum'),
        'TASA_ROTACION_MENSUAL':('TASA_ROTACION_MENSUAL','mean'),
        'TASA_ROTACION_ACT_MES_ANT':('TASA_ROTACION_ACT_MES_ANT','mean'),
        'TASA_DE_ACCIDENTALIDAD':('TASA_DE_ACCIDENTALIDAD','mean'),
    }.items() if v[0] in df.columns}
    df_agg = df.groupby(group_cols,dropna=False).agg(**agg_dict).reset_index()
    activos = df_agg['TOTAL_ACTIVOS'].clip(lower=1)
    df_agg['TASA_ROTACION'] = (df_agg['TOTAL_RETIROS']/activos*100).fillna(0)
    df_agg['TASA_AUSENTISMO'] = (df_agg['TOTAL_AUSENTISMO']/activos*100).fillna(0)
    df_agg['TASA_ACCIDENTALIDAD'] = (df_agg['TOTAL_ACCIDENTES']/activos*100).fillna(0)
    df_agg['FECHA'] = df_agg['MES'].map(MES_ORDEN).astype(str)+'/'+df_agg['AÑO'].astype(str)
    df_agg = df_agg.dropna(subset=['LATITUD','LONGITUD'])
    return df_agg

@st.cache_data(ttl=600,show_spinner=False)
def get_oficio_data(df_raw,mes,año,zona_filtro):
    df = df_raw[(df_raw['MES']==mes)&(df_raw['AÑO']==año)].copy()
    if zona_filtro != 'TODAS': df = df[df['ZONA']==zona_filtro]
    if df.empty: return pd.DataFrame()
    return (df.groupby('NOM_OFICIO',dropna=False)
              .agg(TOTAL_ACTIVOS=('TOTAL_ACTIVOS','sum'),TOTAL_RETIROS=('TOTAL_RETIROS','sum'),
                   TOTAL_AUSENTISMO=('TOTAL_AUSENTISMO','sum'),TOTAL_ACCIDENTES=('TOTAL_ACCIDENTES','sum'))
              .reset_index().sort_values('TOTAL_ACTIVOS',ascending=False))

@st.cache_data(ttl=600,show_spinner=False)
def get_rango_permanencia(df_raw,mes,año,zona_filtro):
    df = df_raw[(df_raw['MES']==mes)&(df_raw['AÑO']==año)].copy()
    if zona_filtro != 'TODAS': df = df[df['ZONA']==zona_filtro]
    df = df[df['TOTAL_RETIROS']>=1]
    if df.empty: return pd.DataFrame()
    rango = (df.groupby('RANGO_PERMANENCIA',dropna=False)
               .agg(TOTAL_RETIROS=('TOTAL_RETIROS','sum')).reset_index())
    rango['ORDEN'] = rango['RANGO_PERMANENCIA'].map({v:i for i,v in enumerate(RANGO_ORDEN)}).fillna(99)
    return rango.sort_values('ORDEN')

@st.cache_data(ttl=600,show_spinner=False)
def get_tasas_ccosto(df_raw,mes,año,zona_filtro):
    df = df_raw[(df_raw['MES']==mes)&(df_raw['AÑO']==año)].copy()
    if zona_filtro != 'TODAS': df = df[df['ZONA']==zona_filtro]
    if df.empty: return pd.DataFrame()
    agg = (df.groupby('ALMACEN',dropna=False)
             .agg(TOTAL_ACTIVOS=('TOTAL_ACTIVOS','sum'),TOTAL_RETIROS=('TOTAL_RETIROS','sum'),
                  TOTAL_AUSENTISMO=('TOTAL_AUSENTISMO','sum'),TOTAL_ACCIDENTES=('TOTAL_ACCIDENTES','sum'))
             .reset_index())
    activos = agg['TOTAL_ACTIVOS'].clip(lower=1)
    agg['TASA_ROTACION'] = (agg['TOTAL_RETIROS']/activos*100).round(2)
    agg['TASA_AUSENTISMO'] = (agg['TOTAL_AUSENTISMO']/activos*100).round(2)
    agg['TASA_ACCIDENTALIDAD'] = (agg['TOTAL_ACCIDENTES']/activos*100).round(2)
    return agg.sort_values('TASA_ROTACION',ascending=False)

@st.cache_data(ttl=600,show_spinner=False)
def load_geojson(file_path=None):
    try:
        if file_path is None:
            geo_path = Path(GEOJSON_PATH)
            if not geo_path.exists(): return None
            files = list(geo_path.glob('*.geojson'))+list(geo_path.glob('*.shp'))
            if not files: return None
            file_path = files[0]
        return gpd.read_file(file_path)
    except Exception as e:
        st.warning(f"No se pudieron cargar capas geográficas: {e}")
        return None

# ── HEADER ──
st.markdown("""
<div class="main-header">
    <h1>📊 Dashboard Obeya Comercial 2026</h1>
    <h3>🎯 Análisis Estratégico de Cobertura y Gestión de Personal</h3>
</div>
""", unsafe_allow_html=True)

df_raw = load_csv()
meses_disponibles = sorted(df_raw['MES'].dropna().unique().tolist(), key=lambda m: MES_ORDEN.get(m,99))
zonas_disponibles = sorted(df_raw['ZONA'].dropna().unique().tolist())

# ── SIDEBAR ──
with st.sidebar:
    st.markdown("### 🎯 Panel de Control")
    st.markdown("---")
    st.markdown("#### 📅 Período")
    mes = st.selectbox("Mes", meses_disponibles, key="mes_select")
    años = sorted(df_raw['AÑO'].dropna().unique().tolist(), reverse=True)
    año = st.selectbox("Año", años, index=0, key="año_select")
    st.markdown("---")
    st.markdown("#### 🚨 Filtros de Alerta")
    mostrar_alertas = st.checkbox("🔔 Solo tiendas con alertas", value=False)
    if mostrar_alertas:
        umbral_rotacion = st.slider("Umbral rotación (%)", 0, 50, 10, key="umbral_rot")
        umbral_ausentismo = st.slider("Umbral ausentismo (%)", 0, 50, 15, key="umbral_aus")
        umbral_accidentes = st.slider("Umbral accidentes (%)", 0, 20, 5, key="umbral_acc")
    st.markdown("---")
    if st.button("🔄 Resetear Filtros", use_container_width=True):
        st.session_state['zona_sel'] = 'TODAS'
        st.rerun()

# ── BOTONES DE ZONA ──
if 'zona_sel' not in st.session_state:
    st.session_state['zona_sel'] = 'TODAS'

st.markdown('<div class="section-title">🌍 Filtro por Zona</div>', unsafe_allow_html=True)

todas_zonas = ['TODAS'] + zonas_disponibles
n_cols = min(len(todas_zonas), 5)
btn_cols = st.columns(n_cols)

for i, zona in enumerate(todas_zonas):
    col_idx = i % n_cols
    is_active = st.session_state['zona_sel'] == zona
    label = f"{'✅ ' if is_active else ''}{zona}"
    if btn_cols[col_idx].button(label, key=f"btn_zona_{zona}", use_container_width=True):
        st.session_state['zona_sel'] = zona
        st.rerun()

zona_sel = st.session_state['zona_sel']
if zona_sel != 'TODAS':
    st.info(f"📍 Filtrando por zona: **{zona_sel}** — haz clic en ✅ {zona_sel} para quitar el filtro")

st.markdown("---")

# ── PROCESAR ──
with st.spinner('🔄 Procesando datos...'):
    df = process_data(df_raw, mes, int(año), zona_sel)

if df.empty:
    st.warning(f"⚠️ No hay datos para **{mes} {año}** en la zona seleccionada.")
    st.stop()

df_f = df.copy()
if mostrar_alertas:
    df_f = df_f[
        (df_f['TASA_ROTACION'] >= umbral_rotacion) |
        (df_f['TASA_AUSENTISMO'] >= umbral_ausentismo) |
        (df_f['TASA_ACCIDENTALIDAD'] >= umbral_accidentes)
    ]
if df_f.empty:
    st.warning("⚠️ No hay datos para los filtros de alerta seleccionados.")
    st.stop()

df_oficio = get_oficio_data(df_raw, mes, int(año), zona_sel)
df_rango  = get_rango_permanencia(df_raw, mes, int(año), zona_sel)
df_ccosto = get_tasas_ccosto(df_raw, mes, int(año), zona_sel)

# ── KPIs ──
st.markdown('<div class="section-title">📈 Indicadores Clave de Desempeño</div>', unsafe_allow_html=True)

total_act  = int(df_f['TOTAL_ACTIVOS'].sum())
total_ret  = int(df_f['TOTAL_RETIROS'].sum())
total_aus  = int(df_f['TOTAL_AUSENTISMO'].sum())
total_acc  = int(df_f['TOTAL_ACCIDENTES'].sum())
total_dias = int(df_f['DIAS_AUSENCIA'].sum())
total_hrs  = int(df_f['HORAS_AUSENTISMO'].sum())
pct_tot    = total_act / max(int(df['TOTAL_ACTIVOS'].sum()),1) * 100

k1,k2,k3,k4,k5,k6 = st.columns(6)
k1.metric("👥 Activos",          f"{total_act:,}",  f"{pct_tot:.1f}% del total")
k2.metric("🚪 Retiros",          f"{total_ret:,}",  f"{total_ret/max(total_act,1)*100:.1f}% rot.",  delta_color="inverse")
k3.metric("😷 Ausentismo",       f"{total_aus:,}",  f"{total_aus/max(total_act,1)*100:.1f}% tasa",  delta_color="inverse")
k4.metric("🚑 Accidentes",       f"{total_acc:,}",  f"{total_acc/max(total_act,1)*100:.1f}% tasa",  delta_color="inverse")
k5.metric("📅 Días Ausencia",    f"{total_dias:,}")
k6.metric("⏱️ Horas Ausentismo", f"{total_hrs:,}")

with st.expander("💾 Exportar datos filtrados"):
    st.download_button("📥 Descargar CSV",
        data=df_f.to_csv(index=False).encode('utf-8'),
        file_name=f"Obeya_{zona_sel}_{mes}_{año}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv")

st.markdown("---")

# ── TABS ──
st.markdown('<div class="section-title">📊 Análisis Comparativo</div>', unsafe_allow_html=True)
tab1,tab2,tab3,tab4,tab5,tab6 = st.tabs(["📈 General","🚪 Rotación","😷 Ausentismo","🚑 Accidentes","💼 Por Cargo","📅 Tendencia"])

with tab1:
    c1,c2 = st.columns(2)
    with c1:
        zona_m = df_f.groupby('ZONA').agg(TOTAL_ACTIVOS=('TOTAL_ACTIVOS','sum'),TOTAL_RETIROS=('TOTAL_RETIROS','sum'),TOTAL_AUSENTISMO=('TOTAL_AUSENTISMO','sum'),TOTAL_ACCIDENTES=('TOTAL_ACCIDENTES','sum')).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(name='👥 Activos',   x=zona_m['ZONA'],y=zona_m['TOTAL_ACTIVOS'],  marker_color=COLORS['primary']))
        fig.add_trace(go.Bar(name='🚪 Retiros',   x=zona_m['ZONA'],y=zona_m['TOTAL_RETIROS'],  marker_color=COLORS['retiros']))
        fig.add_trace(go.Bar(name='😷 Ausentismo',x=zona_m['ZONA'],y=zona_m['TOTAL_AUSENTISMO'],marker_color=COLORS['ausentismo']))
        fig.add_trace(go.Bar(name='🚑 Accidentes',x=zona_m['ZONA'],y=zona_m['TOTAL_ACCIDENTES'],marker_color=COLORS['accidentes']))
        fig.update_layout(title='Métricas por Zona',barmode='group',plot_bgcolor='white',paper_bgcolor='white',height=400,xaxis_tickangle=-30)
        st.plotly_chart(fig,use_container_width=True)
    with c2:
        zona_t = df_f.groupby('ZONA').agg(TASA_ROTACION=('TASA_ROTACION','mean'),TASA_AUSENTISMO=('TASA_AUSENTISMO','mean'),TASA_ACCIDENTALIDAD=('TASA_ACCIDENTALIDAD','mean')).reset_index()
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name='% Rotación',      x=zona_t['ZONA'],y=zona_t['TASA_ROTACION'],      marker_color=COLORS['retiros']))
        fig2.add_trace(go.Bar(name='% Ausentismo',    x=zona_t['ZONA'],y=zona_t['TASA_AUSENTISMO'],    marker_color=COLORS['ausentismo']))
        fig2.add_trace(go.Bar(name='% Accidentalidad',x=zona_t['ZONA'],y=zona_t['TASA_ACCIDENTALIDAD'],marker_color=COLORS['accidentes']))
        fig2.update_layout(title='Tasas Promedio por Zona',barmode='group',yaxis_title='%',plot_bgcolor='white',paper_bgcolor='white',height=400,xaxis_tickangle=-30)
        st.plotly_chart(fig2,use_container_width=True)
    fig_sc = px.scatter(df_f,x='TOTAL_ACTIVOS',y='TOTAL_RETIROS',size='TOTAL_AUSENTISMO',color='ZONA',hover_name='ALMACEN',hover_data={'TASA_ROTACION':':.1f','TOTAL_ACCIDENTES':True},title='Relación Activos vs Retiros (tamaño = Ausentismo)',color_discrete_sequence=CHART_COLORS)
    fig_sc.update_layout(plot_bgcolor='white',paper_bgcolor='white',height=380)
    st.plotly_chart(fig_sc,use_container_width=True)

with tab2:
    c1,c2 = st.columns([2,1])
    with c1:
        top_rot = df_f.nlargest(15,'TASA_ROTACION')[['ALMACEN','ZONA','TOTAL_ACTIVOS','TOTAL_RETIROS','TASA_ROTACION','TASA_ROTACION_MENSUAL','TASA_ROTACION_ACT_MES_ANT']].copy()
        fig = go.Figure(go.Bar(y=top_rot['ALMACEN'],x=top_rot['TASA_ROTACION'],orientation='h',text=top_rot['TASA_ROTACION'].round(1),texttemplate='%{text}%',textposition='outside',marker=dict(color=top_rot['TASA_ROTACION'],colorscale=[[0,COLORS['warning']],[1,COLORS['danger']]]),customdata=top_rot[['TOTAL_ACTIVOS','TOTAL_RETIROS','ZONA','TASA_ROTACION_MENSUAL','TASA_ROTACION_ACT_MES_ANT']],hovertemplate='<b>%{y}</b><br>Rotación: %{x:.1f}%<br>Activos: %{customdata[0]}<br>Retiros: %{customdata[1]}<br>Zona: %{customdata[2]}<br>Tasa mensual: %{customdata[3]:.1f}%<br>Mes ant.: %{customdata[4]:.1f}%<extra></extra>'))
        fig.update_layout(title='🚪 Top 15 – Mayor Tasa de Rotación',xaxis_title='Tasa (%)',plot_bgcolor='white',paper_bgcolor='white',height=500,margin=dict(l=200))
        st.plotly_chart(fig,use_container_width=True)
        fig_cmp = go.Figure()
        fig_cmp.add_trace(go.Bar(name='Mes anterior',x=top_rot['ALMACEN'],y=top_rot['TASA_ROTACION_ACT_MES_ANT'],marker_color=COLORS['accent']))
        fig_cmp.add_trace(go.Bar(name='Mes actual',  x=top_rot['ALMACEN'],y=top_rot['TASA_ROTACION_MENSUAL'],    marker_color=COLORS['retiros']))
        fig_cmp.update_layout(title='Comparativa Rotación: Mes Anterior vs Actual',barmode='group',xaxis_tickangle=-45,plot_bgcolor='white',paper_bgcolor='white',height=380)
        st.plotly_chart(fig_cmp,use_container_width=True)
    with c2:
        st.markdown("#### 📊 Estadísticas")
        st.metric("Promedio",    f"{df_f['TASA_ROTACION'].mean():.1f}%")
        st.metric("Mediana",     f"{df_f['TASA_ROTACION'].median():.1f}%")
        st.metric("Máxima",      f"{df_f['TASA_ROTACION'].max():.1f}%")
        st.metric("Tiendas >10%",f"{len(df_f[df_f['TASA_ROTACION']>=10])}")
        st.metric("Total retiros",f"{int(df_f['TOTAL_RETIROS'].sum()):,}")
        fig_d = go.Figure(go.Histogram(x=df_f['TASA_ROTACION'],nbinsx=20,marker_color=COLORS['retiros']))
        fig_d.update_layout(title="Distribución",xaxis_title="Tasa (%)",yaxis_title="Frecuencia",height=260,margin=dict(l=20,r=20,t=40,b=40))
        st.plotly_chart(fig_d,use_container_width=True)

with tab3:
    tot_aus_sum = df_f['TOTAL_AUSENTISMO'].sum()
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("🏥 Médico",        f"{int(df_f['AUS_MEDICO'].sum()):,}",      f"{df_f['AUS_MEDICO'].sum()/max(tot_aus_sum,1)*100:.0f}%")
    k2.metric("⚖️ Legal",         f"{int(df_f['AUS_LEGAL'].sum()):,}",       f"{df_f['AUS_LEGAL'].sum()/max(tot_aus_sum,1)*100:.0f}%")
    k3.metric("🗂️ Administrativo",f"{int(df_f['AUS_ADMINISTRATIVO'].sum()):,}",f"{df_f['AUS_ADMINISTRATIVO'].sum()/max(tot_aus_sum,1)*100:.0f}%")
    k4.metric("📅 Días totales",  f"{int(df_f['DIAS_AUSENCIA'].sum()):,}")
    c1,c2 = st.columns([2,1])
    with c1:
        top_aus = df_f.nlargest(15,'TASA_AUSENTISMO')[['ALMACEN','ZONA','TOTAL_ACTIVOS','TOTAL_AUSENTISMO','AUS_MEDICO','AUS_LEGAL','AUS_ADMINISTRATIVO','DIAS_AUSENCIA','HORAS_AUSENTISMO','TASA_AUSENTISMO']].copy()
        fig = go.Figure(go.Bar(y=top_aus['ALMACEN'],x=top_aus['TASA_AUSENTISMO'],orientation='h',text=top_aus['TASA_AUSENTISMO'].round(1),texttemplate='%{text}%',textposition='outside',marker=dict(color=top_aus['TASA_AUSENTISMO'],colorscale=[[0,'#fff3cd'],[1,COLORS['warning']]]),customdata=top_aus[['TOTAL_ACTIVOS','TOTAL_AUSENTISMO','ZONA','AUS_MEDICO','AUS_LEGAL','AUS_ADMINISTRATIVO','DIAS_AUSENCIA','HORAS_AUSENTISMO']],hovertemplate='<b>%{y}</b><br>Tasa: %{x:.1f}%<br>Activos: %{customdata[0]}<br>Ausentes: %{customdata[1]}<br>Zona: %{customdata[2]}<br>🏥 Médico: %{customdata[3]}<br>⚖️ Legal: %{customdata[4]}<br>🗂️ Admin: %{customdata[5]}<br>📅 Días: %{customdata[6]}<br>⏱️ Horas: %{customdata[7]:.0f}<extra></extra>'))
        fig.update_layout(title='😷 Top 15 – Mayor Tasa de Ausentismo',xaxis_title='Tasa (%)',plot_bgcolor='white',paper_bgcolor='white',height=500,margin=dict(l=200))
        st.plotly_chart(fig,use_container_width=True)
        zona_aus = df_f.groupby('ZONA').agg(AUS_MEDICO=('AUS_MEDICO','sum'),AUS_LEGAL=('AUS_LEGAL','sum'),AUS_ADMINISTRATIVO=('AUS_ADMINISTRATIVO','sum')).reset_index()
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name='🏥 Médico',        x=zona_aus['ZONA'],y=zona_aus['AUS_MEDICO'],        marker_color=COLORS['aus_medico']))
        fig2.add_trace(go.Bar(name='⚖️ Legal',         x=zona_aus['ZONA'],y=zona_aus['AUS_LEGAL'],         marker_color=COLORS['aus_legal']))
        fig2.add_trace(go.Bar(name='🗂️ Administrativo',x=zona_aus['ZONA'],y=zona_aus['AUS_ADMINISTRATIVO'],marker_color=COLORS['aus_admin']))
        fig2.update_layout(title='Composición del Ausentismo por Zona',barmode='stack',plot_bgcolor='white',paper_bgcolor='white',height=360)
        st.plotly_chart(fig2,use_container_width=True)
    with c2:
        st.markdown("#### 📊 Estadísticas")
        st.metric("Promedio",    f"{df_f['TASA_AUSENTISMO'].mean():.1f}%")
        st.metric("Mediana",     f"{df_f['TASA_AUSENTISMO'].median():.1f}%")
        st.metric("Máxima",      f"{df_f['TASA_AUSENTISMO'].max():.1f}%")
        st.metric("Tiendas >15%",f"{len(df_f[df_f['TASA_AUSENTISMO']>=15])}")
        st.metric("⏱️ Horas totales",f"{int(df_f['HORAS_AUSENTISMO'].sum()):,}")
        vals = [df_f['AUS_MEDICO'].sum(),df_f['AUS_LEGAL'].sum(),df_f['AUS_ADMINISTRATIVO'].sum()]
        fig_pie = go.Figure(go.Pie(labels=['Médico','Legal','Admin'],values=vals,marker_colors=[COLORS['aus_medico'],COLORS['aus_legal'],COLORS['aus_admin']],hole=0.4))
        fig_pie.update_layout(title="Composición",height=280,margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig_pie,use_container_width=True)
        fig_d = go.Figure(go.Histogram(x=df_f['TASA_AUSENTISMO'],nbinsx=20,marker_color=COLORS['ausentismo']))
        fig_d.update_layout(title="Distribución",xaxis_title="Tasa (%)",yaxis_title="Frecuencia",height=230,margin=dict(l=20,r=20,t=40,b=40))
        st.plotly_chart(fig_d,use_container_width=True)

with tab4:
    c1,c2 = st.columns([2,1])
    with c1:
        top_acc = df_f.nlargest(15,'TASA_ACCIDENTALIDAD')[['ALMACEN','ZONA','TOTAL_ACTIVOS','TOTAL_ACCIDENTES','TASA_ACCIDENTALIDAD']].copy()
        fig = go.Figure(go.Bar(y=top_acc['ALMACEN'],x=top_acc['TASA_ACCIDENTALIDAD'],orientation='h',text=top_acc['TASA_ACCIDENTALIDAD'].round(1),texttemplate='%{text}%',textposition='outside',marker=dict(color=top_acc['TASA_ACCIDENTALIDAD'],colorscale=[[0,'#c8f7c5'],[1,COLORS['accidentes']]]),customdata=top_acc[['TOTAL_ACTIVOS','TOTAL_ACCIDENTES','ZONA']],hovertemplate='<b>%{y}</b><br>Accidentalidad: %{x:.1f}%<br>Activos: %{customdata[0]}<br>Accidentes: %{customdata[1]}<br>Zona: %{customdata[2]}<extra></extra>'))
        fig.update_layout(title='🚑 Top 15 – Mayor Tasa de Accidentalidad',xaxis_title='Tasa (%)',plot_bgcolor='white',paper_bgcolor='white',height=500,margin=dict(l=200))
        st.plotly_chart(fig,use_container_width=True)
        zona_acc = df_f.groupby('ZONA').agg(TOTAL_ACCIDENTES=('TOTAL_ACCIDENTES','sum'),TOTAL_ACTIVOS=('TOTAL_ACTIVOS','sum')).reset_index()
        zona_acc['TASA'] = zona_acc['TOTAL_ACCIDENTES']/zona_acc['TOTAL_ACTIVOS'].clip(1)*100
        fig2 = px.bar(zona_acc,x='ZONA',y='TOTAL_ACCIDENTES',color='TASA',color_continuous_scale=['#c8f7c5',COLORS['accidentes']],title='Total Accidentes por Zona',labels={'TOTAL_ACCIDENTES':'Accidentes','ZONA':'Zona','TASA':'Tasa %'})
        fig2.update_layout(plot_bgcolor='white',paper_bgcolor='white',height=360)
        st.plotly_chart(fig2,use_container_width=True)
    with c2:
        st.markdown("#### 📊 Estadísticas")
        st.metric("Promedio",   f"{df_f['TASA_ACCIDENTALIDAD'].mean():.1f}%")
        st.metric("Mediana",    f"{df_f['TASA_ACCIDENTALIDAD'].median():.1f}%")
        st.metric("Máxima",     f"{df_f['TASA_ACCIDENTALIDAD'].max():.1f}%")
        st.metric("Tiendas >5%",f"{len(df_f[df_f['TASA_ACCIDENTALIDAD']>=5])}")
        st.metric("Total accidentes",f"{int(df_f['TOTAL_ACCIDENTES'].sum()):,}")
        fig_d = go.Figure(go.Histogram(x=df_f['TASA_ACCIDENTALIDAD'],nbinsx=20,marker_color=COLORS['accidentes']))
        fig_d.update_layout(title="Distribución",xaxis_title="Tasa (%)",yaxis_title="Frecuencia",height=280,margin=dict(l=20,r=20,t=40,b=40))
        st.plotly_chart(fig_d,use_container_width=True)

with tab5:
    if df_oficio.empty:
        st.warning("No hay datos de cargos para el período seleccionado.")
    else:
        st.markdown("#### 💼 Distribución por Cargo (NOM_OFICIO)")
        metrica_cargo = st.radio("Ver por:",["👥 Total Activos","🚪 Retiros","😷 Ausentismo","🚑 Accidentes"],horizontal=True,key="radio_cargo")
        col_cargo = {"👥 Total Activos":"TOTAL_ACTIVOS","🚪 Retiros":"TOTAL_RETIROS","😷 Ausentismo":"TOTAL_AUSENTISMO","🚑 Accidentes":"TOTAL_ACCIDENTES"}[metrica_cargo]
        color_cargo = {"👥 Total Activos":COLORS['primary'],"🚪 Retiros":COLORS['retiros'],"😷 Ausentismo":COLORS['ausentismo'],"🚑 Accidentes":COLORS['accidentes']}[metrica_cargo]
        df_oficio_sorted = df_oficio.sort_values(col_cargo,ascending=True)
        fig_of = go.Figure(go.Bar(y=df_oficio_sorted['NOM_OFICIO'],x=df_oficio_sorted[col_cargo],orientation='h',text=df_oficio_sorted[col_cargo],texttemplate='%{text:,}',textposition='outside',marker_color=color_cargo,customdata=df_oficio_sorted[['TOTAL_ACTIVOS','TOTAL_RETIROS','TOTAL_AUSENTISMO','TOTAL_ACCIDENTES']],hovertemplate='<b>%{y}</b><br>👥 Activos: %{customdata[0]:,}<br>🚪 Retiros: %{customdata[1]:,}<br>😷 Ausentismo: %{customdata[2]:,}<br>🚑 Accidentes: %{customdata[3]:,}<extra></extra>'))
        fig_of.update_layout(title=f'{metrica_cargo} por Cargo',xaxis_title='Total',plot_bgcolor='white',paper_bgcolor='white',height=max(350,len(df_oficio_sorted)*35),margin=dict(l=250,r=80))
        st.plotly_chart(fig_of,use_container_width=True)

        st.markdown("#### 📊 Comparativa Completa por Cargo")
        fig_stk = go.Figure()
        fig_stk.add_trace(go.Bar(name='🚪 Retiros',   x=df_oficio['NOM_OFICIO'],y=df_oficio['TOTAL_RETIROS'],   marker_color=COLORS['retiros']))
        fig_stk.add_trace(go.Bar(name='😷 Ausentismo',x=df_oficio['NOM_OFICIO'],y=df_oficio['TOTAL_AUSENTISMO'],marker_color=COLORS['ausentismo']))
        fig_stk.add_trace(go.Bar(name='🚑 Accidentes',x=df_oficio['NOM_OFICIO'],y=df_oficio['TOTAL_ACCIDENTES'],marker_color=COLORS['accidentes']))
        fig_stk.update_layout(barmode='group',xaxis_tickangle=-35,title='Retiros, Ausentismo y Accidentes por Cargo',plot_bgcolor='white',paper_bgcolor='white',height=420)
        st.plotly_chart(fig_stk,use_container_width=True)

        st.markdown("#### 📋 Tasas (%) por Cargo")
        df_ot = df_oficio.copy()
        act = df_ot['TOTAL_ACTIVOS'].clip(lower=1)
        df_ot['% Rotación']      = (df_ot['TOTAL_RETIROS']   /act*100).round(2)
        df_ot['% Ausentismo']    = (df_ot['TOTAL_AUSENTISMO']/act*100).round(2)
        df_ot['% Accidentalidad']= (df_ot['TOTAL_ACCIDENTES']/act*100).round(2)
        fig_to = go.Figure()
        fig_to.add_trace(go.Bar(name='% Rotación',      x=df_ot['NOM_OFICIO'],y=df_ot['% Rotación'],      marker_color=COLORS['retiros']))
        fig_to.add_trace(go.Bar(name='% Ausentismo',    x=df_ot['NOM_OFICIO'],y=df_ot['% Ausentismo'],    marker_color=COLORS['ausentismo']))
        fig_to.add_trace(go.Bar(name='% Accidentalidad',x=df_ot['NOM_OFICIO'],y=df_ot['% Accidentalidad'],marker_color=COLORS['accidentes']))
        fig_to.update_layout(barmode='group',xaxis_tickangle=-35,yaxis_title='Tasa (%)',title='Tasas (%) por Cargo',plot_bgcolor='white',paper_bgcolor='white',height=400)
        st.plotly_chart(fig_to,use_container_width=True)

        st.markdown("#### 🕐 Retiros por Rango de Permanencia")
        if df_rango.empty:
            st.info("No hay retiros registrados para el período y zona seleccionados.")
        else:
            cr1,cr2 = st.columns([3,1])
            with cr1:
                fig_rg2 = go.Figure(go.Bar(x=df_rango['RANGO_PERMANENCIA'],y=df_rango['TOTAL_RETIROS'],text=df_rango['TOTAL_RETIROS'],texttemplate='%{text}',textposition='outside',marker=dict(color=df_rango['TOTAL_RETIROS'],colorscale=[[0,'#fce4e4'],[1,COLORS['retiros']]],line=dict(color=COLORS['retiros'],width=1)),hovertemplate='<b>%{x}</b><br>Retiros: %{y}<extra></extra>'))
                fig_rg2.update_layout(title='Retiros por Rango de Permanencia (retiro ≥ 1)',xaxis_title='Rango',yaxis_title='Retiros',plot_bgcolor='white',paper_bgcolor='white',height=400,xaxis_tickangle=-35)
                st.plotly_chart(fig_rg2,use_container_width=True)
            with cr2:
                total_r2 = int(df_rango['TOTAL_RETIROS'].sum())
                st.metric("Total retiros",f"{total_r2:,}")
                top_r2 = df_rango.nlargest(1,'TOTAL_RETIROS')
                if not top_r2.empty:
                    st.metric("Rango crítico",top_r2['RANGO_PERMANENCIA'].values[0],f"{int(top_r2['TOTAL_RETIROS'].values[0])} retiros")
                fig_pie_r2 = go.Figure(go.Pie(labels=df_rango['RANGO_PERMANENCIA'],values=df_rango['TOTAL_RETIROS'],hole=0.35,marker_colors=CHART_COLORS[:len(df_rango)]))
                fig_pie_r2.update_layout(title="Distribución",height=320,margin=dict(l=5,r=5,t=40,b=5),showlegend=True,legend=dict(font=dict(size=9)))
                st.plotly_chart(fig_pie_r2,use_container_width=True)

with tab6:
    st.markdown("#### 📈 Evolución Mensual (todos los períodos)")
    df_trend = df_raw.copy() if zona_sel=='TODAS' else df_raw[df_raw['ZONA']==zona_sel].copy()
    for col in ['TASA_ROTACION_MENSUAL','TASA_ROTACION_ACT_MES_ANT','TASA_DE_ACCIDENTALIDAD']:
        if col in df_trend.columns: df_trend[col] = parse_pct(df_trend[col])
    trend = df_trend.groupby(['MES','AÑO']).agg(TOTAL_ACTIVOS=('TOTAL_ACTIVOS','sum'),TOTAL_RETIROS=('TOTAL_RETIROS','sum'),TOTAL_AUSENTISMO=('TOTAL_AUSENTISMO','sum'),TOTAL_ACCIDENTES=('TOTAL_ACCIDENTES','sum')).reset_index()
    trend['MES_NUM'] = trend['MES'].map(MES_ORDEN).fillna(0)
    trend = trend.sort_values(['AÑO','MES_NUM'])
    trend['PERIODO'] = trend['MES'].str.replace(r'^\d+\.\s*','',regex=True)+' '+trend['AÑO'].astype(str)
    trend['TASA_ROT'] = (trend['TOTAL_RETIROS']/trend['TOTAL_ACTIVOS'].clip(1)*100).round(2)
    trend['TASA_AUS'] = (trend['TOTAL_AUSENTISMO']/trend['TOTAL_ACTIVOS'].clip(1)*100).round(2)
    trend['TASA_ACC'] = (trend['TOTAL_ACCIDENTES']/trend['TOTAL_ACTIVOS'].clip(1)*100).round(2)
    fig_t = go.Figure()
    fig_t.add_trace(go.Scatter(x=trend['PERIODO'],y=trend['TASA_ROT'],mode='lines+markers',name='% Rotación',   line=dict(color=COLORS['retiros'],   width=2)))
    fig_t.add_trace(go.Scatter(x=trend['PERIODO'],y=trend['TASA_AUS'],mode='lines+markers',name='% Ausentismo', line=dict(color=COLORS['ausentismo'],width=2)))
    fig_t.add_trace(go.Scatter(x=trend['PERIODO'],y=trend['TASA_ACC'],mode='lines+markers',name='% Accidentalidad',line=dict(color=COLORS['accidentes'],width=2)))
    fig_t.update_layout(title='Evolución de Tasas por Período',xaxis_title='Período',yaxis_title='Tasa (%)',plot_bgcolor='white',paper_bgcolor='white',height=420,xaxis_tickangle=-45,legend=dict(orientation='h',y=1.1))
    st.plotly_chart(fig_t,use_container_width=True)
    fig_act = go.Figure()
    for anio in sorted(trend['AÑO'].unique()):
        d = trend[trend['AÑO']==anio]
        fig_act.add_trace(go.Scatter(x=d['MES'].str.replace(r'^\d+\.\s*','',regex=True),y=d['TOTAL_ACTIVOS'],mode='lines+markers',name=str(anio)))
    fig_act.update_layout(title='Personal Activo por Mes y Año',xaxis_title='Mes',yaxis_title='Total Activos',plot_bgcolor='white',paper_bgcolor='white',height=360)
    st.plotly_chart(fig_act,use_container_width=True)

st.markdown("---")

# ── TASAS POR NOM_CCOSTO ──
st.markdown('<div class="section-title">🏪 Tasas por Tienda (NOM_CCOSTO)</div>', unsafe_allow_html=True)

if not df_ccosto.empty:
    top_n = st.slider("Número de tiendas a mostrar",5,min(50,len(df_ccosto)),20,key="top_ccosto")
    tasa_ccosto_sel = st.radio("Ordenar por:",["TASA_ROTACION","TASA_AUSENTISMO","TASA_ACCIDENTALIDAD"],format_func=lambda x:{"TASA_ROTACION":"% Rotación","TASA_AUSENTISMO":"% Ausentismo","TASA_ACCIDENTALIDAD":"% Accidentalidad"}[x],horizontal=True,key="radio_ccosto")
    top_cc = df_ccosto.nlargest(top_n,tasa_ccosto_sel)
    fig_cc = go.Figure()
    fig_cc.add_trace(go.Bar(name='% Rotación',      y=top_cc['ALMACEN'],x=top_cc['TASA_ROTACION'],      orientation='h',marker_color=COLORS['retiros'],   hovertemplate='<b>%{y}</b><br>Rotación: %{x:.1f}%<extra></extra>'))
    fig_cc.add_trace(go.Bar(name='% Ausentismo',    y=top_cc['ALMACEN'],x=top_cc['TASA_AUSENTISMO'],    orientation='h',marker_color=COLORS['ausentismo'], hovertemplate='<b>%{y}</b><br>Ausentismo: %{x:.1f}%<extra></extra>'))
    fig_cc.add_trace(go.Bar(name='% Accidentalidad',y=top_cc['ALMACEN'],x=top_cc['TASA_ACCIDENTALIDAD'],orientation='h',marker_color=COLORS['accidentes'], hovertemplate='<b>%{y}</b><br>Accidentalidad: %{x:.1f}%<extra></extra>'))
    fig_cc.update_layout(title=f'Top {top_n} Tiendas – Las 3 Tasas Comparadas',barmode='group',xaxis_title='Tasa (%)',plot_bgcolor='white',paper_bgcolor='white',height=max(400,top_n*28),margin=dict(l=230,r=80))
    st.plotly_chart(fig_cc,use_container_width=True)

    st.markdown("##### 🌡️ Heatmap de Tasas por Tienda")
    top_heat = df_ccosto.nlargest(top_n,tasa_ccosto_sel)[['ALMACEN','TASA_ROTACION','TASA_AUSENTISMO','TASA_ACCIDENTALIDAD']].set_index('ALMACEN')
    fig_heat = go.Figure(go.Heatmap(z=top_heat.values,x=['% Rotación','% Ausentismo','% Accidentalidad'],y=top_heat.index.tolist(),colorscale='RdYlGn_r',text=top_heat.values.round(1),texttemplate='%{text}%',hovertemplate='Tienda: %{y}<br>Métrica: %{x}<br>Tasa: %{z:.1f}%<extra></extra>'))
    fig_heat.update_layout(title='Heatmap de Tasas por Tienda',plot_bgcolor='white',paper_bgcolor='white',height=max(400,top_n*25),margin=dict(l=230))
    st.plotly_chart(fig_heat,use_container_width=True)

st.markdown("---")

# ── RANGO DE PERMANENCIA ──
st.markdown('<div class="section-title">🕐 Retiros por Rango de Permanencia</div>', unsafe_allow_html=True)

if df_rango.empty:
    st.info("No hay retiros registrados (RETIROS ≥ 1) para el período y zona seleccionados.")
else:
    cr1,cr2 = st.columns([3,1])
    with cr1:
        fig_rg = go.Figure(go.Bar(x=df_rango['RANGO_PERMANENCIA'],y=df_rango['TOTAL_RETIROS'],text=df_rango['TOTAL_RETIROS'],texttemplate='%{text}',textposition='outside',marker=dict(color=df_rango['TOTAL_RETIROS'],colorscale=[[0,'#fce4e4'],[1,COLORS['retiros']]],line=dict(color=COLORS['retiros'],width=1)),hovertemplate='<b>%{x}</b><br>Retiros: %{y}<extra></extra>'))
        fig_rg.update_layout(title='Retiros por Rango de Permanencia (registros con retiro ≥ 1)',xaxis_title='Rango de Permanencia',yaxis_title='Total Retiros',plot_bgcolor='white',paper_bgcolor='white',height=420,xaxis_tickangle=-35)
        st.plotly_chart(fig_rg,use_container_width=True)
    with cr2:
        total_r = int(df_rango['TOTAL_RETIROS'].sum())
        st.metric("Total retiros",  f"{total_r:,}")
        st.metric("Rangos activos", f"{len(df_rango)}")
        top_r = df_rango.nlargest(1,'TOTAL_RETIROS')
        if not top_r.empty:
            st.metric("Rango más crítico",top_r['RANGO_PERMANENCIA'].values[0],f"{int(top_r['TOTAL_RETIROS'].values[0])} retiros")
        df_rango_pct = df_rango.copy()
        df_rango_pct['%'] = (df_rango_pct['TOTAL_RETIROS']/total_r*100).round(1)
        st.dataframe(df_rango_pct[['RANGO_PERMANENCIA','TOTAL_RETIROS','%']].rename(columns={'RANGO_PERMANENCIA':'Rango','TOTAL_RETIROS':'Retiros'}),hide_index=True,height=320)

st.markdown("---")

# ── MAPA ──
st.markdown('<div class="section-title">🗺️ Vista Geográfica</div>', unsafe_allow_html=True)

col_map,col_cfg = st.columns([4,1])
with col_cfg:
    st.markdown("#### ⚙️ Config")
    metrica_mapa = st.selectbox("Métrica",['Total Activos','Tasa Rotación','Tasa Ausentismo','Tasa Accidentalidad','Días Ausencia','Horas Ausentismo'],key="metrica_mapa")
    tamaño_base   = st.slider("Tamaño base",3,15,6,key="tam_mapa")
    factor_escala = st.slider("Escala",0.1,2.0,0.4,step=0.1,key="esc_mapa")
    mostrar_capa  = st.checkbox("Mostrar capa geográfica",value=False)
    st.caption(f"📍 Puntos: {len(df_f)}")
    st.caption(f"🌍 Zonas: {df_f['ZONA'].nunique()}")

with col_map:
    df_map = df_f.dropna(subset=['LATITUD','LONGITUD']).copy()
    COL_MAP = {'Total Activos':('TOTAL_ACTIVOS',COLORS['primary']),'Tasa Rotación':('TASA_ROTACION',COLORS['retiros']),'Tasa Ausentismo':('TASA_AUSENTISMO',COLORS['ausentismo']),'Tasa Accidentalidad':('TASA_ACCIDENTALIDAD',COLORS['accidentes']),'Días Ausencia':('DIAS_AUSENCIA',COLORS['aus_medico']),'Horas Ausentismo':('HORAS_AUSENTISMO',COLORS['info'])}
    col_val,color_base = COL_MAP[metrica_mapa]
    if df_map.empty:
        st.error("❌ No hay coordenadas válidas para mostrar.")
    else:
        m = folium.Map(location=[df_map['LATITUD'].mean(),df_map['LONGITUD'].mean()],zoom_start=11,tiles='CartoDB positron',control_scale=True,prefer_canvas=True)
        if mostrar_capa:
            gdf = load_geojson()
            if gdf is not None:
                folium.GeoJson(gdf,name='Capa Geográfica',style_function=lambda x:{'fillColor':'#7fa8e0','color':'#1e3c72','weight':2,'fillOpacity':0.2}).add_to(m)
        zonas_u  = df_map['ZONA'].dropna().unique()
        col_zona = {z:CHART_COLORS[i%len(CHART_COLORS)] for i,z in enumerate(zonas_u)}
        for _,row in df_map.iterrows():
            valor  = row.get(col_val,0)
            radio  = max(tamaño_base,float(valor)*factor_escala)
            color  = col_zona.get(row['ZONA'],color_base)
            alerta = (row['TASA_ROTACION']>=10 or row['TASA_AUSENTISMO']>=15 or row['TASA_ACCIDENTALIDAD']>=5)
            popup_html = f"""<div style="font-family:Arial;min-width:270px;"><h4 style="margin:0;color:{COLORS['primary']};"> {'🚨 ' if alerta else ''}{row['ALMACEN']}</h4><hr style="margin:5px 0;"><table style="width:100%;font-size:12px;"><tr><td>📍 Zona:</td><td><b>{row['ZONA']}</b></td></tr><tr><td colspan=2><hr style="margin:2px 0;"></td></tr><tr><td>👥 Activos:</td><td><b>{int(row['TOTAL_ACTIVOS'])}</b></td></tr><tr><td>🚪 Retiros:</td><td><b>{int(row['TOTAL_RETIROS'])} ({row['TASA_ROTACION']:.1f}%)</b></td></tr><tr><td>😷 Ausentismo:</td><td><b>{int(row['TOTAL_AUSENTISMO'])} ({row['TASA_AUSENTISMO']:.1f}%)</b></td></tr><tr><td>  ↳ Médico:</td><td>{int(row.get('AUS_MEDICO',0))}</td></tr><tr><td>  ↳ Legal:</td><td>{int(row.get('AUS_LEGAL',0))}</td></tr><tr><td>  ↳ Admin:</td><td>{int(row.get('AUS_ADMINISTRATIVO',0))}</td></tr><tr><td>📅 Días:</td><td><b>{int(row.get('DIAS_AUSENCIA',0))}</b></td></tr><tr><td>⏱️ Horas:</td><td><b>{int(row.get('HORAS_AUSENTISMO',0))}</b></td></tr><tr><td>🚑 Accidentes:</td><td><b>{int(row['TOTAL_ACCIDENTES'])} ({row['TASA_ACCIDENTALIDAD']:.1f}%)</b></td></tr></table></div>"""
            folium.CircleMarker(location=[row['LATITUD'],row['LONGITUD']],radius=radio,popup=folium.Popup(popup_html,max_width=320),color=color,fill=True,fill_color=color,fill_opacity=0.7,weight=2,tooltip=f"{row['ALMACEN']} – {metrica_mapa}: {valor:.1f}").add_to(m)
        folium.LayerControl().add_to(m)
        st_folium(m,width=None,height=600,returned_objects=[])
        st.success(f"✅ {len(df_map)} ubicaciones | Métrica: {metrica_mapa}")

st.markdown("---")

# ── TABLA DETALLADA ──
st.markdown('<div class="section-title">📋 Datos Detallados por Tienda</div>', unsafe_allow_html=True)

all_cols = ['ALMACEN','ZONA','TOTAL_ACTIVOS','TOTAL_RETIROS','TOTAL_AUSENTISMO','AUS_MEDICO','AUS_LEGAL','AUS_ADMINISTRATIVO','DIAS_AUSENCIA','HORAS_AUSENTISMO','TOTAL_ACCIDENTES','TASA_ROTACION','TASA_AUSENTISMO','TASA_ACCIDENTALIDAD','TASA_ROTACION_MENSUAL','TASA_ROTACION_ACT_MES_ANT','FECHA']
existing_cols = [c for c in all_cols if c in df_f.columns]
default_cols  = [c for c in ['ALMACEN','ZONA','TOTAL_ACTIVOS','TOTAL_RETIROS','TOTAL_AUSENTISMO','AUS_MEDICO','AUS_LEGAL','AUS_ADMINISTRATIVO','DIAS_AUSENCIA','TOTAL_ACCIDENTES'] if c in existing_cols]
tc1,tc2,tc3 = st.columns(3)
with tc1: mcols = st.multiselect("Columnas",options=existing_cols,default=default_cols,key="cols_tabla")
with tc2: n_reg = st.selectbox("Registros",[10,25,50,100,"Todos"],index=1,key="n_tabla")
with tc3:
    sort_opts = [c for c in ['TOTAL_ACTIVOS','TASA_ROTACION','TASA_AUSENTISMO','TASA_ACCIDENTALIDAD','ALMACEN'] if c in df_f.columns]
    sort_col  = st.selectbox("Ordenar por",sort_opts,key="sort_tabla")
    asc       = st.checkbox("Ascendente",value=False,key="asc_tabla")
if mcols:
    tabla = df_f[mcols].sort_values(sort_col,ascending=asc)
    if n_reg != "Todos": tabla = tabla.head(int(n_reg))
    col_cfg_t = {"ALMACEN":st.column_config.TextColumn("🏪 Tienda",width="medium"),"ZONA":st.column_config.TextColumn("📍 Zona",width="small"),"TOTAL_ACTIVOS":st.column_config.NumberColumn("👥 Activos",format="%d"),"TOTAL_RETIROS":st.column_config.NumberColumn("🚪 Retiros",format="%d"),"TOTAL_AUSENTISMO":st.column_config.NumberColumn("😷 Aus. Total",format="%d"),"AUS_MEDICO":st.column_config.NumberColumn("🏥 Médico",format="%d"),"AUS_LEGAL":st.column_config.NumberColumn("⚖️ Legal",format="%d"),"AUS_ADMINISTRATIVO":st.column_config.NumberColumn("🗂️ Admin",format="%d"),"DIAS_AUSENCIA":st.column_config.NumberColumn("📅 Días",format="%d"),"HORAS_AUSENTISMO":st.column_config.NumberColumn("⏱️ Horas",format="%.0f"),"TOTAL_ACCIDENTES":st.column_config.NumberColumn("🚑 Accidentes",format="%d"),"TASA_ROTACION":st.column_config.NumberColumn("% Rotación",format="%.1f%%"),"TASA_AUSENTISMO":st.column_config.NumberColumn("% Ausentismo",format="%.1f%%"),"TASA_ACCIDENTALIDAD":st.column_config.NumberColumn("% Accidentalidad",format="%.1f%%"),"TASA_ROTACION_MENSUAL":st.column_config.NumberColumn("% Rot. Mensual",format="%.1f%%"),"TASA_ROTACION_ACT_MES_ANT":st.column_config.NumberColumn("% Rot. Mes Ant.",format="%.1f%%"),"FECHA":st.column_config.TextColumn("📅 Período")}
    st.dataframe(tabla,use_container_width=True,hide_index=True,column_config=col_cfg_t,height=400)
    st.caption(f"📊 Mostrando {len(tabla):,} de {len(df_f):,} registros | Total general: {len(df):,}")

# ── FOOTER ──
st.markdown("---")
st.markdown(f"""
<div style="text-align:center;padding:20px;background:linear-gradient(135deg,{COLORS['gradient_start']} 0%,{COLORS['gradient_end']} 100%);color:white;border-radius:10px;">
    <h4>📊 Dashboard Obeya Comercial 2026</h4>
    <p style="margin:5px 0;"><b>Generado:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | <b>Período:</b> {mes} {año} | <b>Zona:</b> {zona_sel} | <b>Registros:</b> {len(df_f):,} de {len(df):,}</p>
</div>
""", unsafe_allow_html=True)