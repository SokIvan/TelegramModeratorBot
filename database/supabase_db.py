from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
import logging

# Создаем клиент Supabase

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class Database:
    @staticmethod
    async def add_trusted_user(user_id: int, username: str = None, full_name: str = None):
        """Добавить пользователя в список доверенных"""
        try:
            data = {
                "user_id": user_id,
                "username": username,
                "full_name": full_name
            }
            # Используем upsert для обновления или вставки
            supabase.table("trusted_users").upsert(data).execute()
            logging.info(f"User {user_id} added to trusted list")
        except Exception as e:
            logging.error(f"Error adding trusted user: {e}")

    @staticmethod
    async def is_trusted(user_id: int) -> bool:
        """Проверить, является ли пользователь доверенным"""
        try:
            result = supabase.table("trusted_users").select("*").eq("user_id", user_id).execute()
            return len(result.data) > 0
        except Exception as e:
            logging.error(f"Error checking trusted user: {e}")
            return False

    @staticmethod
    async def add_to_ban_list(chat_id: int, message_id: int, user_id: int, username: str, full_name: str, suspect_message: str):
        """Сохранить информацию о подозреваемом"""
        try:
            data = {
                "chat_id": chat_id,
                "message_id": message_id,
                "user_id": user_id,
                "username": username,
                "full_name": full_name,
                "suspect_message": suspect_message,
                "status": "pending"
            }
            supabase.table("ban_list").insert(data).execute()
            logging.info(f"Suspicious user {user_id} added to ban_list")
        except Exception as e:
            logging.error(f"Error adding to ban_list: {e}")

    @staticmethod
    async def get_pending_suspect(message_id: int):
        """Получить данные о подозреваемом по ID сообщения"""
        try:
            result = supabase.table("ban_list").select("*").eq("message_id", message_id).eq("status", "pending").execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logging.error(f"Error getting pending suspect: {e}")
            return None

    @staticmethod
    async def update_suspect_status(message_id: int, status: str):
        """Обновить статус подозреваемого"""
        try:
            supabase.table("ban_list").update({"status": status}).eq("message_id", message_id).execute()
            logging.info(f"Updated suspect status to {status} for message {message_id}")
        except Exception as e:
            logging.error(f"Error updating suspect status: {e}")