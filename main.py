#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import locale
from loguru import logger
from telegram_client import TelegramHandler
from console_commands import ConsoleCommands
from binance_client import BinanceClient
from config import set_risk_multiplier  # Risk çarpanı ayarlama fonksiyonunu import et

def setup_environment():
    """Çalışma ortamını hazırla"""
    try:
        # Windows için UTF-8 ayarları
        if sys.platform == 'win32':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleCP(65001)
            kernel32.SetConsoleOutputCP(65001)
        
        # Varsayılan sistem locale'ini kullan
        if sys.platform == 'win32':
            locale.setlocale(locale.LC_ALL, '')
        else:
            locale.setlocale(locale.LC_ALL, 'tr_TR.UTF-8')
            
    except Exception as e:
        logger.warning(f"Ortam ayarları yapılırken uyarı: {e}")
        logger.info("Program çalışmaya devam edecek...")

def setup_logging():
    """Loglama yapılandırmasını ayarla"""
    # Log klasörünü oluştur
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Varsayılan logger'ı kaldır ve yeniden yapılandır
    logger.remove()

    # Konsol için renkli loglama
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    # Dosya için detaylı loglama
    logger.add(
        "logs/main.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="1 MB",
        retention=5,
        encoding='utf-8',
        mode='a'
    )

def get_risk_multiplier() -> float:
    """Kullanıcıdan risk çarpanını al"""
    while True:
        try:
            multiplier = input("\nRisk çarpanını girin (örn: 2.5): ").strip()
            multiplier = float(multiplier)
            if multiplier <= 0:
                logger.warning("Risk çarpanı 0'dan büyük olmalıdır!")
                continue
            return multiplier
        except ValueError:
            logger.warning("Geçersiz değer! Lütfen sayısal bir değer girin.")
        except KeyboardInterrupt:
            logger.info("Program sonlandırılıyor...")
            sys.exit(0)

def main():
    """Ana program fonksiyonu"""
    try:
        # Çevre değişkenlerini yükle
        setup_environment()
        
        logger.info("=" * 50)
        logger.info("Signal Sage başlatılıyor...")
        logger.info("=" * 50)
        
        # Risk çarpanını al
        risk_multiplier = get_risk_multiplier()
        set_risk_multiplier(risk_multiplier)
        logger.info(f"Risk çarpanı {risk_multiplier}x olarak ayarlandı")
        
        # Binance bağlantısını kontrol et
        try:
            binance_client = BinanceClient()
            
            # Futures hesap durumunu kontrol et
            logger.info("\n=== Futures Hesap Durumu ===")
            try:
                # Futures bakiyesini kontrol et
                futures_balance = binance_client.get_futures_balance()
                logger.info(f"Futures USDT Bakiyesi: {futures_balance:.2f} USDT")
                
                # Spot bakiyesini kontrol et
                spot_balance = binance_client.get_spot_balance()
                logger.info(f"Spot USDT Bakiyesi: {spot_balance:.2f} USDT")
                
                # Toplam bakiye
                total_balance = futures_balance + spot_balance
                logger.info(f"Toplam USDT Bakiyesi: {total_balance:.2f} USDT")
                
                # Açık pozisyonları kontrol et
                open_positions = binance_client.get_open_positions()
                if open_positions:
                    logger.info("\nAçık Pozisyonlar:")
                    for pos in open_positions:
                        logger.info(f"Sembol: {pos['symbol']}")
                        logger.info(f"Yön: {pos['side']}")
                        logger.info(f"Miktar: {pos['amount']}")
                        logger.info(f"Giriş Fiyatı: {pos['entryPrice']}")
                        logger.info(f"İşaret Fiyatı: {pos['markPrice']}")
                        logger.info(f"Kar/Zarar: {pos['unrealizedProfit']} USDT")
                        logger.info("-" * 30)
                else:
                    logger.info("\nAçık pozisyon bulunmuyor.")
                
            except Exception as e:
                logger.error(f"Futures hesap durumu kontrolünde hata: {e}")
                logger.error("Futures hesabınızın açık olduğundan emin olun!")
                return
            
            logger.info("=" * 50)
            
            # Konsol komutlarını başlat
            console = ConsoleCommands()
            console_thread = console.run_in_thread()
            
            logger.info("Telegram bağlantısı kuruluyor...")
            # Telegram handler'ı başlat
            handler = TelegramHandler()
            
            # Botu çalıştır
            handler.run()
            
            # Konsol thread'ini bekle
            console_thread.join()
            
        except Exception as e:
            logger.error(f"Binance bağlantı hatası: {e}")
            return
        
    except KeyboardInterrupt:
        logger.info("\nProgram kullanıcı tarafından durduruldu")
    except Exception as e:
        logger.error(f"Program hatası: {e}")
        import traceback
        logger.error(f"Hata izleme:\n{traceback.format_exc()}")
    finally:
        logger.info("\nProgram sonlandırıldı")

if __name__ == "__main__":
    main() 