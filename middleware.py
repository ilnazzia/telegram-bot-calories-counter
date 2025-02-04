from typing import Any, Awaitable, Callable

from aiogram import types

from utils import setup_logger

logger = setup_logger(__name__)


class LoggingMiddleware:
    async def __call__(
        self,
        handler: Callable[[types.Message, dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: dict[str, Any],
    ) -> Any:
        if event.text and event.text.startswith("/"):
            user = event.from_user
            logger.info(f"User {user.id} ({user.username}) sent command: {event.text}")

        return await handler(event, data)
