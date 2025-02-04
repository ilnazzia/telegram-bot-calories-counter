import asyncio
from datetime import date

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN
from middleware import LoggingMiddleware
from utils import (
    calculate_calorie_norm,
    calculate_water_norm,
    create_calories_progress_chart,
    create_water_progress_chart,
    get_activity_calories,
    get_food_calories,
    get_temperature,
    setup_logger,
)

logger = setup_logger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.message.middleware(LoggingMiddleware())

users = {}


class SetProfile(StatesGroup):
    """Состояния для настройки профиля пользователя."""

    weight = State()
    height = State()
    age = State()
    sex = State()
    city = State()
    activity_level = State()


class LogFood(StatesGroup):
    """Состояния для записи приема пищи."""

    food_name = State()
    food_amount = State()


# Словарь для временного хранения данных о продуктах
food_cache = {}


@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.full_name}!\n"
        "Я бот, который проверяет текущий курс валют:\n"
        "1. В сценарии /convert : введите базовую валюту, "
        "потом валюту, в которую вы хотите сконвертировать;\n"
        "2. Введите запрос в формате 'USD to RUB.'\n"
        "Популярные валюты и конвертации представлены в виде кнопок.\n"
    )


@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "Привет! Я бот, который проверяет текущий курс валют\n"
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
async def set_user_activity_level(message: types.Message, state: FSMContext):
    """Задать уровень активности."""

    await state.update_data(user_activity_level=message.text)
    data = await state.get_data()
    await state.clear()

    # Convert string values to numbers
    weight = float(data["user_weight"])
    height = float(data["user_height"])
    age = int(data["user_age"])
    activity = int(data["user_activity_level"])

    # Get temperature for user's city
    temperature = await get_temperature(data["user_city"])

    # Calculate norms
    water_norm = calculate_water_norm(weight, activity, temperature)
    calorie_norm = calculate_calorie_norm(
        weight, height, age, activity, data["user_sex"]
    )

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


def get_today_date():
    """Get current date as string in format YYYY-MM-DD"""
    return date.today().isoformat()


def init_daily_logs(user_id: int, today: str) -> None:
    """Initialize daily logs structure for user if not exists."""
    if "daily_logs" not in users[user_id]:
        users[user_id]["daily_logs"] = {}

    if today not in users[user_id]["daily_logs"]:
        users[user_id]["daily_logs"][today] = {
            "water": 0,
            "calories_in": 0,
            "calories_burned": 0,
        }


@dp.message(Command("log_water"))
async def log_water_command(message: types.Message, command: CommandObject):
    """Запись количества выпитой воды"""
    if command.args is None:
        await message.answer("Ошибка: не переданы аргументы")
        return

    if message.from_user.id not in users:
        await message.answer("Ошибка: сначала заполните профиль с помощью /set_profile")
        return

    try:
        water_amount = int(command.args)
        today = get_today_date()

        init_daily_logs(message.from_user.id, today)
        users[message.from_user.id]["daily_logs"][today]["water"] += water_amount
        current_water = users[message.from_user.id]["daily_logs"][today]["water"]
        water_goal = users[message.from_user.id]["water_goal"]
        remaining_water = max(0, water_goal - current_water)

        await message.answer(
            f"Записано!\nВыпито {water_amount} мл воды\n"
            f"Всего за сегодня: {current_water} мл\n"
            f"Осталось выпить: {remaining_water} мл до нормы {water_goal} мл"
        )
    except ValueError:
        await message.answer(
            "Ошибка: неправильный формат команды. Пример:\n/log_water <объём воды в мл>"
        )
        return


@dp.message(Command("log_workout"))
async def log_workout_command(message: types.Message, command: CommandObject):
    """Запись тренировки"""
    if command.args is None:
        await message.answer("Ошибка: не переданы аргументы")
        return

    if (
        message.from_user.id not in users
        or users[message.from_user.id].get("weight") is None
    ):
        await message.answer("Ошибка: сначала укажите ваш вес в профиле.")
        return

    try:
        # Разделяем аргументы на тип тренировки и длительность
        workout_type, duration = command.args.rsplit(maxsplit=1)
        workout_duration = int(duration)

        user_weight = users[message.from_user.id]["weight"]
        total_calories = await get_activity_calories(
            workout_type, user_weight, workout_duration
        )
    except (ValueError, TypeError):
        await message.answer(
            "Ошибка: неправильный формат команды. Пример:\n"
            "/log_workout <тип тренировки> <длительность тренировки в минутах>"
        )
        return

    await message.answer(
        f"Записано!\nТренировка: {workout_type}\n"
        f"Длительность: {workout_duration} минут\n"
        f"Потрачено {total_calories} ккал."
    )


