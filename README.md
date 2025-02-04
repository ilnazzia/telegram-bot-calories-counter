# Fitness Tracking Telegram Bot

A Telegram bot that helps users track their daily water intake, calories, and physical activities. The bot provides personalized recommendations based on user parameters and environmental conditions.

## Features

- 👤 User Profile Management
  - Weight, height, age, and activity level tracking
  - Gender-specific calculations
  - Location-based adjustments

- 💧 Water Intake Tracking
  - Personalized daily water norm calculation
  - Temperature-based adjustments
  - Daily logging and progress monitoring

- 🍎 Calorie Management
  - Daily calorie norm calculation using Mifflin-St Jeor formula
  - Food calorie tracking using Nutritionix API
  - Workout calorie burn tracking

- 📊 Progress Visualization
  - 7-day progress charts for water intake
  - Calorie balance visualization
  - Daily and weekly statistics

## Commands

- `/start` - Initialize the bot
- `/help` - Display help information
- `/set_profile` - Set up or update user profile
- `/log_water <amount>` - Log water intake in milliliters
- `/log_food <food_name>` - Log food consumption
- `/log_workout <activity> <duration>` - Log physical activity
- `/check_progress` - View progress charts and statistics

# Docker Deployment

1. Build the Docker image:
```bash
bash
docker build -t fitness-bot .
```
2. Run the container:
```bash
docker run -d --env-file .env fitness-bot
```

## API Dependencies

- Telegram Bot API
- OpenWeatherMap API - for temperature data
- Nutritionix API - for food calorie data
- API Ninjas - for activity calorie calculations

## Technical Details

- Built with Python 3.12
- Uses aiogram 3.x for Telegram bot functionality
- Implements FSM (Finite State Machine) for conversation flow
- Utilizes matplotlib for data visualization
- Includes logging middleware for monitoring