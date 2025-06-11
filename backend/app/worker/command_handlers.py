"""Command handlers for the Telegram bot that manage user interactions and bot commands."""

import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.schemas.user import UserCreate
from app.core.dependencies import container
from app.services.user_service import UserService
from app.worker.bot_states import StateManager

router = Router()
state_manager = StateManager()
logger = logging.getLogger(__name__)

#######################
# INTERNAL FUNCTIONS  #
#######################


#######################
# EXTERNAL FUNCTIONS  #
#######################


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
):
    """Handles the /start command and initializes the bot for a user."""
    try:
        # Get user service from container
        user_service: UserService = container.resolve(UserService)

        # Check if user exists
        user = await user_service.get_user_by_telegram_id(message.from_user.id)

        if not user:
            # Create new user
            user_data = UserCreate(
                telegram_id=message.from_user.id,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                username=message.from_user.username,
            )
            user = await user_service.create_user(user_data)
            await message.answer("Welcome! Your account has been created.")
        else:
            await message.answer("Welcome back!")

    except Exception as e:
        logger.error(f"Error in cmd_start: {e}")
        await message.answer("Sorry, something went wrong. Please try again later.")
