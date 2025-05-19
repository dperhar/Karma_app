from aiogram.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from config import MINIAPP_URL_CHAT


class BotStates(StatesGroup):
    MAIN_STATE = State()  # Основное состояние бота
    INVITE_STATE = State()  # Состояние приглашения
    REGISTRATION_FIRST_NAME_STATE = State()  # Состояние ввода имени при регистрации
    REGISTRATION_LAST_NAME_STATE = State()  # Состояние ввода фамилии при регистрации
    WAITING_PHONE_STATE = State()  # Состояние ввода телефона при регистрации
    REGISTRATION_PHONE_STATE = State()  # Состояние ввода телефона при регистрации


class StateManager:
    def __init__(self):
        self.menus = {
            BotStates.MAIN_STATE: self.main_menu(),
            BotStates.INVITE_STATE: self.invite_menu(),
            BotStates.REGISTRATION_FIRST_NAME_STATE: self.registration_menu(),
            BotStates.REGISTRATION_LAST_NAME_STATE: self.registration_menu(),
            BotStates.WAITING_PHONE_STATE: self.registration_phone_menu(),
            BotStates.REGISTRATION_PHONE_STATE: self.registration_phone_menu(),
        }

    def main_menu(self):
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Чат мероприятия",
                        url=MINIAPP_URL_CHAT,
                    )
                ],
            ]
        )

    def invite_menu(self):
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Помощь")],
            ],
            resize_keyboard=True,
        )

    def registration_menu(self):
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="❌ Отмена")],
            ],
            resize_keyboard=True,
            one_time_keyboard=False,
            input_field_placeholder="Введите текст...",
        )

    def registration_phone_menu(self):
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="📱 Поделиться номером телефона", request_contact=True
                    )
                ],
                [KeyboardButton(text="❌ Отмена")],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
            input_field_placeholder="Нажмите на кнопку ниже",
        )

    def get_menu(self, state):
        # Получить меню, соответствующее текущему состоянию
        return self.menus.get(state, self.main_menu())  # Основное меню по умолчанию
