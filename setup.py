"""
Script de Inicialización
Dashboard Obeya Comercial 2026

Este script ayuda a configurar el dashboard por primera vez:
- Verifica dependencias
- Crea estructura de directorios
- Valida base de datos
- Genera archivos de configuración
"""

import sys
import os
from pathlib import Path
import subprocess

def print_header(text):
    """Imprime un encabezado formateado"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def verificar_python():
    """Verifica la versión de Python"""
    print("🔍 Verificando versión de Python...")
    version = sys.version_info
    
    if version.major >= 3 and version.minor >= 8:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} - Requiere Python 3.8+")
        return False


def verificar_dependencias():
    """Verifica si las dependencias están instaladas"""
    print("\n🔍 Verificando dependencias...")
    
    dependencias_requeridas = [
        'streamlit',
        'pandas',
        'numpy',
        'plotly',
        'folium',
        'streamlit_folium',
        'geopandas',
        'shapely'
    ]
    
    dependencias_faltantes = []
    dependencias_ok = []
    
    for dep in dependencias_requeridas:
        try:
            __import__(dep)
            dependencias_ok.append(dep)
            print(f"   ✅ {dep}")
        except ImportError:
            dependencias_faltantes.append(dep)
            print(f"   ❌ {dep} - NO INSTALADO")
    
    if dependencias_faltantes:
        print("\n⚠️  Dependencias faltantes detectadas.")
        print("   Ejecutar: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ Todas las dependencias están instaladas")
        return True


def crear_estructura_directorios():
    """Crea la estructura de directorios necesaria"""
    print("\n📁 Creando estructura de directorios...")
    
    directorios = [
        'data',
        'geodata',
        '.streamlit',
        'logs'
    ]
    
    for directorio in directorios:
        path = Path(directorio)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ Creado: {directorio}/")
        else:
            print(f"   ℹ️  Ya existe: {directorio}/")
    
    return True


def crear_archivo_env():
    """Crea archivo .env si no existe"""
    print("\n📝 Configurando archivo de entorno...")
    
    env_path = Path('.env')
    
    if env_path.exists():
        print("   ℹ️  El archivo .env ya existe")
        respuesta = input("   ¿Deseas sobrescribirlo? (s/N): ").lower()
        if respuesta != 's':
            return True
    
    # Solicitar rutas
    print("\n   Por favor, proporciona las siguientes rutas:")
    
    db_path = input("   Ruta a la base de datos (Maestro.db): ").strip()
    if not db_path:
        db_path = str(Path.cwd() / 'data' / 'Maestro.db')
        print(f"   Usando ruta por defecto: {db_path}")
    
    geo_path = input("   Ruta a archivos geográficos: ").strip()
    if not geo_path:
        geo_path = str(Path.cwd() / 'geodata')
        print(f"   Usando ruta por defecto: {geo_path}")
    
    # Crear contenido del .env
    env_content = f"""# Configuración de Entorno - Dashboard Obeya 2026
# Generado automáticamente

# Rutas principales
DATABASE_PATH={db_path}
GEODATA_PATH={geo_path}

# Configuración
DEBUG=False
CACHE_TTL=300

