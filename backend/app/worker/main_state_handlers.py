import logging

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
)

from app.worker.bot_states import BotStates, StateManager

router = Router()

state_manager = StateManager()
logger = logging.getLogger(__name__)


@router.message(StateFilter(None))
async def handle_no_state(message: Message, state: FSMContext):
    """Обработчик сообщений, когда состояние не установлено"""
    await state.set_state(BotStates.MAIN_STATE)
    await handle_message(message)


@router.message(StateFilter(BotStates.MAIN_STATE))
async def handle_message(message: Message):
    """Handles incoming messages that don't match any other handlers."""

    try:
        await message.reply(
            "Чтобы открыть приложение, нажмите кнопку Клуб в левом нижнем углу экрана"
        )
    except TelegramAPIError as e:
        logger.error("Error processing message: %s", e)
        await message.reply("Произошла ошибка при обработке сообщения.")
        return
