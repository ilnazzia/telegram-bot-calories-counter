import asyncio
import logging

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN
from utils import get_temperature

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

users = {}


class SetProfile(StatesGroup):
    weight = State()
    height = State()
    age = State()
    sex = State()
    city = State()
    activity_level = State()


def calculate_water_norm(
    weight: float, activity_minutes: int, temperature: float
) -> int:
    """Calculate daily water intake norm in ml."""
    base_norm = weight * 30  # Base water norm

    # Add water for activity
    activity_addition = (activity_minutes // 30) * 200

    # Add water for hot weather
    weather_addition = 500 if temperature > 25 else 0

    return int(base_norm + activity_addition + weather_addition)


def calculate_calorie_norm(weight: float, height: float, age: int, sex: str) -> int:
    """Calculate daily calorie norm."""
    calories = 10 * weight + 6.25 * height - 5 * age

    # Adjust for sex
    if sex == "male":
        calories += 50
    else:
        calories -= 161

    return int(calories)


@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.full_name}!\n"
        "Я бот, который проверяет текущий курс валют. Поддерживается два режима:\n"
        "1. В сценарии /convert : введите базовую валюту, "
        "потом валюту, в которую вы хотите сконвертировать;\n"
        "2. Введите запрос в формате 'USD to RUB.'\n"
        "Популярные валюты и конвертации представлены в виде кнопок.\n"
    )


@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "Привет! Я бот, который проверяет текущий курс валют. Поддерживается два режима:\n"
        "1. В сценарии /convert : введите базовую валюту, потом валюту, "
        "в которую вы хотите сконвертировать;\n"
        "2. Введите запрос в формате 'USD to RUB.'\n"
        "Популярные валюты и конвертации представлены в виде кнопок.\n"
        "/start - Начать работу\n"
        "/help - Помощь"
    )


@dp.message(Command("set_profile"))
async def start_set_profile(message: types.Message, state: FSMContext):
    """Начало настройки профиля через FSM."""
    await state.set_state(SetProfile.weight)
    await message.answer(
        "Давайте заполним данные вашего профиля.\nВведите ваш вес (в кг)"
    )


@dp.message(SetProfile.weight)
async def set_user_weight(message: types.Message, state: FSMContext):
    """Задать вес."""
    await state.update_data(user_weight=message.text)
    await state.set_state(SetProfile.height)
    await message.answer("Введите ваш рост (в см)")


@dp.message(SetProfile.height)
async def set_user_height(message: types.Message, state: FSMContext):
    """Задать рост."""
    await state.update_data(user_height=message.text)
    await state.set_state(SetProfile.age)
    await message.answer("Введите ваш возраст")


@dp.message(SetProfile.age)
async def set_user_age(message: types.Message, state: FSMContext):
    """Задать возраст."""
    await state.update_data(user_age=message.text)
    await state.set_state(SetProfile.sex)

    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="Мужчина", callback_data="sex_male"),
        types.InlineKeyboardButton(text="Женщина", callback_data="sex_female"),
    )

    await message.answer("Выберите ваш пол:", reply_markup=builder.as_markup())


@dp.message(SetProfile.sex)
@dp.callback_query(F.data.startswith("sex_"))
async def set_user_sex(callback: types.CallbackQuery, state: FSMContext):
    """Задать пол."""
    await state.update_data(user_sex=callback.data.split("_")[1])
    await state.set_state(SetProfile.city)
    await callback.message.answer("В каком городе вы находитесь?")


@dp.message(SetProfile.city)
async def set_user_city(message: types.Message, state: FSMContext):
    """Задать город."""
    await state.update_data(user_city=message.text)
    await state.set_state(SetProfile.activity_level)
    await message.answer("Сколько минут активности у вас в день?")


@dp.message(SetProfile.activity_level)
async def set_user_acitivity_level(message: types.Message, state: FSMContext):
    """Задать уровень активности."""

    await state.update_data(user_acitivity_level=message.text)
    data = await state.get_data()
    await state.clear()
    
    # Convert string values to numbers
    weight = float(data["user_weight"])
    height = float(data["user_height"])
    age = int(data["user_age"])
    activity = int(data["user_acitivity_level"])

    # Get temperature for user's city
    temperature = await get_temperature(data["user_city"])

    # Calculate norms
    water_norm = calculate_water_norm(weight, activity, temperature)
    calorie_norm = calculate_calorie_norm(weight, height, age, data["user_sex"])

    # Save user data
    users[message.from_user.id] = {
        "weight": weight,
        "height": height,
        "age": age,
        "activity": activity,
        "city": data["user_city"],
        "water_goal": water_norm,
        "calorie_goal": calorie_norm,
        "logged_water": 0,
        "logged_calories": 0,
        "burned_calories": 0,
    }

    await message.answer(
        "Ваш профиль успешно заполнен!\n"
        f"Температура в вашем городе {temperature} градусов\n"
        f"Рекомендуемая норма воды - {water_norm} мл\n"
        f"Рекомендуемая норма калорий - {calorie_norm} ккал"
    )


@dp.message(Command("log_water"))
async def log_water_command(message: types.Message, command: CommandObject):
    """Запись количества выпитой воды"""
    if command.args is None:
        await message.answer("Ошибка: не переданы аргументы")
        return
    try:
        water_amount = command.args
    except ValueError:
        await message.answer(
            "Ошибка: неправильный формат команды. Пример:\n/log_water <объём воды>"
        )
        return
    await message.answer(f"Записано!\nВыпито {water_amount} мл воды")


@dp.message(Command("log_workout"))
async def log_workout_command(message: types.Message, command: CommandObject):
    """Запись тренировки"""
    if command.args is None:
        await message.answer("Ошибка: не переданы аргументы")
        return
    try:
        water_amount = command.args
    except ValueError:
        await message.answer(
            "Ошибка: неправильный формат команды. Пример:\n/log_water <объём воды>"
        )
        return
    await message.answer(f"Записано!\nВыпито {water_amount} мл воды")


async def main():
    await dp.start_polling(bot)
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
