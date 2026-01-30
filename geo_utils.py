"""
Utilidades para Procesamiento de Datos Geográficos
Dashboard Obeya Comercial 2026

Este script contiene funciones útiles para:
- Validar archivos .shp y .geojson
- Convertir entre formatos
- Verificar sistemas de coordenadas
- Generar capas geográficas de prueba
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
import json
from shapely.geometry import Point, Polygon
import warnings
warnings.filterwarnings('ignore')

# ==========================
# FUNCIONES DE VALIDACIÓN
# ==========================

def validar_geojson(filepath):
    """
    Valida un archivo GeoJSON y muestra información básica
    
    Args:
        filepath: Ruta al archivo .geojson
    
    Returns:
        dict: Información del archivo o None si hay error
    """
    try:
        gdf = gpd.read_file(filepath)
        
        info = {
            'archivo': filepath,
            'features': len(gdf),
            'geometria_tipo': gdf.geometry.type.unique().tolist(),
            'crs': str(gdf.crs),
            'columnas': gdf.columns.tolist(),
            'bounds': gdf.total_bounds.tolist(),
            'valido': True
        }
        
        print(f"✅ Archivo válido: {filepath}")
        print(f"   - Features: {info['features']}")
        print(f"   - Tipo: {info['geometria_tipo']}")
        print(f"   - CRS: {info['crs']}")
        print(f"   - Columnas: {', '.join(info['columnas'])}")
        
        return info
        
    except Exception as e:
        print(f"❌ Error al validar {filepath}: {str(e)}")
        return None


def validar_shapefile(filepath):
    """
    Valida un archivo Shapefile y muestra información básica
    
    Args:
        filepath: Ruta al archivo .shp
    
    Returns:
        dict: Información del archivo o None si hay error
    """
    try:
        gdf = gpd.read_file(filepath)
        
        # Verificar archivos asociados
        base_path = Path(filepath).with_suffix('')
        archivos_requeridos = ['.shp', '.shx', '.dbf']
        archivos_encontrados = []
        archivos_faltantes = []
        
        for ext in archivos_requeridos:
            if (base_path.parent / f"{base_path.name}{ext}").exists():
                archivos_encontrados.append(ext)
            else:
                archivos_faltantes.append(ext)
        
        info = {
            'archivo': filepath,
            'features': len(gdf),
            'geometria_tipo': gdf.geometry.type.unique().tolist(),
            'crs': str(gdf.crs),
            'columnas': gdf.columns.tolist(),
            'bounds': gdf.total_bounds.tolist(),
            'archivos_asociados': archivos_encontrados,
            'archivos_faltantes': archivos_faltantes,
            'valido': len(archivos_faltantes) == 0
        }
        
        print(f"{'✅' if info['valido'] else '⚠️'} Archivo: {filepath}")
        print(f"   - Features: {info['features']}")
        print(f"   - Tipo: {info['geometria_tipo']}")
        print(f"   - CRS: {info['crs']}")
        print(f"   - Archivos encontrados: {', '.join(archivos_encontrados)}")
        if archivos_faltantes:
            print(f"   - Archivos faltantes: {', '.join(archivos_faltantes)}")
        
        return info
        
    except Exception as e:
        print(f"❌ Error al validar {filepath}: {str(e)}")
        return None


def validar_directorio_geodata(directorio):
    """
    Valida todos los archivos geográficos en un directorio
    
    Args:
        directorio: Ruta al directorio con archivos geográficos
    
    Returns:
        dict: Resumen de validación
    """
    path = Path(directorio)
    
    if not path.exists():
        print(f"❌ El directorio no existe: {directorio}")
        return None
    
    archivos_geojson = list(path.glob('*.geojson'))
    archivos_shp = list(path.glob('*.shp'))
    
    print(f"\n📁 Validando directorio: {directorio}")
    print(f"   GeoJSON encontrados: {len(archivos_geojson)}")
    print(f"   Shapefiles encontrados: {len(archivos_shp)}")
    print("-" * 60)
    
    resultados = {
        'geojson': [],
        'shapefile': [],
        'total_validos': 0,
        'total_invalidos': 0
    }
    
    # Validar GeoJSON
    for archivo in archivos_geojson:
        info = validar_geojson(archivo)
        resultados['geojson'].append(info)
        if info and info['valido']:
            resultados['total_validos'] += 1
        else:
            resultados['total_invalidos'] += 1
        print()
    
    # Validar Shapefiles
    for archivo in archivos_shp:
        info = validar_shapefile(archivo)
        resultados['shapefile'].append(info)
        if info and info['valido']:
            resultados['total_validos'] += 1
        else:
            resultados['total_invalidos'] += 1
        print()
    
    print("=" * 60)
    print(f"📊 Resumen: {resultados['total_validos']} válidos, {resultados['total_invalidos']} con problemas")
    
    return resultados


# ==========================
# FUNCIONES DE CONVERSIÓN
# ==========================

def shp_a_geojson(input_shp, output_geojson=None):
    """
    Convierte un archivo Shapefile a GeoJSON
    
    Args:
        input_shp: Ruta al archivo .shp
        output_geojson: Ruta de salida (opcional, se genera automáticamente si no se proporciona)
    
    Returns:
        str: Ruta al archivo generado o None si hay error
    """
    try:
        gdf = gpd.read_file(input_shp)
        
        # Generar nombre de salida si no se proporciona
        if output_geojson is None:
            output_geojson = str(Path(input_shp).with_suffix('.geojson'))
        
        # Convertir a WGS84 si es necesario (para compatibilidad web)
        if gdf.crs and gdf.crs.to_string() != 'EPSG:4326':
            print(f"🔄 Convirtiendo de {gdf.crs} a EPSG:4326")
            gdf = gdf.to_crs('EPSG:4326')
        
        # Guardar
        gdf.to_file(output_geojson, driver='GeoJSON')
        print(f"✅ Archivo convertido exitosamente: {output_geojson}")
        
        return output_geojson
        
    except Exception as e:
        print(f"❌ Error al convertir {input_shp}: {str(e)}")
        return None


def geojson_a_shp(input_geojson, output_shp=None):
    """
    Convierte un archivo GeoJSON a Shapefile
    
    Args:
        input_geojson: Ruta al archivo .geojson
        output_shp: Ruta de salida (opcional)
    
    Returns:
        str: Ruta al archivo generado o None si hay error
    """
    try:
        gdf = gpd.read_file(input_geojson)
        
        # Generar nombre de salida si no se proporciona
        if output_shp is None:
            output_shp = str(Path(input_geojson).with_suffix('.shp'))
        
        # Guardar
        gdf.to_file(output_shp, driver='ESRI Shapefile')
        print(f"✅ Archivo convertido exitosamente: {output_shp}")
        
        return output_shp
        
    except Exception as e:
        print(f"❌ Error al convertir {input_geojson}: {str(e)}")
        return None


def reproyectar_archivo(input_file, output_file, target_crs='EPSG:4326'):
    """
    Reproyecta un archivo geográfico a un sistema de coordenadas específico
    
    Args:
        input_file: Archivo de entrada (.shp o .geojson)
        output_file: Archivo de salida
        target_crs: Sistema de coordenadas destino (por defecto WGS84)
    
    Returns:
        str: Ruta al archivo generado o None si hay error
    """
    try:
        gdf = gpd.read_file(input_file)
        
        if gdf.crs is None:
            print("⚠️ El archivo no tiene CRS definido. Se asumirá EPSG:4326")
            gdf = gdf.set_crs('EPSG:4326')
        
        print(f"🔄 Reproyectando de {gdf.crs} a {target_crs}")
        gdf_reproj = gdf.to_crs(target_crs)
        
        # Determinar driver según extensión
        extension = Path(output_file).suffix.lower()
        if extension == '.geojson':
            driver = 'GeoJSON'
        elif extension == '.shp':
            driver = 'ESRI Shapefile'
        else:
            raise ValueError(f"Extensión no soportada: {extension}")
        
        gdf_reproj.to_file(output_file, driver=driver)
        print(f"✅ Archivo reproyectado exitosamente: {output_file}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error al reproyectar {input_file}: {str(e)}")
        return None


# ==========================
# FUNCIONES DE GENERACIÓN
# ==========================

def crear_puntos_desde_csv(csv_file, output_file, lat_col='latitud', lon_col='longitud', crs='EPSG:4326'):
    """
    Crea un archivo geográfico de puntos desde un CSV con coordenadas
    
    Args:
        csv_file: Archivo CSV con coordenadas
        output_file: Archivo de salida (.geojson o .shp)
        lat_col: Nombre de columna de latitud
        lon_col: Nombre de columna de longitud
        crs: Sistema de coordenadas
    
    Returns:
        str: Ruta al archivo generado o None si hay error
    """
    try:
        # Leer CSV
        df = pd.read_csv(csv_file)
        
        # Verificar columnas
        if lat_col not in df.columns or lon_col not in df.columns:
            raise ValueError(f"El CSV debe contener las columnas '{lat_col}' y '{lon_col}'")
        
        # Convertir a numérico
        df[lat_col] = pd.to_numeric(df[lat_col], errors='coerce')
        df[lon_col] = pd.to_numeric(df[lon_col], errors='coerce')
        
        # Eliminar filas sin coordenadas
        df = df.dropna(subset=[lat_col, lon_col])
        
        # Crear geometría
        geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
        
        # Crear GeoDataFrame
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=crs)
        
        # Determinar driver
        extension = Path(output_file).suffix.lower()
        if extension == '.geojson':
            driver = 'GeoJSON'
        elif extension == '.shp':
            driver = 'ESRI Shapefile'
        else:
            raise ValueError(f"Extensión no soportada: {extension}")
        
        # Guardar
        gdf.to_file(output_file, driver=driver)
        print(f"✅ Archivo de puntos creado exitosamente: {output_file}")
        print(f"   - Puntos generados: {len(gdf)}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error al crear archivo de puntos: {str(e)}")
        return None


def crear_zona_ejemplo(nombre, centro_lat, centro_lon, radio_km, output_file):
    """
    Crea un polígono circular de ejemplo (zona o isocrona)
    
    Args:
        nombre: Nombre de la zona
        centro_lat: Latitud del centro
        centro_lon: Longitud del centro
        radio_km: Radio en kilómetros
        output_file: Archivo de salida
    
    Returns:
        str: Ruta al archivo generado o None si hay error
    """
    try:
        from shapely.geometry import Point
        import math
        
        # Convertir km a grados (aproximado)
        radio_grados = radio_km / 111.0
        
        # Crear punto central
        centro = Point(centro_lon, centro_lat)
        
        # Crear círculo (aproximado con buffer)
        circulo = centro.buffer(radio_grados)
        
        # Crear GeoDataFrame
        gdf = gpd.GeoDataFrame({
            'nombre': [nombre],
            'radio_km': [radio_km],
            'centro_lat': [centro_lat],
            'centro_lon': [centro_lon]
        }, geometry=[circulo], crs='EPSG:4326')
        
        # Determinar driver
        extension = Path(output_file).suffix.lower()
        if extension == '.geojson':
            driver = 'GeoJSON'
        elif extension == '.shp':
            driver = 'ESRI Shapefile'
        else:
            raise ValueError(f"Extensión no soportada: {extension}")
        
        # Guardar
        gdf.to_file(output_file, driver=driver)
        print(f"✅ Zona de ejemplo creada: {output_file}")
        print(f"   - Nombre: {nombre}")
        print(f"   - Radio: {radio_km} km")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error al crear zona: {str(e)}")
        return None


# ==========================
# EJEMPLO DE USO
# ==========================

if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("UTILIDADES PARA DATOS GEOGRÁFICOS")
    print("Dashboard Obeya Comercial 2026")
    print("=" * 60)
    print()
    
    # Ejemplo: Validar directorio
    if len(sys.argv) > 1:
        directorio = sys.argv[1]
        validar_directorio_geodata(directorio)
    else:
        print("Uso:")
        print("  python geo_utils.py <directorio>  # Validar archivos en directorio")
        print()
        print("Funciones disponibles:")
        print("  - validar_geojson(filepath)")
        print("  - validar_shapefile(filepath)")
        print("  - validar_directorio_geodata(directorio)")
        print("  - shp_a_geojson(input_shp, output_geojson)")
        print("  - geojson_a_shp(input_geojson, output_shp)")
        print("  - reproyectar_archivo(input_file, output_file, target_crs)")
        print("  - crear_puntos_desde_csv(csv_file, output_file)")
        print("  - crear_zona_ejemplo(nombre, centro_lat, centro_lon, radio_km, output_file)")
        print()
        print("Ejemplo de uso en código:")
        print("""
from geo_utils import *

# Validar archivo
validar_geojson('mi_archivo.geojson')

# Convertir shapefile a geojson
shp_a_geojson('entrada.shp', 'salida.geojson')

# Crear puntos desde CSV
crear_puntos_desde_csv('tiendas.csv', 'tiendas.geojson')

# Crear zona de ejemplo
crear_zona_ejemplo('Zona Norte', 4.6097, -74.0817, 5, 'zona_norte.geojson')
        """)
