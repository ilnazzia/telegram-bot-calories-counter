import os

from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Токены и URL для API
BOT_TOKEN = os.getenv("BOT_TOKEN")

OPEN_WEATHER_API_TOKEN = os.getenv("OPEN_WEATHER_API_TOKEN")
OPEN_WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"

CALORIES_API_TOKEN = os.getenv("CALORIES_API_TOKEN")
CALORIES_API_URL = "https://api.api-ninjas.com/v1/caloriesburned"

NUTRITIONIX_API_TOKEN = os.getenv("NUTRITIONIX_API_TOKEN")
NUTRITIONIX_APP_ID = os.getenv("NUTRITIONIX_APP_ID")
NUTRITIONIX_API_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"

for token in [
    BOT_TOKEN,
    OPEN_WEATHER_API_TOKEN,
    CALORIES_API_TOKEN,
    NUTRITIONIX_API_TOKEN,
]:
    if not token:
        raise NameError
