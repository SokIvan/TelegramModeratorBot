import re
import logging
from typing import List, Dict, Any, Optional, Tuple
import asyncio

from .ml_classifier import MLClassifier

logger = logging.getLogger(__name__)

class BotDetector:
    def __init__(self, use_ml: bool = True, ml_model_path: str = "models/bot_detector.pkl"):
        # Основные паттерны
        self.patterns = [
            self._gift_patterns,
            self._giveaway_patterns,
            self._free_stuff_patterns,
            self._suspicious_emojis,
            self._spam_patterns,
            self._contest_patterns,
            self._test_pattern,
            self._url_patterns,
            self._telegram_patterns,
            self._scam_patterns,
        ]
        
        # Улучшенные regex паттерны с контекстом
        self.regex_patterns = [
            # Ссылки на Telegram (только если это не упоминание канала)
            r"(?i)(?:^|\s)(t\.me/|telegram\.me/)(?![\w\d_]+$)",  # не просто упоминание юзернейма
            r"(?i)(?:^|\s)https?://(?:www\.)?t\.me/\w+",
            r"(?i)(?:^|\s)https?://(?:www\.)?telegram\.me/\w+",
            
            # Агрессивные призывы
            r"(?i)(?:^|\s)(забери|получи|забирай)\s*(?:бесплатно|подарок|приз)\s*(?:прямо\s*сейчас|сейчас)",
            r"(?i)(?:^|\s)(только\s*сейчас|только\s*сегодня|успей|поспеши|ограниченное\s*предложение)",
            r"(?i)(?:^|\s)(переходи|жми|кликай)\s*(?:по\s*ссылке|сюда|быстрее)",
            
            # Мошеннические схемы
            r"(?i)(?:^|\s)(бесплатные?\s*(?:подарки?|призы?)\s*за\s*подписку)",
            r"(?i)(?:^|\s)(напиши\s*\"\+\"|напиши\s*\"\-\"|напиши\s*в\s*чат)",  # типично для ботов
            r"(?i)(?:^|\s)(раздаю\s*подарки?\s*каждый\s*день)",
            r"(?i)(?:^|\s)(дарят?\s*(?:подарки?|призы?)\s*за\s*лайк)",
            
            # Подозрительные комбинации
            r"(?i)(?:^|\s)(?:как\s*получить|способ\s*получить)\s*(?:бесплатно|подарок)",
            r"(?i)(?:^|\s)(?:заработок|заработать)\s*(?:в\s*интернете|онлайн|легко)",
            
            # Капс и много восклицательных знаков (спам)
            r"[A-ZА-Я]{5,}",  # 5+ заглавных подряд
            r"!{3,}",  # 3+ восклицательных
        ]
        
        # Паттерны для исключений (не считаем подозрительным)
        self.exclusion_patterns = [
            r"(?i)(?:розыгрыш|конкурс)\s*(?:окончен|закончен|завершен)",
            r"(?i)(?:где|когда)\s*(?:мой|мои)\s*(?:приз|подарок)",
            r"(?i)(?:жду|ждем|ожидаем)\s*(?:результаты?|итоги?)",
            r"(?i)(?:спасибо|благодарю)\s*(?:за|организаторам?)",
            r"(?i)(?:поздравляю|поздравляем)\s*(?:победителя?|участников?)",
            r"(?i)(?:вопрос|ответ|интересно|думаю)",
            r"(?i)(?:кто\s*выиграл|кто\s*победил)",
            r"(?i)(?:когда\s*следующий|а\s*когда\s*будет)",
            r"(?i)(?:участвую|я\s*с\s*вами|хочу\s*участвовать)",
            r"(?i)^(?:ок|окей|хорошо|понял|поняла)$",
            r"(?i)(?:нет|да|возможно|наверное)$",
        ]
        
        # Слова-триггеры с контекстом
        self.gift_triggers = {
            'primary': ['подар', 'гив', 'гифт', 'gift', 'give'],
            'secondary': ['бесплатно', 'халяв', 'даров', 'free'],
            'context': ['конкурс', 'розыгр', 'приз']
        }
        
        # Слова, которые часто используются в обычных сообщениях
        self.common_words = {
            'спасибо', 'пожалуйста', 'здравствуйте', 'привет', 'пока',
            'хорошо', 'ок', 'понятно', 'интересно', 'класс', 'круто',
            'ого', 'вау', 'супер', 'отлично', 'здорово'
        }
        
        self.compiled_regex = [re.compile(pattern) for pattern in self.regex_patterns]
        self.exclusion_compiled = [re.compile(pattern) for pattern in self.exclusion_patterns]
        
        # Счетчики для анализа
        self.word_count_threshold = 50  # сообщения длиннее не проверяем по эмодзи
        
        
        # ML компонент
        self.use_ml = use_ml
        self.ml_classifier = None
        self.ml_confidence_threshold = 0.7  # Порог уверенности для ML
        
        if use_ml:
            self.ml_classifier = MLClassifier(model_path=ml_model_path)
            if not self.ml_classifier.load():
                logger.warning("ML модель не найдена, будет использоваться только rule-based детекция")
        
    async def is_suspicious(self, message_text: str, user_info: Dict[str, Any]) -> Tuple[bool, Optional[float]]:
        """
        Основной метод проверки сообщения
        
        Returns:
            (подозрительно ли, уверенность ML если есть)
        """
        if not message_text:
            return False, None
            
        # Быстрая проверка на исключения
        for excl_regex in self.exclusion_compiled:
            if excl_regex.search(message_text):
                logger.debug(f"Исключение сработало: {message_text[:50]}")
                return False, None
        
        # Сначала rule-based детекция (быстрая)
        rule_based_suspicious = False
        
        # Проверка regex-паттернов
        for regex in self.compiled_regex:
            if regex.search(message_text):
                rule_based_suspicious = True
                logger.debug(f"Regex сработал: {regex.pattern}")
                break
                
        # Проверка функций-паттернов
        if not rule_based_suspicious:
            for pattern_func in self.patterns:
                try:
                    result = await pattern_func(message_text, user_info)
                    if result:
                        rule_based_suspicious = True
                        logger.debug(f"Функция сработала: {pattern_func.__name__}")
                        break
                except Exception as e:
                    logger.error(f"Ошибка в {pattern_func.__name__}: {e}")
                    continue
        
        # Если rule-based не нашел ничего подозрительного, используем ML
        ml_confidence = None
        ml_suspicious = False
        
        if self.use_ml and self.ml_classifier and self.ml_classifier.is_trained:
            try:
                # Запускаем ML в отдельном потоке, чтобы не блокировать
                loop = asyncio.get_event_loop()
                pred, confidence = await loop.run_in_executor(
                    None, 
                    self.ml_classifier.predict, 
                    message_text
                )
                
                ml_confidence = confidence
                
                # ML считает подозрительным только если уверенность выше порога
                if pred == 1 and confidence >= self.ml_confidence_threshold:
                    ml_suspicious = True
                    logger.debug(f"ML определил как подозрительное с уверенностью {confidence:.3f}")
                    
            except Exception as e:
                logger.error(f"Ошибка ML предсказания: {e}")
        
        # Комбинируем результаты
        final_suspicious = rule_based_suspicious or ml_suspicious
        
        # Логируем для отладки
        if final_suspicious:
            logger.debug(f"Финальное решение: {final_suspicious} (rule: {rule_based_suspicious}, ml: {ml_suspicious}, conf: {ml_confidence})")
        
        return final_suspicious, ml_confidence
    
    async def _test_pattern(self, text: str, user_info: Dict) -> bool:
        """Тестовый паттерн"""
        text_lower = text.lower()
        if "пожарная часть" in text_lower:
            return True
        return False
    
    async def _gift_patterns(self, text: str, user_info: Dict) -> bool:
        """Умный поиск подарков с контекстом"""
        text_lower = text.lower()
        words = set(text_lower.split())
        
        # Проверяем не слишком ли короткое сообщение с подозрительными словами
        if len(words) < 3:  # Очень короткие сообщения
            return False
            
        # Считаем совпадения с разными категориями
        score = 0
        
        # Проверка первичных триггеров
        for trigger in self.gift_triggers['primary']:
            if trigger in text_lower:
                score += 2
                break
                
        # Проверка вторичных триггеров
        for trigger in self.gift_triggers['secondary']:
            if trigger in text_lower:
                score += 1
                
        # Проверка контекстных слов
        for trigger in self.gift_triggers['context']:
            if trigger in text_lower:
                score += 1
                
        # Проверка на URL рядом с подарками
        if 'http' in text_lower or 't.me' in text_lower:
            score += 2
            
        # Если набрано достаточно очков и нет общих слов
        if score >= 3:
            # Проверяем не является ли это обычным сообщением
            common_word_ratio = len([w for w in words if w in self.common_words]) / len(words)
            if common_word_ratio > 0.5:  # Если больше половины общих слов
                return False
            return True
            
        return False
    
    async def _giveaway_patterns(self, text: str, user_info: Dict) -> bool:
        """Умный поиск розыгрышей"""
        text_lower = text.lower()
        
        giveaway_keywords = ['разда', 'розыгр', 'конкурс']
        action_keywords = ['участв', 'побед', 'выигр']
        
        has_giveaway = any(k in text_lower for k in giveaway_keywords)
        has_action = any(k in text_lower for k in action_keywords)
        
        # Если есть оба типа слов, может быть подозрительно
        if has_giveaway and has_action:
            # Но проверяем контекст
            if 'когда' in text_lower or 'где' in text_lower:
                return False  # Вопросы обычно безопасны
            return True
            
        return False
    
    async def _free_stuff_patterns(self, text: str, user_info: Dict) -> bool:
        """Умный поиск бесплатного"""
        text_lower = text.lower()
        
        free_keywords = ['бесплатн', 'халяв', 'даров']
        
        for keyword in free_keywords:
            if keyword in text_lower:
                # Проверяем контекст
                if 'спасибо' in text_lower or 'класс' in text_lower:
                    return False
                if '?' in text_lower:
                    return False
                return True
                
        return False
    
    async def _suspicious_emojis(self, text: str, user_info: Dict) -> bool:
        """Анализ подозрительного использования эмодзи"""
        
        # Если сообщение слишком длинное, пропускаем (вероятно, обычный разговор)
        if len(text) > self.word_count_threshold:
            return False
            
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
        
        if not emojis:
            return False
            
        emoji_count = sum(len(e) for e in emojis)
        emoji_ratio = emoji_count / len(text) if text else 0
        
        # Подозрительно: много эмодзи в коротком тексте
        if emoji_count > 5 and len(text) < 50:
            return True
            
        # Подозрительно: высокая плотность эмодзи
        if emoji_ratio > 0.3 and len(text) < 100:
            return True
            
        return False
    
    async def _spam_patterns(self, text: str, user_info: Dict) -> bool:
        """Улучшенный поиск спама"""
        text_lower = text.lower()
        
        spam_keywords = ['@channel', '@everyone', 'подпишись', 'вступай']
        
        for keyword in spam_keywords:
            if keyword in text_lower:
                return True
                
        # Поиск призывов к действию
        call_to_action = ['жми', 'переходи', 'кликай']
        has_call = any(c in text_lower for c in call_to_action)
        has_link = 't.me' in text_lower or 'http' in text_lower
        
        if has_call and has_link:
            return True
            
        return False
    
    async def _contest_patterns(self, text: str, user_info: Dict) -> bool:
        """Поиск конкурсов"""
        text_lower = text.lower()
        
        contest_keywords = ['конкурс', 'розыгрыш', 'приз', 'призы']
        
        for keyword in contest_keywords:
            if keyword in text_lower:
                # Исключаем вопросы
                if '?' in text_lower:
                    return False
                return True
                
        return False
    
    async def _url_patterns(self, text: str, user_info: Dict) -> bool:
        """Анализ URL в сообщениях"""
        url_pattern = re.compile(r'https?://[^\s]+|t\.me/[^\s]+|telegram\.me/[^\s]+')
        urls = url_pattern.findall(text)
        
        if not urls:
            return False
            
        # Если больше одной ссылки - подозрительно
        if len(urls) > 1:
            return True
            
        # Если ссылка и короткое сообщение
        if len(text.split()) < 5:
            return True
            
        return False
    
    async def _telegram_patterns(self, text: str, user_info: Dict) -> bool:
        """Специфические Telegram паттерны"""
        text_lower = text.lower()
        
        # Поиск упоминаний каналов не нашего
        channel_mentions = re.findall(r'@(\w+)', text)
        if channel_mentions:
            # Если упоминается канал и есть призыв
            if 'подпишись' in text_lower or 'вступай' in text_lower:
                return True
                
        return False
    
    async def _scam_patterns(self, text: str, user_info: Dict) -> bool:
        """Поиск мошеннических паттернов"""
        text_lower = text.lower()
        
        scam_phrases = [
            'бесплатно за подписку',
            'получи приз за лайк',
            'раздача каждый день',
            'дарят подарки',
            'легкий заработок',
        ]
        
        for phrase in scam_phrases:
            if phrase in text_lower:
                return True
                
        return False
    
    # Добавим метод для обучения ML
    async def train_ml(self, texts: List[str], labels: List[int], incremental: bool = False) -> dict:
        if not self.use_ml:
            return {'error': 'ML отключен'}

        if not self.ml_classifier:
            self.ml_classifier = MLClassifier(model_path=self.ml_model_path)

        # Логируем типы и значения для отладки
        logger.info(f"train_ml: получено {len(texts)} примеров")
        logger.info(f"train_ml: первые 5 меток: {labels[:5]}, типы: {[type(l) for l in labels[:5]]}")

        loop = asyncio.get_event_loop()

        # Функция-обёртка для захвата исключений
        def _train_sync(classifier, texts, labels, incremental_flag):
            try:
                if incremental_flag and classifier.is_trained:
                    return classifier.incremental_train(texts, labels)
                else:
                    return classifier.train(texts, labels)
            except Exception as e:
                import traceback
                logger.error(f"Ошибка при обучении: {e}\n{traceback.format_exc()}")
                return {'error': str(e), 'traceback': traceback.format_exc()}

        result = await loop.run_in_executor(
            None,
            _train_sync,
            self.ml_classifier, texts, labels, incremental
        )

        if 'error' in result:
            logger.error(f"Обучение завершилось с ошибкой: {result['error']}")

        return result