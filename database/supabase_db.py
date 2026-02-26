from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
import logging
from typing import List, Optional

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
    async def add_to_ban_list(chat_id: int, message_id: int, user_id: int, username: str, full_name: str, suspect_message: str, ml_confidence: float = None):
        """Сохранить информацию о подозреваемом (с ML уверенностью)"""
        try:
            data = {
                "chat_id": chat_id,
                "message_id": message_id,
                "user_id": user_id,
                "username": username,
                "full_name": full_name,
                "suspect_message": suspect_message,
                "ml_confidence": ml_confidence,
                "status": "pending"
            }
            supabase.table("ban_list").insert(data).execute()
            logging.info(f"Suspicious user {user_id} added to ban_list")
        except Exception as e:
            logging.error(f"Error adding to ban_list: {e}")

    @staticmethod
    async def get_pending_suspect(message_id: int):
        """Получить данные о подозреваемом по ID сообщения (статус pending)"""
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

    @staticmethod
    async def get_suspect_message(message_id: int) -> Optional[dict]:
        """Получает запись из ban_list по message_id (для получения текста сообщения)"""
        try:
            result = supabase.table("ban_list").select("*").eq("message_id", message_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logging.error(f"Error getting suspect message: {e}")
            return None

    # Новые методы для ML обучения

    @staticmethod
    async def add_training_example(text: str, label: int, moderated_by: int):
        """Добавляет размеченный пример для обучения"""
        try:
            data = {
                "text": text,
                "label": label,
                "moderated_by": moderated_by,
                "processed": False
            }
            result = supabase.table("training_examples").insert(data).execute()
            logging.info(f"Training example added (label={label})")
            return result.data
        except Exception as e:
            logging.error(f"Error adding training example: {e}")
            return None

    @staticmethod
    async def get_unprocessed_training_examples() -> List[dict]:
        """Получает все необработанные примеры"""
        try:
            result = supabase.table("training_examples").select("*").eq("processed", False).execute()
            return result.data
        except Exception as e:
            logging.error(f"Error getting unprocessed training examples: {e}")
            return []

    @staticmethod
    async def mark_training_examples_processed(ids: List[int]):
        """Помечает примеры как обработанные"""
        try:
            supabase.table("training_examples").update({"processed": True}).in_("id", ids).execute()
            logging.info(f"Marked {len(ids)} training examples as processed")
        except Exception as e:
            logging.error(f"Error marking training examples as processed: {e}")
    
    @staticmethod
    async def get_training_stats() -> dict:
        """Получает статистику по обучающим примерам"""
        try:
            # Все примеры
            all_result = supabase.table("training_examples").select("*").execute()
            total = len(all_result.data)
            
            # Хорошие примеры (label=0)
            good_result = supabase.table("training_examples").select("*").eq("label", 0).execute()
            good = len(good_result.data)
            
            # Плохие примеры (label=1)
            bad_result = supabase.table("training_examples").select("*").eq("label", 1).execute()
            bad = len(bad_result.data)
            
            # Необработанные
            unprocessed_result = supabase.table("training_examples").select("*").eq("processed", False).execute()
            unprocessed = len(unprocessed_result.data)
            
            return {
                "total": total,
                "good": good,
                "bad": bad,
                "unprocessed": unprocessed
            }
        except Exception as e:
            logging.error(f"Error getting training stats: {e}")
            return {"total": 0, "good": 0, "bad": 0, "unprocessed": 0}