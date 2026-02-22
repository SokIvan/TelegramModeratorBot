import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class BotDetector:
    def __init__(self):

        
        self.patterns = [
            self._gift_patterns,
            self._giveaway_patterns,
            self._free_stuff_patterns,
            self._suspicious_emojis,
            self._spam_patterns,
            self._contest_patterns,
            self._test_pattern,
        ]
        
        self.regex_patterns = [
            r"(?i)(бесплатн[ыо][еёй]\s+подарк[иа])",
            r"(?i)(разда[юу]т?\s+подарк[ии])",
            r"(?i)(халяв[аы]\s+подарк[ии])",
            r"(?i)(промокод\s+на\s+подарок)",
            r"(?i)(бот\s+раздает)",
            r"(?i)(забери\s+подарок)",
            r"(?i)(получи\s+бесплатно)",
            r"(?i)(успей\s+забрать)",
            r"(?i)(только\s+сегодня)",
            r"(?i)(переходи\s+по\s+ссылке)",
            r"(?i)(t\.me/|telegram\.me/)",
        ]
        
        self.compiled_regex = [re.compile(pattern) for pattern in self.regex_patterns]


    async def is_suspicious(self, message_text: str, user_info: Dict[str, Any]) -> bool:
        """Основной метод проверки сообщения"""
        

        
        if not message_text:

            return False

        # Проверка regex-паттернов

        
        for idx, regex in enumerate(self.compiled_regex):

            if regex.search(message_text):

                return True


        # Проверка функций-паттернов

        
        for pattern_func in self.patterns:
            func_name = pattern_func.__name__

            
            result = await pattern_func(message_text, user_info)
            
            if result:

                return True



        return False

    async def _test_pattern(self, text: str, user_info: Dict) -> bool:
        """Тестовый паттерн для проверки работы бота"""
        text_lower = text.lower()
        

        
        if "пожарная часть" in text_lower:

            return True
        else:

            return False

    async def _gift_patterns(self, text: str, user_info: Dict) -> bool:
        gift_keywords = ['подар', 'гив', 'гифт', 'гифта', 'гивов', 'gift', 'give']
        text_lower = text.lower()
        

        
        for keyword in gift_keywords:
            if keyword in text_lower:

                return True
        

        return False

    async def _giveaway_patterns(self, text: str, user_info: Dict) -> bool:
        giveaway_keywords = ['разда', 'розыгр', 'конкурс', 'выигр']
        text_lower = text.lower()
        

        
        for keyword in giveaway_keywords:
            if keyword in text_lower:

                return True
        

        return False

    async def _free_stuff_patterns(self, text: str, user_info: Dict) -> bool:
        free_keywords = ['бесплатн', 'халяв', 'даров', 'free', 'бонус']
        text_lower = text.lower()
        

        
        for keyword in free_keywords:
            if keyword in text_lower:

                return True
        

        return False

    async def _suspicious_emojis(self, text: str, user_info: Dict) -> bool:

        
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # эмоции
            "\U0001F300-\U0001F5FF"  # символы
            "\U0001F680-\U0001F6FF"  # транспорт
            "\U0001F1E0-\U0001F1FF"  # флаги
            "\U00002700-\U000027BF"  # разные символы
            "\U000024C2-\U0001F251"  # прочее
            "]+", flags=re.UNICODE
        )
        
        emojis = emoji_pattern.findall(text)
        emoji_count = sum(len(e) for e in emojis)
        

        
        result = emoji_count > 3 and len(text) < 100

        
        return result

    async def _spam_patterns(self, text: str, user_info: Dict) -> bool:
        spam_keywords = ['@channel', '@everyone', 'подпишись', 'вступай', 'жми']
        text_lower = text.lower()
        

        
        for keyword in spam_keywords:
            if keyword in text_lower:

                return True
        

        return False

    async def _contest_patterns(self, text: str, user_info: Dict) -> bool:
        contest_keywords = ['участв', 'побед', 'приз', 'призы', 'подарк']
        text_lower = text.lower()
        

        
        for keyword in contest_keywords:
            if keyword in text_lower:

                return True
        

        return False