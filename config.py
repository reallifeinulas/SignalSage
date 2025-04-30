import os
from dotenv import load_dotenv
import json

# .env dosyasını yükle
load_dotenv()

# Telegram API yapılandırması
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_PHONE = os.getenv('TELEGRAM_PHONE')

# Telegram kanal listesini al ve integer listesine çevir
TELEGRAM_CHANNEL_IDS = [int(channel_id.strip()) for channel_id in os.getenv('TELEGRAM_CHANNEL_IDS', '').split(',') if channel_id.strip()]

# Binance API yapılandırması
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')

# Risk ayarları
RISK_SETTINGS_FILE = 'risk_settings.json'

def load_risk_settings():
    try:
        if os.path.exists(RISK_SETTINGS_FILE):
            with open(RISK_SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                return settings.get('risk_multiplier', 1.0)
        return float(os.getenv('RISK_MULTIPLIER', 1.0))
    except Exception as e:
        print(f"Risk ayarları yüklenirken hata: {e}")
        return 1.0

def save_risk_settings(risk_multiplier):
    try:
        settings = {'risk_multiplier': risk_multiplier}
        with open(RISK_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f)
        return True
    except Exception as e:
        print(f"Risk ayarları kaydedilirken hata: {e}")
        return False

RISK_PERCENTAGE = float(os.getenv('RISK_PERCENTAGE', 1.0))
RISK_MULTIPLIER = load_risk_settings()

def set_risk_multiplier(multiplier: float):
    global RISK_MULTIPLIER
    RISK_MULTIPLIER = float(multiplier)
    save_risk_settings(multiplier) 