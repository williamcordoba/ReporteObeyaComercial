# 📊 Dashboard Obeya Comercial 2026

Dashboard interactivo de análisis estratégico de dotación y cobertura geográfica diseñado para la gestión comercial.

## 🎯 Características Principales

### ✨ Funcionalidades
- **Visualización Geográfica**: Mapas interactivos con soporte para archivos .geojson y .shp
- **KPIs en Tiempo Real**: Métricas clave de desempeño actualizadas dinámicamente
- **Análisis Multi-dimensional**: Filtros por zona, gestor, tipo de tienda y período
- **Top Performers**: Identificación de tiendas con mejor desempeño
- **Exportación de Datos**: Descarga de reportes en formato CSV
- **Diseño Responsive**: Adaptable a diferentes dispositivos

### 🎨 Diseño Gerencial
- Paleta de colores corporativa profesional
- Tipografía moderna y legible (Roboto)
- Visualizaciones interactivas con Plotly
- Mapas personalizables con capas geográficas
- Interfaz intuitiva con navegación por tabs

## 📋 Requisitos Previos

### Software Necesario
- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Base de datos SQLite con las tablas requeridas
- (Opcional) Archivos geográficos .geojson o .shp para capas adicionales

### Estructura de la Base de Datos
El dashboard espera las siguientes tablas en la base de datos:

**Tabla `maestro`:**
- ccosto
- nom_oficio
- oficio
- empleado
- mes
- año
- estado

**Tabla `Localizacion`:**
- centro_de_costo
- almacen
- gestor
- tipo_tienda
- zona
- latitud
- logitud (longitud)

## 🚀 Instalación y Configuración

### 1. Clonar o Descargar el Proyecto

```bash
# Crear directorio del proyecto
mkdir dashboard-obeya-2026
cd dashboard-obeya-2026

# Copiar los archivos del dashboard
```

### 2. Crear Entorno Virtual (Recomendado)

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

**Opción A: Archivo .env (Recomendado para desarrollo)**

```bash
# Copiar el template
cp .env.template .env

# Editar .env con tus rutas
DATABASE_PATH=C:\ruta\a\tu\Maestro.db
GEODATA_PATH=C:\ruta\a\tus\archivos\geograficos
```

**Opción B: Modificar directamente el código (No recomendado)**

Editar las líneas 36-45 en `dashboard_obeya_2026_pro.py` con tus rutas.

### 5. Preparar Archivos Geográficos (Opcional)

Si tienes archivos .shp o .geojson:

```bash
# Crear carpeta para geodatos
mkdir geodata

# Copiar tus archivos .geojson o .shp
cp /ruta/a/tus/archivos/*.geojson geodata/
# O
cp /ruta/a/tus/archivos/*.shp geodata/
# Si usas .shp, copia también los archivos asociados (.dbf, .shx, .prj)
```

## ▶️ Ejecutar el Dashboard

### Modo Desarrollo (Local)

```bash
streamlit run dashboard_obeya_2026_pro.py
```

El dashboard se abrirá automáticamente en tu navegador en `http://localhost:8501`

### Modo Producción

```bash
streamlit run dashboard_obeya_2026_pro.py --server.port 8501 --server.address 0.0.0.0
```

## 🌐 Despliegue en Producción

### Opción 1: Streamlit Cloud (Recomendado - Gratis)

