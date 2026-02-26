import pickle
import logging
import os
from typing import List, Tuple, Optional
import re
from collections import Counter
#skip some imports
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

class MLClassifier:
    """
    Легковесный ML классификатор для детекции ботов
    Использует SGDClassifier (стохастический градиентный спуск) - очень быстрый и легкий
    """
    
    def __init__(self, model_path: str = "models/bot_detector.pkl"):
        self.model_path = model_path
        self.pipeline = None
        self.is_trained = False
        
        # Создаем директорию для моделей, если её нет
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
    def _create_pipeline(self) -> Pipeline:
        """Создает pipeline с TF-IDF и SGDClassifier"""
        return Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=5000,  # Ограничиваем количество признаков
                ngram_range=(1, 3),  # Используем униграммы, биграммы и триграммы
                min_df=2,  # Игнорируем слова, встречающиеся меньше 2 раз
                max_df=0.9,  # Игнорируем слишком частые слова
                analyzer='char_wb',  # Анализируем символы внутри слов (лучше для русского)
                token_pattern=r'(?u)\b\w+\b'
            )),
            ('clf', SGDClassifier(
                loss='log_loss',  # Логистическая регрессия через SGD
                penalty='l2',
                alpha=1e-4,  # Сила регуляризации
                max_iter=1000,
                tol=1e-3,
                learning_rate='optimal',
                class_weight=None,
                random_state=42,
                n_jobs=-1  # Используем все ядра
            ))
        ])
    
    def _preprocess_text(self, texts: List[str]) -> List[str]:
        """Предобработка текстов"""
        processed = []
        for text in texts:
            if not text:
                processed.append("")
                continue
                
            # Приводим к нижнему регистру
            text = text.lower()
            
            # Заменяем URL на специальный токен
            text = re.sub(r'https?://\S+|t\.me/\S+|telegram\.me/\S+', ' [URL] ', text)
            
            # Заменяем упоминания пользователей
            text = re.sub(r'@\w+', ' [USER] ', text)
            
            # Заменяем числа
            text = re.sub(r'\d+', ' [NUM] ', text)
            
            # Убираем лишние пробелы
            text = re.sub(r'\s+', ' ', text).strip()
            
            processed.append(text)
            
        return processed
    
    
    def train(self, texts: List[str], labels: List[int]) -> dict:
        """
        Обучает модель на новых данных
        
        Args:
            texts: список текстов
            labels: список меток (0 - нормально, 1 - подозрительно)
            
        Returns:
            dict с метриками обучения
        """
        if len(texts) < 10:
            raise ValueError("Слишком мало данных для обучения (минимум 10)")
            
        # Предобработка
        processed_texts = self._preprocess_text(texts)
        
        # Создаем pipeline
        self.pipeline = self._create_pipeline()
        
        # Обучаем
        self.pipeline.fit(processed_texts, labels)
        self.is_trained = True
        
        # Оцениваем качество
        if len(texts) >= 20:
            X_train, X_test, y_train, y_test = train_test_split(
                processed_texts, labels, test_size=0.2, random_state=42
            )
            self.pipeline.fit(X_train, y_train)
            accuracy = self.pipeline.score(X_test, y_test)
            
            logger.info(f"Модель обучена. Точность на тесте: {accuracy:.3f}")
            
            # Сохраняем модель
            self.save()
            
            return {
                'accuracy': accuracy,
                'train_size': len(X_train),
                'test_size': len(X_test)
            }
        else:
            self.pipeline.fit(processed_texts, labels)
            self.save()
            return {
                'accuracy': None,
                'train_size': len(texts),
                'test_size': 0
            }
    
    def incremental_train(self, texts: List[str], labels: List[int]) -> dict:
        if not self.is_trained or self.pipeline is None:
            return self.train(texts, labels)

        # Приводим метки к int, отбрасываем недопустимые
        clean_labels = []
        clean_texts = []
        for t, l in zip(texts, labels):
            try:
                label = int(l)
            except (ValueError, TypeError):
                logger.warning(f"Невозможно преобразовать метку {l} (тип {type(l)}) в int")
                continue
            if label not in (0, 1):
                logger.warning(f"Метка {label} не является 0 или 1")
                continue
            clean_labels.append(label)
            clean_texts.append(t)

        if not clean_labels:
            logger.warning("Нет валидных примеров для инкрементального обучения")
            return {'incremental': False, 'reason': 'no valid examples'}

        processed = self._preprocess_text(clean_texts)
        try:
            self.pipeline.named_steps['clf'].partial_fit(
                self.pipeline.named_steps['tfidf'].transform(processed),
                clean_labels,
                classes=np.array([0, 1])
            )
        except Exception as e:
            logger.error(f"Ошибка в partial_fit: {e}")
            raise  # пробрасываем дальше, чтобы увидеть в логах

        logger.info(f"Модель дообучена на {len(clean_texts)} примерах")
        self.save()
        return {'incremental': True, 'new_samples': len(clean_texts)}
    
    def predict(self, text: str) -> Tuple[int, float]:
        """
        Предсказывает класс текста
        
        Returns:
            (класс, уверенность)
        """
        if not self.is_trained or self.pipeline is None:
            return 0, 0.0
            
        processed = self._preprocess_text([text])
        
        # Получаем вероятности
        probs = self.pipeline.predict_proba(processed)[0]
        pred = self.pipeline.predict(processed)[0]
        
        confidence = probs[pred]
        
        return int(pred), float(confidence)
    
    def save(self):
        """Сохраняет модель"""
        if self.pipeline:
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.pipeline, f)
            logger.info(f"Модель сохранена в {self.model_path}")
    
    def load(self) -> bool:
        """Загружает модель"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    self.pipeline = pickle.load(f)
                self.is_trained = True
                logger.info(f"Модель загружена из {self.model_path}")
                return True
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            
        return False