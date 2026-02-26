from utils.detector import BotDetector

# Единый экземпляр детектора для всего приложения
detector = BotDetector(use_ml=True, ml_model_path="models/bot_detector.pkl")