1. **Crear cuenta en [Streamlit Cloud](https://streamlit.io/cloud)**

2. **Preparar repositorio Git:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <tu-repo-url>
   git push -u origin main
   ```

3. **Configurar en Streamlit Cloud:**
   - Conectar tu repositorio
   - Seleccionar el archivo principal: `dashboard_obeya_2026_pro.py`
   - Configurar secrets en el dashboard:
     ```toml
     DATABASE_PATH = "/app/data/Maestro.db"
     GEODATA_PATH = "/app/geodata"
     ```

4. **Subir archivos adicionales:**
   - Base de datos → carpeta `data/`
   - Archivos geográficos → carpeta `geodata/`

5. **Deploy**

### Opción 2: Servidor Propio (Ubuntu/Linux)

**1. Instalar dependencias del sistema:**
```bash
sudo apt update
sudo apt install python3-pip python3-venv
sudo apt install libgdal-dev libgeos-dev libproj-dev  # Para geopandas
```

**2. Configurar la aplicación:**
```bash
# Crear directorio
mkdir -p /opt/dashboard-obeya
cd /opt/dashboard-obeya

# Copiar archivos
# ...

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**3. Crear servicio systemd:**
```bash
sudo nano /etc/systemd/system/dashboard-obeya.service
```

Contenido del archivo:
```ini
[Unit]
Description=Dashboard Obeya Comercial 2026
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/dashboard-obeya
Environment="PATH=/opt/dashboard-obeya/venv/bin"
ExecStart=/opt/dashboard-obeya/venv/bin/streamlit run dashboard_obeya_2026_pro.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

**4. Activar y ejecutar:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable dashboard-obeya
sudo systemctl start dashboard-obeya
sudo systemctl status dashboard-obeya
```

**5. Configurar Nginx (opcional, para proxy reverso):**
```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### Opción 3: Docker

**1. Crear Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicación
COPY . .

# Exponer puerto
EXPOSE 8501

# Comando de inicio
CMD ["streamlit", "run", "dashboard_obeya_2026_pro.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**2. Crear docker-compose.yml:**
```yaml
version: '3.8'

services:
  dashboard:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
      - ./geodata:/app/geodata
    environment:
      - DATABASE_PATH=/app/data/Maestro.db
      - GEODATA_PATH=/app/geodata
    restart: unless-stopped
```

**3. Ejecutar:**
```bash
docker-compose up -d
```

## 📊 Uso del Dashboard

### Panel de Control (Sidebar)
1. **Seleccionar período**: Mes y año a analizar
2. **Aplicar filtros**: Zona, gestor, tipo de tienda
3. **Ajustar rango**: Cantidad mínima/máxima de activos
4. **Exportar datos**: Descargar CSV con datos filtrados

### Pestañas Principales

**🗺️ Vista Geográfica**
- Mapa interactivo con todas las ubicaciones
- Configuración de tamaño y escala de marcadores
- Opción para superponer capas geográficas (.geojson/.shp)
- Click en marcadores para ver detalles

**📈 Análisis por Zona**
- Gráfico de barras: Distribución por zona
- Gráfico circular: Distribución por tipo de tienda
- Análisis comparativo por gestor y zona

**🏆 Top Performers**
- Top 15 tiendas con mayor dotación
- Estadísticas clave (mínimo, mediana, promedio, máximo)
- Histograma de distribución

### Tabla de Datos
- Selección de columnas a mostrar
- Paginación configurable
- Ordenamiento por cualquier columna
- Búsqueda y filtrado

## 🎨 Personalización

### Cambiar Colores Corporativos

Editar el diccionario `COLORS` en el código (líneas 27-38):

```python
COLORS = {
    'primary': '#TU_COLOR_AQUI',      # Color principal
    'secondary': '#TU_COLOR_AQUI',    # Color secundario
    # ... etc
}
```

### Ajustar Paleta de Gráficos

Modificar `CHART_COLORS` (línea 41):

```python
CHART_COLORS = ['#color1', '#color2', '#color3', '#color4', '#color5', '#color6']
```

### Modificar Query de Datos

Si tu estructura de base de datos es diferente, ajusta la query SQL en la función `load_data()` (líneas 258-301).

## 🔧 Solución de Problemas

### Error: "No se pudieron cargar datos"
- Verificar que la ruta de la base de datos sea correcta
- Confirmar que las tablas `maestro` y `Localizacion` existen
- Verificar que haya datos para el período seleccionado

### Error: "No hay coordenadas válidas"
- Verificar que los campos `latitud` y `longitud` contengan valores numéricos
- Confirmar que no estén vacíos
- Revisar el formato (deben ser decimales, ej: 4.6097, -74.0817)

### Error al cargar archivos geográficos
- Verificar que la ruta `GEODATA_PATH` exista
- Para archivos .shp, incluir todos los archivos asociados (.dbf, .shx, .prj)
- Verificar que el sistema de coordenadas sea compatible

### Performance lento
- Reducir el TTL del caché (línea 265)
- Limitar la cantidad de datos cargados
- Optimizar las queries SQL
- Considerar usar base de datos PostgreSQL en lugar de SQLite para grandes volúmenes

## 📝 Mantenimiento

### Actualizar Datos
El dashboard usa caché de 5 minutos (300 segundos). Para forzar actualización:
- Cambiar cualquier filtro
- Refrescar la página completa (F5)
- Modificar el período

### Backup
```bash
# Backup de base de datos
cp /ruta/Maestro.db /ruta/backup/Maestro_$(date +%Y%m%d).db

# Backup de configuración
tar -czf config_backup.tar.gz .env .streamlit/
```

## 📈 Métricas y Monitoreo

Para ambiente de producción, considerar:
- Logs de acceso (Streamlit genera logs automáticamente)
- Monitoreo de uso de recursos (CPU, RAM)
- Alertas por caídas del servicio
- Google Analytics o similar para estadísticas de uso

## 🤝 Soporte

Para reportar problemas o sugerencias:
1. Crear un issue en el repositorio
2. Contactar al equipo de desarrollo
3. Revisar la documentación de [Streamlit](https://docs.streamlit.io)

## 📄 Licencia

[Especificar licencia según corresponda]

## 🔄 Changelog

### Versión 2.0 (2026)
- ✨ Diseño gerencial profesional
- 🗺️ Soporte para archivos .geojson y .shp
- 📊 Nuevas visualizaciones interactivas
- 🎨 Paleta de colores corporativa
- ⚡ Optimizaciones de performance
- 🌐 Configuración para producción

### Versión 1.0 (Original)
- 📊 Dashboard básico con métricas
- 🗺️ Mapa simple con folium
- 📈 Gráficos básicos

---

**Desarrollado para análisis comercial estratégico** | © 2026
