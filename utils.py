import asyncio
import aiohttp
from config import OPEN_WEATHER_API_TOKEN, OPEN_WEATHER_API_URL


async def get_temperature(city: str) -> float:
    """Get current temperature for city using weather API."""
    params = {"q": city,
              "appid": OPEN_WEATHER_API_TOKEN,
              "units": "metric",
              "lang": "ru"}
    
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        try:
            async with session.get(OPEN_WEATHER_API_URL, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    main = data.get("main", {})
                    return main.get("temp", "Нет данных")
                else:
                    print(f"Ошибка API: {response.status}, {await response.text()}")
        except aiohttp.ClientError as e:
            print(f"Ошибка клиента API: {e}")
        except asyncio.TimeoutError:
            print("Ошибка: Таймаут при запросе к API")
    return None