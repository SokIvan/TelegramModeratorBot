import re
from typing import List, Dict, Any

class BotDetector:
    """
    Расширяемый класс для обнаружения ботов по паттернам
    """
    
    def __init__(self):
        # Список паттернов для проверки
        self.patterns = [
            # Паттерны с подарками
            self._gift_patterns,
            # Паттерны с раздачами
            self._giveaway_patterns,
            # Паттерны с бесплатными подарками
            self._free_stuff_patterns,
            # Подозрительные эмодзи
            self._suspicious_emojis,
            # Спам-паттерны
            self._spam_patterns,
            # Паттерны с упоминанием конкурсов
            self._contest_patterns,
        ]
        
        # Регулярные выражения для быстрой проверки
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
            r"(?i)(t\.me/|telegram\.me/)",  # ссылки на другие каналы
        ]
        self.compiled_regex = [re.compile(pattern) for pattern in self.regex_patterns]
    
    async def is_suspicious(self, message_text: str, user_info: Dict[str, Any]) -> bool:
        """
        Основной метод проверки на подозрительность
        """
        if not message_text:
            return False
            
        # Проверяем каждый паттерн
        for pattern_func in self.patterns:
            if await pattern_func(message_text, user_info):
                return True
                
        # Проверяем регулярные выражения
        for regex in self.compiled_regex:
            if regex.search(message_text):
                return True
                
        return False
    
    async def _gift_patterns(self, text: str, user_info: Dict) -> bool:
        """Паттерны, связанные с подарками"""
        gift_keywords = ['подар', 'гив', 'гифт', 'гифта', 'гивов', 'gift', 'give']
        return any(keyword in text.lower() for keyword in gift_keywords)
    
    async def _giveaway_patterns(self, text: str, user_info: Dict) -> bool:
        """Паттерны раздач"""
        giveaway_keywords = ['разда', 'розыгр', 'конкурс', 'выигр']
        return any(keyword in text.lower() for keyword in giveaway_keywords)
    
    async def _free_stuff_patterns(self, text: str, user_info: Dict) -> bool:
        """Бесплатные предложения"""
        free_keywords = ['бесплатн', 'халяв', 'даров', 'free', 'бонус']
        return any(keyword in text.lower() for keyword in free_keywords)
    
    async def _suspicious_emojis(self, text: str, user_info: Dict) -> bool:
        """Много подозрительных эмодзи"""
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # эмоции
            "\U0001F300-\U0001F5FF"  # символы
            "\U0001F680-\U0001F6FF"  # транспорт
            "\U0001F1E0-\U0001F1FF"  # флаги
            "\U00002700-\U000027BF"  # символы
            "\U000024C2-\U0001F251" 
            "]+", flags=re.UNICODE
        )
        
        emojis = emoji_pattern.findall(text)
        emoji_count = sum(len(e) for e in emojis)
        
        # Если больше 3 эмодзи в коротком сообщении - подозрительно
        return emoji_count > 3 and len(text) < 100
    
    async def _spam_patterns(self, text: str, user_info: Dict) -> bool:
        """Спам-паттерны"""
        spam_keywords = ['@channel', '@everyone', 'подпишись', 'вступай', 'жми']
        return any(keyword in text.lower() for keyword in spam_keywords)
    
    async def _contest_patterns(self, text: str, user_info: Dict) -> bool:
        """Конкурсные паттерны"""
        contest_keywords = ['участв', 'побед', 'приз', 'призы', 'подарк']
        return any(keyword in text.lower() for keyword in contest_keywords)
    
    # Метод для добавления новых паттернов на лету
    def add_pattern(self, pattern_func):
        """Добавить новый паттерн для проверки"""
        self.patterns.append(pattern_func)