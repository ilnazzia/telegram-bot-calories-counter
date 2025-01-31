import os
import logging

from dotenv import load_dotenv

logging.basicConfig(level=logging.DEBUG)

aiohttp_logger = logging.getLogger("aiohttp")
aiohttp_logger.setLevel(logging.DEBUG)

# Загрузка переменных из .env файла
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPEN_WEATHER_API_TOKEN = os.getenv("OPEN_WEATHER_API_TOKEN")
OPEN_WEATHER_API_URL= "https://api.openweathermap.org/data/2.5/weather"

if not BOT_TOKEN or not OPEN_WEATHER_API_TOKEN:
    raise NameError