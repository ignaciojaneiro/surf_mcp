# Surf MCP Server

MCP Server para consultar condiciones de surf usando la Windy Point Forecast API.

## Características

- **3 Tools MCP disponibles**:
  - `find_beaches`: Buscar playas por ciudad
  - `get_surf_conditions_by_beach`: Obtener forecast por nombre de playa
  - `get_surf_conditions`: Obtener forecast por coordenadas
- **Búsqueda inteligente**: Geocoding usando OpenStreetMap para encontrar playas
- **Datos normalizados**: Altura de olas, período, dirección, swell, viento
- **Análisis de viento**: Clasificación automática offshore/onshore/cross
- **Indicadores de calidad**: Evaluación de condiciones surfeables
- **Clean Architecture**: Separación clara de responsabilidades por capas
- **Listo para producción**: Docker + Railway deployment

## Instalación

### Requisitos

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recomendado) o pip
- API Key de [Windy Point Forecast](https://api.windy.com/keys)

### Setup Local

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/surf-mcp.git
cd surf-mcp

# Crear entorno virtual e instalar dependencias
uv venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

uv pip install -e .

# Configurar variables de entorno
cp .env.example .env
# Editar .env y agregar tu WINDY_API_KEY
```

### Configuración

Variables de entorno requeridas:

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `WINDY_API_KEY` | API Key de Windy Point Forecast | Sí |
| `PORT` | Puerto del servidor (default: 8000) | No |
| `MCP_TRANSPORT` | Transporte: `http` o `stdio` | No |
| `LOG_LEVEL` | Nivel de logs: INFO, DEBUG, etc. | No |

## Uso

### Iniciar servidor HTTP (producción)

```bash
python -m app.server
```

El servidor estará disponible en `http://localhost:8000/mcp`

### Iniciar con STDIO (desarrollo local)

```bash
MCP_TRANSPORT=stdio python -m app.server
```

### Configurar en Cursor

Agregar a `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "surf-conditions": {
      "command": "python",
      "args": ["-m", "app.server"],
      "cwd": "/ruta/a/surf-mcp",
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

La API key de Windy se lee automáticamente desde el archivo `.env` del proyecto (o variables de entorno del sistema). No es necesario pasarla en la configuración de Cursor.

## Flujo de Trabajo Típico

1. **Descubrir playas**: Usa `find_beaches` para ver qué playas hay en una ciudad
2. **Consultar forecast**: Usa `get_surf_conditions_by_beach` con el nombre de la playa elegida
3. **Análisis avanzado**: Si necesitas, usa `get_surf_conditions` directamente con coordenadas específicas

### Ejemplos de uso

#### 1. Buscar playas en una ciudad

```python
# Buscar todas las playas en Mar del Plata
find_beaches(city="Mar del Plata", country="Argentina")
```

Respuesta:

```json
{
  "beaches": [
    {
      "name": "La Maquinita Surf Beach",
      "display_name": "La Maquinita Surf Beach, Mar del Plata, Argentina",
      "lat": -38.1000,
      "lon": -57.5457,
      "city": "Mar del Plata",
      "country": "Argentina"
    },
    {
      "name": "Playa Grande",
      "display_name": "Playa Grande, Mar del Plata, Argentina",
      "lat": -38.0120,
      "lon": -57.5350,
      "city": "Mar del Plata",
      "country": "Argentina"
    }
  ],
  "count": 8
}
```

#### 2. Obtener condiciones por nombre de playa

```python
# Consultar condiciones en Playa Grande
get_surf_conditions_by_beach(
    beach_name="Playa Grande",
    city="Mar del Plata",
    hours_ahead=48
)
```

Respuesta:

```json
{
  "beach": {
    "name": "Playa Grande",
    "display_name": "Playa Grande, Mar del Plata, Argentina",
    "lat": -38.0120,
    "lon": -57.5350,
    "city": "Mar del Plata",
    "country": "Argentina"
  },
  "location": {"lat": -38.0120, "lon": -57.5350},
  "forecasts": [ /* ... */ ],
  "metadata": { /* ... */ }
}
```

#### 3. Obtener condiciones por coordenadas

```python
# Consultar condiciones directamente con coordenadas
get_surf_conditions(lat=-38.0055, lon=-57.5426, hours_ahead=48)
```

Respuesta:

```json
{
  "location": {"lat": -38.0055, "lon": -57.5426},
  "forecasts": [
    {
      "timestamp": "2026-01-29T12:00:00+00:00",
      "wave_height_m": 1.8,
      "wave_period_s": 12.5,
      "wave_direction_deg": 285,
      "swell_height_m": 1.5,
      "swell_period_s": 14.0,
      "swell_direction_deg": 270,
      "wind_speed_ms": 3.2,
      "wind_direction_deg": 45,
      "wind_type": "offshore",
      "quality_indicators": {
        "is_offshore": true,
        "good_period": true,
        "surfable": true
      }
    }
  ],
  "metadata": {
    "model": "gfsWave",
    "generated_at": "2026-01-29T10:00:00+00:00"
  }
}
```

## Estructura del Proyecto

```
app/
├── server.py                    # Entry point MCP
├── application/
│   ├── use_cases/
│   │   └── get_surf_conditions.py   # Orquestación
│   └── services/
│       └── surf_analyzer.py         # Reglas de negocio
├── repository/
│   ├── windy_repository.py      # Acceso a Windy API
│   └── geocoding_repository.py  # Geocoding con OpenStreetMap
├── resources/
│   ├── config.py                # Configuración
│   └── http_client.py           # Cliente HTTP
├── tools/
│   └── surf_tools.py            # Definición MCP tools
└── prompts/
    └── surf_interpretation.md   # Guía de interpretación
```

## Deploy en Railway

### 1. Crear proyecto en Railway

```bash
# Instalar Railway CLI
npm install -g @railway/cli

# Login
railway login

# Crear proyecto
railway init
```

### 2. Configurar variables de entorno

En Railway Dashboard, agregar:

- `WINDY_API_KEY`: Tu API key de Windy (como secret)

### 3. Deploy

```bash
railway up
```

O conectar con GitHub para auto-deploy.

### Health Check

El servidor expone `/health` para monitoreo:

```bash
curl https://tu-app.railway.app/health
```

## Interpretación de Datos

### Tipo de Viento

| Tipo | Descripción | Calidad |
|------|-------------|---------|
| `offshore` | Viento de tierra al mar | Excelente |
| `cross` | Viento lateral | Aceptable |
| `onshore` | Viento del mar a tierra | Pobre |

### Indicadores de Calidad

- **is_offshore**: `true` si el viento es offshore
- **good_period**: `true` si período >= 10s (ground swell)
- **surfable**: `true` si altura >= 0.5m y período >= 8s

### Escala de Olas

| Altura | Categoría |
|--------|-----------|
| 0 - 0.5m | Plano |
| 0.5 - 1m | Pequeño |
| 1 - 2m | Medio |
| 2 - 3m | Grande |
| 3m+ | Muy grande |

## Ejemplo Completo de Uso

Flujo típico de un surfista buscando condiciones:

```python
# Paso 1: Descubrir playas en la ciudad
beaches = find_beaches("Mar del Plata", "Argentina")
# Resultado: Lista de 8 playas con coordenadas

# Paso 2: Ver condiciones para una playa específica
forecast = get_surf_conditions_by_beach(
    beach_name="La Maquinita Surf Beach",
    city="Mar del Plata",
    hours_ahead=96  # 4 días
)

# Paso 3: Analizar el forecast
for f in forecast["forecasts"]:
    if f["quality_indicators"]["surfable"] and f["quality_indicators"]["is_offshore"]:
        print(f"Buenas condiciones: {f['timestamp']}")
        print(f"  - Olas: {f['wave_height_m']}m @ {f['wave_period_s']}s")
        print(f"  - Viento: {f['wind_speed_ms']}m/s {f['wind_type']}")
```

## Limitaciones

- **Cobertura GFS Wave**: No disponible para Hudson Bay, Mar Negro, Mar Caspio y Océano Ártico
- **Rate limits**: Según tu plan de Windy API
- **Forecast máximo**: 384 horas (16 días)
- **Geocoding**: Depende de la calidad de datos en OpenStreetMap
  - Playas populares suelen tener buena cobertura
  - Spots remotos pueden no estar en la base de datos

## Desarrollo

### Instalar dependencias de desarrollo

```bash
uv pip install -e ".[dev]"
```

### Ejecutar tests

```bash
pytest
```

### Linting

```bash
ruff check .
ruff format .
```

## Integración con Telegram (Moltbot)

Este servidor MCP puede integrarse con Telegram usando Moltbot para crear un asistente de surf interactivo.

### Arquitectura

```
Usuario → Telegram → Moltbot → Surf MCP Server → Windy API
```

### Configuración

Ver la carpeta `../moltbot/` para la configuración completa de Moltbot con Telegram:

- `moltbot/README.md` - Guía principal de configuración
- `moltbot/docs/TELEGRAM_SETUP.md` - Configuración de Telegram Bot
- `moltbot/docs/RAILWAY_DEPLOY.md` - Despliegue en Railway
- `moltbot/skills/surf-conditions/SKILL.md` - Skill de surf para Moltbot

### Deploy Rápido

1. **Surf MCP Server**: Ya configurado en esta carpeta, despliega a Railway
2. **Moltbot**: Usa el [template oficial](https://railway.com/deploy/moltbot-railway-template)
3. **Telegram Bot**: Crea uno con [@BotFather](https://t.me/BotFather)
4. **Conectar**: Configura `SURF_MCP_URL` en Moltbot apuntando a este servidor

### Ejemplo de Uso en Telegram

```
Usuario: Cómo están las olas en Mar del Plata?

Bot: 🏄 Condiciones en La Maquinita, Mar del Plata:
     🌊 Altura: 1.5m @ 11s
     💨 Viento: offshore 🟢
     📊 Calidad: Excelente
```

## Licencia

MIT
