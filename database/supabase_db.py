from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class Database:
    @staticmethod
    async def add_trusted_user(user_id: int, username: str = None, full_name: str = None):
        """Добавить пользователя в список доверенных"""
        data = {
            "user_id": user_id,
            "username": username,
            "full_name": full_name
        }
        supabase.table("trusted_users").upsert(data).execute()

    @staticmethod
    async def is_trusted(user_id: int) -> bool:
        """Проверить, является ли пользователь доверенным"""
        result = supabase.table("trusted_users").select("*").eq("user_id", user_id).execute()
        return len(result.data) > 0

    @staticmethod
    async def add_to_ban_list(chat_id: int, message_id: int, user_id: int, username: str, full_name: str, suspect_message: str):
        """Сохранить информацию о подозреваемом"""
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

    @staticmethod
    async def get_pending_suspect(message_id: int):
        """Получить данные о подозреваемом по ID сообщения"""
        result = supabase.table("ban_list").select("*").eq("message_id", message_id).eq("status", "pending").execute()
        return result.data[0] if result.data else None

    @staticmethod
    async def update_suspect_status(message_id: int, status: str):
        """Обновить статус подозреваемого"""
        supabase.table("ban_list").update({"status": status}).eq("message_id", message_id).execute()