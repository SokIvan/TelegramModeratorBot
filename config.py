import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHANNEL_CHAT_ID = os.getenv("CHANNEL_CHAT_ID")
BAN_LIST_CHAT_ID = int(os.getenv("BAN_LIST_CHAT_ID")) if os.getenv("BAN_LIST_CHAT_ID").lstrip('-').isdigit() else os.getenv("BAN_LIST_CHAT_ID")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")