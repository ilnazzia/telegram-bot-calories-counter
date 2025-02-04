import asyncio
import io
from datetime import date, timedelta
import logging

import aiohttp
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from googletrans import Translator

from config import (
    CALORIES_API_TOKEN,
    CALORIES_API_URL,
    NUTRITIONIX_API_TOKEN,
    NUTRITIONIX_API_URL,
    NUTRITIONIX_APP_ID,
    OPEN_WEATHER_API_TOKEN,
    OPEN_WEATHER_API_URL,
)


def calculate_water_norm(
    weight: float, activity_minutes: int, temperature: float
) -> int:
    """Daily water intake norm.

    Args:
        weight (float): User weight in kg
        activity_minutes (int): Activity time in minutes
        temperature (float): Temperature in Celsius

    Returns:
        int: Water norm
    """
    base_norm = weight * 30  # Базовая норма воды

    # Добавляем воду за время активности
    activity_addition = (activity_minutes // 30) * 300

    # Добавляем воду из-за жаркой погоды
    weather_addition = 300 if temperature > 25 else 0

    return int(base_norm + activity_addition + weather_addition)


def calculate_calorie_norm(
    weight: float, height: float, age: int, activity: int, sex: str
) -> int:
    """Daily calorie norm.

    Args:
        weight (float): User weight in kg
        height (float): User height in cm
        age (int): User age
        sex (str): User sex

    Returns:
        int: Calorie norm
    """
    calories = 10 * weight + 6.25 * height - 5 * age + activity * 10

    if sex == "male":
        calories += 50
    else:
        calories -= 161

    return int(calories)


async def get_temperature(city: str) -> float:
    """Get current temperature for city using weather API.

    Args:
        city (str): City name

    Returns:
        float: Temperature in Celsius
    """
    params = {
        "q": city,
        "appid": OPEN_WEATHER_API_TOKEN,
        "units": "metric",
        "lang": "ru",
    }

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=False)
    ) as session:
        try:
            async with session.get(
                OPEN_WEATHER_API_URL, params=params, timeout=10
            ) as response:
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


async def translate_text(some_text: str):
    async with Translator() as translator:
        result = await translator.translate(some_text)
        return result.text


async def get_activity_calories(activity: str, weight: float, duration: int) -> float:
    """Get calories burned for activity using calories API.

    Args:
        activity (str): Activity name
        weight (float): User weight in kg
        duration (int): Activity duration in minutes

    Returns:
        float: Calories burned
    """
    headers = {
        "X-Api-Key": CALORIES_API_TOKEN,
    }
    params = {
        "activity": await translate_text(activity),
        "weight": weight * 2.20462,
        "duration": duration,
    }

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=False)
    ) as session:
        try:
            async with session.get(
                CALORIES_API_URL, params=params, headers=headers, timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data[0].get("total_calories", "Нет данных")
                else:
                    print(f"Ошибка API: {response.status}, {await response.text()}")
        except aiohttp.ClientError as e:
            print(f"Ошибка клиента API: {e}")
        except asyncio.TimeoutError:
            print("Ошибка: Таймаут при запросе к API")
    return None


async def get_food_calories(food_name: str) -> float:
    """Get calories for food item using Nutritionix API.

    Args:
        food_name (str): Name of the food item to look up

    Returns:
        float: Calories for the food item, or None if not found
    """
    headers = {
        "x-app-id": NUTRITIONIX_APP_ID,
        "x-app-key": NUTRITIONIX_API_TOKEN,
    }

    data = {
        "query": await translate_text(food_name),
    }

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=False)
    ) as session:
        try:
            async with session.post(
                NUTRITIONIX_API_URL, json=data, headers=headers, timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    foods = data.get("foods", [])
                    if foods:
                        return foods[0].get("nf_calories", "Нет данных")
                else:
                    print(f"Ошибка API: {response.status}, {await response.text()}")
        except aiohttp.ClientError as e:
            print(f"Ошибка клиента API: {e}")
        except asyncio.TimeoutError:
            print("Ошибка: Таймаут при запросе к API")
    return None


def get_last_7_days():
    """Get list of last 7 days in YYYY-MM-DD format"""
    today = date.today()
    return [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]


def create_water_progress_chart(daily_logs: dict, goal: float) -> io.BytesIO:
    """Create water progress chart for the last 7 days.

    Args:
        daily_logs (dict): Dictionary with daily water and calorie logs
        goal (float): Daily water goal

    Returns:
        io.BytesIO: Buffer containing the chart image
    """
    # Get data for last 7 days
    dates = get_last_7_days()
    values = [daily_logs.get(date, {}).get("water", 0) for date in dates]

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 6))

    # Create bar chart
    bars = ax.bar(dates, values, color="#2ecc71", alpha=0.7)

    # Add goal line
    ax.axhline(y=goal, color="#e74c3c", linestyle="--", label="Цель")

    # Customize chart
    ax.set_title("Потребление воды за последние 7 дней")
    ax.set_xlabel("Дата")
    ax.set_ylabel("мл")

    # Format x-axis
    plt.xticks(rotation=45)

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{int(height)}",
            ha="center",
            va="bottom",
        )

    # Add legend
    ax.legend()

    # Adjust layout
    plt.tight_layout()

    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()

    return buf


def create_calories_progress_chart(daily_logs: dict, goal: float) -> io.BytesIO:
    """Create calories progress chart for the last 7 days.

    Args:
        daily_logs (dict): Dictionary with daily water and calorie logs
        goal (float): Daily calorie goal

    Returns:
        io.BytesIO: Buffer containing the chart image
    """
    # Get data for last 7 days
    dates = get_last_7_days()
    calories_in = [daily_logs.get(date, {}).get("calories_in", 0) for date in dates]
    calories_burned = [
        daily_logs.get(date, {}).get("calories_burned", 0) for date in dates
    ]
    net_calories = [
        in_cal - burned for in_cal, burned in zip(calories_in, calories_burned)
    ]

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 6))

    # Create bar chart
    bars = ax.bar(
        dates,
        net_calories,
        color=["#e74c3c" if cal > goal else "#2ecc71" for cal in net_calories],
        alpha=0.7,
    )

    # Add goal line
    ax.axhline(y=goal, color="#3498db", linestyle="--", label="Лимит калорий")

    # Customize chart
    ax.set_title("Баланс калорий за последние 7 дней")
    ax.set_xlabel("Дата")
    ax.set_ylabel("ккал")

    # Format x-axis
    plt.xticks(rotation=45)

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{int(height)}",
            ha="center",
            va="bottom",
        )

    # Add legend
    ax.legend()

    # Adjust layout
    plt.tight_layout()

    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()

    return buf


def setup_logger(name: str) -> logging.Logger:
    """
    Настройка и получение логгера
    
    Args:
        name: Имя логгера
    
    Returns:
        logging.Logger: Настроенный логгер
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(name)
