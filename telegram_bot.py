from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from loguru import logger
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID
from binance_client import BinanceClient
import re

class TelegramBot:
    def __init__(self):
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("Telegram bot token eksik. Lütfen .env dosyasını kontrol edin.")
            
        if not TELEGRAM_CHANNEL_ID or not TELEGRAM_CHANNEL_ID.isdigit():
            raise ValueError("Geçersiz Telegram kanal ID. Lütfen .env dosyasını kontrol edin.")
            
        self.binance = BinanceClient()
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Mesaj işleyicilerini ekle
        self.application.add_handler(MessageHandler(
            filters.ChatType.CHANNEL & filters.Chat(chat_id=int(TELEGRAM_CHANNEL_ID)),
            self.handle_channel_message
        ))

    async def handle_channel_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            message = update.channel_post.text
            if not message:
                return

            # Sinyal formatını kontrol et
            signal = self.parse_signal(message)
            if not signal:
                return

            # Sinyali işle
            await self.process_signal(signal)

        except Exception as e:
            logger.error(f"Mesaj işleme hatası: {e}")

    def parse_signal(self, message: str) -> dict:
        try:
            # LONG sinyal formatı: LONG BTCUSDT Entry: 50000 SL: 49000 TP: 52000
            # SHORT sinyal formatı: SHORT BTCUSDT Entry: 50000 SL: 51000 TP: 48000
            pattern = r'(LONG|SHORT)\s+(\w+)\s+Entry:\s+(\d+\.?\d*)\s+SL:\s+(\d+\.?\d*)\s+TP:\s+(\d+\.?\d*)'
            match = re.search(pattern, message)
            
            if match:
                return {
                    'type': match.group(1),
                    'symbol': match.group(2),
                    'entry': float(match.group(3)),
                    'stop_loss': float(match.group(4)),
                    'take_profit': float(match.group(5))
                }
            return None
        except Exception as e:
            logger.error(f"Sinyal ayrıştırma hatası: {e}")
            return None

    async def process_signal(self, signal: dict):
        try:
            symbol = signal['symbol']
            side = 'BUY' if signal['type'] == 'LONG' else 'SELL'
            
            # Kaldıracı ayarla
            self.binance.set_leverage(symbol)
            
            # Pozisyon aç
            order = self.binance.open_position(
                symbol=symbol,
                side=side,
                quantity=self.calculate_position_size(symbol),
                entry_price=signal['entry'],
                stop_loss=signal['stop_loss'],
                take_profit=signal['take_profit']
            )
            
            if order:
                logger.info(f"Yeni pozisyon açıldı: {symbol} {signal['type']} Entry: {signal['entry']} SL: {signal['stop_loss']} TP: {signal['take_profit']}")

        except Exception as e:
            logger.error(f"Sinyal işleme hatası: {e}")

    def calculate_position_size(self, symbol: str) -> float:
        # Burada pozisyon büyüklüğü hesaplama mantığı eklenecek
        # Örnek: Bakiye * risk yüzdesi / stop loss mesafesi
        return 0.01  # Geçici değer

    def run(self):
        self.application.run_polling() 