@dp.message(Command("log_food"))
async def log_food_command(
    message: types.Message, command: CommandObject, state: FSMContext
):
    """Начало логирования приема пищи"""
    if message.from_user.id not in users:
        await message.answer("Ошибка: сначала заполните профиль с помощью /set_profile")
        return

    if command.args:
        # Если название продукта передано сразу в команде
        food_name = command.args.lower()
        try:
            calories_per_100g = await get_food_calories(food_name)
            # Сохраняем информацию о калорийности во временный кэш
            food_cache[message.from_user.id] = {"calories": calories_per_100g}

            await state.update_data(food_name=food_name)
            await state.set_state(LogFood.food_amount)
            await message.answer(
                f"{food_name.capitalize()} — {calories_per_100g:.1f} "
                "ккал на 100 г.\n"
                "Сколько грамм вы съели?"
            )
        except Exception as e:
            await message.answer("Извините, не могу найти информацию об этом продукте.")
            await state.clear()
    else:
        await message.answer(
            "Ошибка: не указано название продукта. Пример:\n/log_food банан"
        )


@dp.message(LogFood.food_amount)
async def process_food_amount(message: types.Message, state: FSMContext):
    """Обработка указанного количества продукта"""
    try:
        amount = float(message.text)
        food_data = food_cache.get(message.from_user.id)

        if food_data:
            calories_per_100g = food_data["calories"]
            total_calories = (calories_per_100g * amount) / 100

            today = get_today_date()
            init_daily_logs(message.from_user.id, today)
            users[message.from_user.id]["daily_logs"][today]["calories_in"] += (
                total_calories
            )

            current_calories = users[message.from_user.id]["daily_logs"][today][
                "calories_in"
            ]
            calorie_goal = users[message.from_user.id]["calorie_goal"]
            remaining_calories = max(0, calorie_goal - current_calories)

            await message.answer(
                f"Записано: {total_calories:.1f} ккал\n"
                f"Всего за сегодня: {current_calories:.1f} ккал\n"
                f"Осталось: {remaining_calories:.1f} ккал до нормы"
            )

            # Очищаем временные данные
            del food_cache[message.from_user.id]
        else:
            await message.answer("Произошла ошибка. Попробуйте снова.")

    except ValueError:
        await message.answer("Пожалуйста, введите корректное число грамм")
        return
    finally:
        await state.clear()


@dp.message(Command("check_progress"))
async def check_progress_command(message: types.Message):
    """Показывает прогресс пользователя по воде и калориям"""
    if message.from_user.id not in users:
        await message.answer("Ошибка: сначала заполните профиль с помощью /set_profile")
        return

    user_data = users[message.from_user.id]

    if "daily_logs" not in user_data:
        await message.answer("У вас пока нет записей о воде и калориях")
        return

    # Получаем данные за последние 7 дней
    daily_logs = user_data["daily_logs"]
    water_goal = user_data["water_goal"]
    calorie_goal = user_data["calorie_goal"]

    # Создаем графики
    water_chart = create_water_progress_chart(daily_logs, water_goal)
    calories_chart = create_calories_progress_chart(daily_logs, calorie_goal)

    # Получаем данные за сегодня для текстового отчета
    today = get_today_date()
    today_data = daily_logs.get(
        today, {"water": 0, "calories_in": 0, "calories_burned": 0}
    )

    water_consumed = today_data["water"]
    water_remaining = max(0, water_goal - water_consumed)

    calories_consumed = today_data["calories_in"]
    calories_burned = today_data["calories_burned"]
    calories_balance = calories_consumed - calories_burned
    calories_remaining = max(0, calorie_goal - calories_balance)

    # Отправляем текстовый отчет
    await message.answer(
        "Прогресс за сегодня:\n\n"
        "Вода:\n"
        f"- Выпито: {water_consumed} мл из {water_goal} мл\n"
        f"- Осталось: {water_remaining} мл\n\n"
        "Калории:\n"
        f"- Потреблено: {calories_consumed:.1f} ккал\n"
        f"- Сожжено: {calories_burned:.1f} ккал\n"
        f"- Баланс: {calories_balance:.1f} ккал из {calorie_goal} ккал\n"
        f"- Осталось: {calories_remaining:.1f} ккал"
    )

    # Отправляем графики
    await message.answer_photo(
        BufferedInputFile(water_chart.getvalue(), filename="water.png"),
        caption="График потребления воды за последние 7 дней",
    )
    await message.answer_photo(
        BufferedInputFile(calories_chart.getvalue(), filename="calories.png"),
        caption="График баланса калорий за последние 7 дней",
    )


async def main():
    await dp.start_polling(bot)
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
