import time
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
import httpx

# --- Configuration & Constants ---
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("WeatherAPI")

OPEN_METEO_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_TTL_SECONDS = 600  # 10 minutes
RATE_LIMIT_MAX_REQUESTS = 10
RATE_LIMIT_WINDOW = 60  # 1 minute
HTTP_TIMEOUT = 5.0  # 5 seconds

# --- WMO Weather Code Interpretation ---
# Derived from Open-Meteo docs
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Drizzle: Light", 53: "Drizzle: Moderate", 55: "Drizzle: Dense",
    61: "Rain: Slight", 63: "Rain: Moderate", 65: "Rain: Heavy",
    71: "Snow: Slight", 73: "Snow: Moderate", 75: "Snow: Heavy",
    77: "Snow grains",
    80: "Rain showers: Slight", 81: "Rain showers: Moderate", 82: "Rain showers: Violent",
    95: "Thunderstorm: Slight or Moderate",
    96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
}

def get_weather_desc(code: int) -> str:
    return WMO_CODES.get(code, "Unknown")

# --- In-Memory Caching System ---
class WeatherCache:
    def __init__(self):
        self.store: Dict[str, Dict[str, Any]] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Dict]:
        entry = self.store.get(key)
        if not entry:
            self.misses += 1
            return None

        if time.time() > entry['expiry']:
            logger.info(f"Cache expired for {key}")
            del self.store[key]
            self.misses += 1
            return None

        self.hits += 1
        logger.info(f"Cache HIT for {key}")
        return entry['data']

    def set(self, key: str, data: Dict):
        self.store[key] = {
            'data': data,
            'expiry': time.time() + CACHE_TTL_SECONDS
        }
        logger.info(f"Cache SET for {key}")

    def clear(self):
        self.store.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Cache manually cleared")

    def get_stats(self):
        return {
            "cache_hits": self.hits,
            "cache_misses": self.misses,
            "cached_items_count": len(self.store)
        }

weather_cache = WeatherCache()

# --- Rate Limiting Storage ---
# Map: IP -> List[timestamps]
rate_limit_store: Dict[str, List[float]] = {}

# --- Lifecycle Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize HTTP Client
    app.state.client = httpx.AsyncClient(timeout=HTTP_TIMEOUT)
    yield
    # Shutdown: Close Client
    await app.state.client.aclose()

app = FastAPI(lifespan=lifespan, title="Assignment 2 Weather API")

# --- Middleware: Rate Limiting ---
@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    client_ip = request.client.host
    current_time = time.time()

    # Initialize or clean up old requests
    if client_ip not in rate_limit_store:
        rate_limit_store[client_ip] = []

    # Filter out requests older than the window
    rate_limit_store[client_ip] = [
        t for t in rate_limit_store[client_ip]
        if t > current_time - RATE_LIMIT_WINDOW
    ]

    # Check limit
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"error": "Rate limit exceeded. Max 10 requests per minute."}
        )

    # Add current request and proceed
    rate_limit_store[client_ip].append(current_time)
    response = await call_next(request)
    return response

# --- Helper Functions ---

async def get_coordinates(client: httpx.AsyncClient, city: str):
    """Fetches Lat/Lon for a city name using Open-Meteo Geocoding."""
    try:
        response = await client.get(
            OPEN_METEO_GEO_URL,
            params={"name": city, "count": 1, "language": "en", "format": "json"}
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("results"):
            raise HTTPException(status_code=404, detail=f"City '{city}' not found.")

        return data["results"][0]
    except httpx.HTTPStatusError as e:
        logger.error(f"Geocoding API error: {str(e)}")
        raise HTTPException(status_code=503, detail="Weather service unavailable")
    except httpx.RequestError as e:
        logger.error(f"Network error during geocoding: {str(e)}")
        raise HTTPException(status_code=503, detail="Weather service unavailable")

# --- Endpoints ---

@app.get("/weather/cache-status")
async def get_cache_status():
    """Returns statistics about the internal cache."""
    return weather_cache.get_stats()

@app.delete("/weather/cache")
async def invalidate_cache():
    """Manually clears the cache."""
    weather_cache.clear()
    return {"message": "Cache invalidated successfully"}

@app.get("/weather/{city}")
async def get_current_weather(city: str, request: Request):
    """Fetches current weather for a specific city."""
    cache_key = f"current_{city.lower()}"
    cached_data = weather_cache.get(cache_key)
    if cached_data:
        return cached_data

    client: httpx.AsyncClient = request.app.state.client

    # 1. Get Coordinates
    location = await get_coordinates(client, city)
    lat, lon = location["latitude"], location["longitude"]
    city_name_resolved = location["name"]

    # 2. Get Weather Data
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "auto"
        }
        response = await client.get(OPEN_METEO_WEATHER_URL, params=params)
        response.raise_for_status()
        data = response.json()

        current = data["current"]

        # 3. Standardize Response
        result = {
            "city": city_name_resolved,
            "country": location.get("country"),
            "temperature": current["temperature_2m"],
            "unit": "Celsius",
            "humidity": current["relative_humidity_2m"],
            "wind_speed": current["wind_speed_10m"],
            "condition": get_weather_desc(current["weather_code"]),
            "timestamp": current["time"]
        }

        # 4. Cache and Return
        weather_cache.set(cache_key, result)
        return result

    except httpx.RequestError as exc:
        logger.error(f"External API connection error: {exc}")
        raise HTTPException(status_code=503, detail="Weather service unavailable (Connection Error)")
    except Exception as exc:
        logger.error(f"Unexpected error: {exc}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/weather/forecast/{city}")
async def get_weather_forecast(city: str, request: Request):
    """Fetches 5-day weather forecast."""
    cache_key = f"forecast_{city.lower()}"
    cached_data = weather_cache.get(cache_key)
    if cached_data:
        return cached_data

    client: httpx.AsyncClient = request.app.state.client

    # 1. Get Coordinates
    location = await get_coordinates(client, city)
    lat, lon = location["latitude"], location["longitude"]

    # 2. Get Forecast Data (5 days)
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_sum",
            "forecast_days": 5,
            "timezone": "auto"
        }
        response = await client.get(OPEN_METEO_WEATHER_URL, params=params)
        response.raise_for_status()
        data = response.json()

        daily = data["daily"]
        forecast_list = []

        # Process arrays into list of objects
        for i in range(len(daily["time"])):
            forecast_list.append({
                "date": daily["time"][i],
                "max_temp": daily["temperature_2m_max"][i],
                "min_temp": daily["temperature_2m_min"][i],
                "condition": get_weather_desc(daily["weather_code"][i]),
                "precipitation_mm": daily["precipitation_sum"][i]
            })

        result = {
            "city": location["name"],
            "country": location.get("country"),
            "forecast": forecast_list
        }

        weather_cache.set(cache_key, result)
        return result

    except httpx.RequestError as exc:
        logger.error(f"External API connection error: {exc}")
        raise HTTPException(status_code=503, detail="Weather service unavailable")
