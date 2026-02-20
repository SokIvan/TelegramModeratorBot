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
        if not message_text:
            logger.debug("Empty message text, skipping")
            return False

        logger.debug(f"Checking message: {message_text[:100]} from user {user_info.get('id')}")

        # Проверка regex
        for idx, regex in enumerate(self.compiled_regex):
            if regex.search(message_text):
                logger.info(f"Suspicious regex #{idx} matched: {regex.pattern}")
                return True

        # Проверка функций-паттернов
        for pattern_func in self.patterns:
            if await pattern_func(message_text, user_info):
                logger.info(f"Suspicious pattern matched: {pattern_func.__name__}")
                return True

        logger.debug("No suspicious patterns found")
        return False

    async def _gift_patterns(self, text: str, user_info: Dict) -> bool:
        gift_keywords = ['подар', 'гив', 'гифт', 'гифта', 'гивов', 'gift', 'give']
        result = any(keyword in text.lower() for keyword in gift_keywords)
        if result:
            logger.debug("_gift_patterns triggered")
        return result

    async def _giveaway_patterns(self, text: str, user_info: Dict) -> bool:
        giveaway_keywords = ['разда', 'розыгр', 'конкурс', 'выигр']
        result = any(keyword in text.lower() for keyword in giveaway_keywords)
        if result:
            logger.debug("_giveaway_patterns triggered")
        return result

    async def _free_stuff_patterns(self, text: str, user_info: Dict) -> bool:
        free_keywords = ['бесплатн', 'халяв', 'даров', 'free', 'бонус']
        result = any(keyword in text.lower() for keyword in free_keywords)
        if result:
            logger.debug("_free_stuff_patterns triggered")
        return result

    async def _suspicious_emojis(self, text: str, user_info: Dict) -> bool:
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002700-\U000027BF"
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE
        )
        emojis = emoji_pattern.findall(text)
        emoji_count = sum(len(e) for e in emojis)
        result = emoji_count > 3 and len(text) < 100
        if result:
            logger.debug(f"_suspicious_emojis triggered: {emoji_count} emojis")
        return result

    async def _spam_patterns(self, text: str, user_info: Dict) -> bool:
        spam_keywords = ['@channel', '@everyone', 'подпишись', 'вступай', 'жми']
        result = any(keyword in text.lower() for keyword in spam_keywords)
        if result:
            logger.debug("_spam_patterns triggered")
        return result

    async def _contest_patterns(self, text: str, user_info: Dict) -> bool:
        contest_keywords = ['участв', 'побед', 'приз', 'призы', 'подарк']
        result = any(keyword in text.lower() for keyword in contest_keywords)
        if result:
            logger.debug("_contest_patterns triggered")
        return result