# Streamlit
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
"""
    
    # Escribir archivo
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print(f"\n   ✅ Archivo .env creado exitosamente")
    return True


def verificar_base_datos():
    """Verifica que la base de datos existe y tiene las tablas necesarias"""
    print("\n🔍 Verificando base de datos...")
    
    try:
        from pathlib import Path
        
        # Leer ruta del .env si existe
        env_path = Path('.env')
        db_path = None
        
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('DATABASE_PATH='):
                        db_path = line.split('=', 1)[1].strip()
                        break
        
        if not db_path:
            db_path = input("   Ruta a la base de datos: ").strip()
        
        if not Path(db_path).exists():
            print(f"   ❌ No se encuentra la base de datos en: {db_path}")
            print("   Por favor, coloca el archivo Maestro.db en la ubicación correcta")
            return False
        
        # Verificar tablas
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Obtener lista de tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tablas = [row[0] for row in cursor.fetchall()]
        
        tablas_requeridas = ['maestro', 'Localizacion']
        tablas_faltantes = [t for t in tablas_requeridas if t not in tablas]
        
        if tablas_faltantes:
            print(f"   ⚠️  Tablas faltantes: {', '.join(tablas_faltantes)}")
            print(f"   Tablas encontradas: {', '.join(tablas)}")
            conn.close()
            return False
        
        # Verificar que hay datos
        cursor.execute("SELECT COUNT(*) FROM maestro")
        count_maestro = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Localizacion")
        count_localizacion = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"   ✅ Base de datos encontrada: {db_path}")
        print(f"   ✅ Tabla 'maestro': {count_maestro:,} registros")
        print(f"   ✅ Tabla 'Localizacion': {count_localizacion:,} registros")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error al verificar base de datos: {str(e)}")
        return False


def generar_datos_ejemplo():
    """Genera datos de ejemplo para testing"""
    print("\n📊 ¿Deseas generar datos de ejemplo para testing?")
    respuesta = input("   (s/N): ").lower()
    
    if respuesta != 's':
        return True
    
    try:
        import sqlite3
        import pandas as pd
        from datetime import datetime
        
        db_path = Path('data') / 'Maestro_ejemplo.db'
        
        # Crear base de datos de ejemplo
        conn = sqlite3.connect(db_path)
        
        # Datos de ejemplo para tabla maestro
        maestro_data = {
            'ccosto': ['CC001', 'CC001', 'CC002', 'CC002', 'CC003'] * 4,
            'nom_oficio': ['Vendedor'] * 20,
            'oficio': ['VEND01'] * 20,
            'empleado': [f'EMP{i:03d}' for i in range(1, 21)],
            'mes': ['ENERO'] * 20,
            'año': [2026] * 20,
            'estado': ['Activo'] * 20
        }
        df_maestro = pd.DataFrame(maestro_data)
        df_maestro.to_sql('maestro', conn, if_exists='replace', index=False)
        
        # Datos de ejemplo para tabla Localizacion
        localizacion_data = {
            'centro_de_costo': ['CC001', 'CC002', 'CC003'],
            'almacen': ['Tienda Centro', 'Tienda Norte', 'Tienda Sur'],
            'gestor': ['Gestor A', 'Gestor B', 'Gestor A'],
            'tipo_tienda': ['Premium', 'Standard', 'Premium'],
            'zona': ['Centro', 'Norte', 'Sur'],
            'latitud': [4.6097, 4.6200, 4.5900],
            'logitud': [-74.0817, -74.0650, -74.0900]
        }
        df_loc = pd.DataFrame(localizacion_data)
        df_loc.to_sql('Localizacion', conn, if_exists='replace', index=False)
        
        conn.close()
        
        print(f"\n   ✅ Base de datos de ejemplo creada: {db_path}")
        print("   Puedes usar esta base de datos para testing modificando la ruta en .env")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error al generar datos de ejemplo: {str(e)}")
        return False


def mostrar_siguiente_pasos():
    """Muestra los siguientes pasos a seguir"""
    print_header("✅ CONFIGURACIÓN COMPLETADA")
    
    print("Siguientes pasos:")
    print()
    print("1. 📝 Revisa el archivo .env y ajusta las rutas si es necesario")
    print()
    print("2. 📁 Coloca tu base de datos Maestro.db en la carpeta 'data/'")
    print("   (o en la ruta especificada en .env)")
    print()
    print("3. 🗺️  (Opcional) Coloca archivos .geojson o .shp en la carpeta 'geodata/'")
    print()
    print("4. 🚀 Ejecuta el dashboard:")
    print("   streamlit run dashboard_obeya_2026_pro.py")
    print()
    print("5. 🌐 Abre tu navegador en:")
    print("   http://localhost:8501")
    print()
    print("📚 Para más información, consulta el archivo README.md")
    print()


def main():
    """Función principal"""
    print_header("INICIALIZACIÓN DEL DASHBOARD OBEYA 2026")
    
    # Lista de verificaciones
    checks = [
        ("Versión de Python", verificar_python),
        ("Dependencias", verificar_dependencias),
        ("Estructura de directorios", crear_estructura_directorios),
        ("Archivo de configuración", crear_archivo_env),
        ("Base de datos", verificar_base_datos)
    ]
    
    resultados = []
    
    for nombre, funcion in checks:
        try:
            resultado = funcion()
            resultados.append((nombre, resultado))
        except Exception as e:
            print(f"\n❌ Error en {nombre}: {str(e)}")
            resultados.append((nombre, False))
    
    # Opcional: generar datos de ejemplo
    generar_datos_ejemplo()
    
    # Mostrar resumen
    print_header("RESUMEN DE CONFIGURACIÓN")
    
    for nombre, resultado in resultados:
        icono = "✅" if resultado else "❌"
        estado = "OK" if resultado else "ERROR"
        print(f"{icono} {nombre}: {estado}")
    
    # Verificar si todo está OK
    todos_ok = all(resultado for _, resultado in resultados)
    
    if todos_ok:
        mostrar_siguiente_pasos()
    else:
        print("\n⚠️  Algunos pasos fallaron. Por favor, revisa los mensajes de error arriba.")
        print("   Puedes ejecutar este script nuevamente después de corregir los problemas.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {str(e)}")
        sys.exit(1)
