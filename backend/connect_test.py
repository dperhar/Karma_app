import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

async def main():
    # --- Загрузка переменных окружения ---
    print("Текущая директория:", os.getcwd())
    print("Содержимое директории:", os.listdir())
    
    env_path = os.path.join(os.getcwd(), '.env')
    print("Путь к .env файлу:", env_path)
    print("Файл существует:", os.path.exists(env_path))
    
    load_dotenv(env_path) # Загружает переменные из .env файла

    api_id_str = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    phone_number = os.getenv('PHONE_NUMBER')
    session_name = "my_telegram_session" # Имя файла сессии

    # --- Валидация переменных окружения ---
    if not all([api_id_str, api_hash, phone_number]):
        print("Ошибка: Не все переменные окружения (API_ID, API_HASH, PHONE_NUMBER) установлены.")
        print("Пожалуйста, создайте файл .env и укажите в нем эти значения.")
        return

    try:
        api_id = int(api_id_str)
    except ValueError:
        print(f"Ошибка: API_ID '{api_id_str}' должен быть числом.")
        return

    print("Переменные окружения загружены.")

    # --- Инициализация и подключение Telegram клиента ---
    # Используем файловую сессию по умолчанию, которая будет сохранена как {session_name}.session
    print(f"Инициализация клиента с сессией: {session_name}")
    async with TelegramClient(session_name, api_id, api_hash) as client:
        print("Клиент создан.")
        try:
            # Проверка, авторизован ли пользователь
            if not await client.is_user_authorized():
                print("Пользователь не авторизован. Попытка входа...")
                # Запрос номера телефона (Telethon может сделать это автоматически, если не указан)
                await client.send_code_request(phone_number)
                try:
                    code = input('Пожалуйста, введите код, полученный в Telegram: ')
                    await client.sign_in(phone_number, code)
                except SessionPasswordNeededError:
                    print("Требуется двухфакторная аутентификация (2FA).")
                    password = input('Пожалуйста, введите ваш пароль 2FA: ')
                    await client.sign_in(password=password)
                except Exception as e_signin:
                    print(f"Ошибка входа: {e_signin}")
                    return
                print("Вход выполнен успешно.")
            else:
                print("Пользователь уже авторизован.")

            # --- Получение информации о себе ---
            me = await client.get_me()
            if me:
                print("\n--- Информация о пользователе ---")
                print(f"ID: {me.id}")
                print(f"Имя: {me.first_name}")
                if me.last_name:
                    print(f"Фамилия: {me.last_name}")
                if me.username:
                    print(f"Username: @{me.username}")
                print(f"Телефон: {me.phone}")
            else:
                print("Не удалось получить информацию о пользователе.")


            # --- Получение списка недавних диалогов ---
            print("\n--- Первые 10 диалогов ---")
            dialog_count = 0
            async for dialog in client.iter_dialogs(limit=10):
                dialog_count += 1
                print(f"{dialog_count}. {dialog.name} (ID: {dialog.id})")
            
            if dialog_count == 0:
                print("Нет доступных диалогов или не удалось их загрузить.")

        except Exception as e:
            print(f"Произошла общая ошибка: {e}")
        finally:
            print("\nЗавершение работы.")


if __name__ == '__main__':
    print("Запуск скрипта connect_test.py...")
    asyncio.run(main()) 