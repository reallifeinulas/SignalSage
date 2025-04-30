from loguru import logger
from binance_client import BinanceClient
from telegram_client import TelegramHandler
from config import set_risk_multiplier, RISK_MULTIPLIER, TELEGRAM_CHANNEL_IDS
import asyncio
from threading import Thread
import sys
import json
from datetime import datetime
from cmd import Cmd
import os
from dotenv import load_dotenv, set_key

class ConsoleCommands(Cmd):
    def __init__(self):
        super().__init__()
        self.prompt = 'SignalSage> '
        self.binance = BinanceClient()
        self.telegram_handler = TelegramHandler()
        self.commands = {
            'bakiye': self.show_balance,
            'islem': self.show_positions,
            'yardim': self.show_help,
            'deneme': self.run_test_signal,
            'risk': self.set_risk,
            'q': self.quit_program,
            'channels': self.do_channels
        }
        
    def show_help(self):
        """Mevcut komutları göster"""
        logger.info("\n=== Kullanılabilir Komutlar ===")
        logger.info("bakiye  : Futures ve Spot bakiyelerini göster")
        logger.info("islem   : Açık işlemleri listele")
        logger.info("deneme  : Test sinyali ile deneme işlemi yap")
        logger.info("risk    : Risk çarpanını ayarla (örn: risk 5)")
        logger.info("yardim  : Bu yardım mesajını göster")
        logger.info("q       : Programdan çık")
        logger.info("channels: Dinlenen kanalları listele veya yönet")
        
    def show_balance(self):
        """Futures ve Spot bakiyelerini göster"""
        try:
            # Futures bakiyesi
            futures_balance = self.binance.get_futures_balance()
            
            # Spot bakiyesi
            spot_balance = self.binance.get_spot_balance()
            
            # Toplam bakiye
            total_balance = futures_balance + spot_balance
            
            # Bakiye bilgilerini göster
            logger.info("\n=== Bakiye Bilgileri ===")
            logger.info(f"Futures USDT : {futures_balance:>10.2f}")
            logger.info(f"Spot USDT    : {spot_balance:>10.2f}")
            logger.info("-" * 30)
            logger.info(f"Toplam USDT   : {total_balance:>10.2f}")
            
        except Exception as e:
            logger.error(f"Bakiye bilgisi alınırken hata: {e}")
            
    def show_positions(self):
        """Açık işlemleri göster"""
        try:
            positions = self.binance.get_open_positions()
            
            if not positions:
                logger.info("\nAçık işlem bulunmuyor")
                return
                
            logger.info("\n=== Açık İşlemler ===")
            for pos in positions:
                direction = "LONG" if pos['side'] == 'BUY' else "SHORT"
                profit = float(pos['unrealizedProfit'])
                profit_color = "green" if profit >= 0 else "red"
                
                logger.info(f"Sembol    : {pos['symbol']}")
                logger.info(f"Yön       : {direction}")
                logger.info(f"Miktar    : {pos['amount']:.4f}")
                logger.info(f"Giriş     : {pos['entryPrice']:.8f}")
                logger.info(f"Güncel    : {pos['markPrice']:.8f}")
                logger.info(f"Kar/Zarar : <{profit_color}>{profit:.2f} USDT</{profit_color}>")
                logger.info("-" * 40)
                
        except Exception as e:
            logger.error(f"Açık işlemler alınırken hata: {e}")
            
    def run_test_signal(self):
        """Test sinyalini işle"""
        try:
            logger.info("\n=== Test Sinyali İşleniyor ===")
            
            # Test mesajını oku
            try:
                with open('deneme_mesaj.txt', 'r', encoding='utf-8') as f:
                    test_message = f.read()
                logger.info("Test mesajı okundu")
            except Exception as e:
                logger.error(f"Test mesajı okuma hatası: {e}")
                return
                
            # Mesajı parse et
            try:
                logger.info("Sinyal ayrıştırılıyor...")
                signal = self.telegram_handler.parse_signal(test_message)
                if not signal:
                    logger.error("Sinyal ayrıştırılamadı!")
                    return
                    
                logger.info("\nAyrıştırılan Sinyal:")
                logger.info(f"Sembol: {signal['symbol']}")
                logger.info(f"İşlem Tipi: {signal['type']}")
                logger.info(f"Kaldıraç: {signal['leverage']}x")
                logger.info(f"Margin Türü: {signal['margin_type']}")
                
                logger.info("\nGiriş Seviyeleri:")
                for entry in signal['entries']:
                    logger.info(f"Seviye {entry['level']}: {entry['price']} ({entry['risk_percentage']}%)")
                    
                logger.info("\nHedef Seviyeleri:")
                for target in signal['targets']:
                    logger.info(f"Seviye {target['level']}: {target['price']} | {target['success_rate']}% | {target['profit_percentage']}%")
                    
                logger.info(f"\nStop Loss: {signal['stop_loss']}")
                logger.info(f"Take Profit: {signal['take_profit']}")
                
            except Exception as e:
                logger.error(f"Sinyal ayrıştırma hatası: {e}")
                return
                
            # Kullanıcıya onay sor
            try:
                logger.info("\nİşlem açmak istiyor musunuz? (E/H)")
                response = input().strip().lower()
                
                if response != 'e':
                    logger.info("İşlem iptal edildi")
                    return
                    
                # İşlemi aç
                logger.info("\nİşlem açılıyor...")
                
                # Yeni event loop oluştur
                try:
                    # Mevcut event loop'u kontrol et
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        # Event loop yoksa yeni bir tane oluştur
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # process_signal'i çalıştır
                    result = loop.run_until_complete(self.telegram_handler.process_signal(signal))
                    
                    if result:
                        logger.info("Test işlemi başarıyla açıldı!")
                    else:
                        logger.error("Test işlemi açılamadı!")
                        
                finally:
                    # Event loop'u kapat
                    try:
                        loop.close()
                    except Exception:
                        pass
                    
            except Exception as e:
                logger.error(f"İşlem açma hatası: {e}")
                
        except Exception as e:
            logger.error(f"Test sırasında hata: {e}")
            
    def quit_program(self):
        """Programı düzgün bir şekilde sonlandır"""
        logger.info("Program kapatılıyor...")
        sys.exit(0)
        
    def start_console(self):
        """Konsol komutlarını dinlemeye başla"""
        logger.info("\nKomut satırı aktif. Komutları görmek için 'yardim' yazın.")
        
        while True:
            try:
                command = input().strip().lower()
                
                if command in self.commands:
                    self.commands[command]()
                else:
                    logger.warning(f"Geçersiz komut: {command}")
                    logger.info("Kullanılabilir komutları görmek için 'yardim' yazın")
                    
            except EOFError:
                break
            except KeyboardInterrupt:
                self.quit_program()
            except Exception as e:
                logger.error(f"Komut işlenirken hata: {e}")
                
    def run_in_thread(self):
        """Konsol komutlarını ayrı bir thread'de çalıştır"""
        console_thread = Thread(target=self.start_console, daemon=True)
        console_thread.start()
        return console_thread

    def set_risk(self):
        """Risk çarpanını ayarla"""
        try:
            if not arg:
                logger.info(f"Mevcut risk çarpanı: {RISK_MULTIPLIER}x")
                return
                
            new_risk = float(arg)
            if new_risk <= 0:
                logger.error("Risk çarpanı 0'dan büyük olmalıdır")
                return
                
            # Risk çarpanını güncelle
            set_risk_multiplier(new_risk)
            logger.info(f"Risk çarpanı {new_risk}x olarak ayarlandı")
            
            # .env dosyasını da güncelle
            dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
            set_key(dotenv_path, 'RISK_MULTIPLIER', str(new_risk))
            logger.info(".env dosyası güncellendi")
            
        except ValueError:
            logger.error("Geçersiz risk değeri. Lütfen sayısal bir değer girin")
            
    def do_channels(self, arg):
        """Dinlenen kanalları listele veya yönet
        Kullanım: 
            channels list - Mevcut kanalları listele
            channels add ID - Yeni kanal ekle
            channels remove ID - Kanal kaldır
        Örnek: channels add 5288263135"""
        args = arg.split()
        if not args:
            logger.info("Mevcut kanallar:")
            for channel in TELEGRAM_CHANNEL_IDS:
                logger.info(f"  {channel}")
            return
            
        command = args[0].lower()
        
        if command == "list":
            logger.info("Dinlenen kanallar:")
            for channel in TELEGRAM_CHANNEL_IDS:
                logger.info(f"  {channel}")
                
        elif command == "add" and len(args) == 2:
            try:
                new_channel = int(args[1])
                channels = set(TELEGRAM_CHANNEL_IDS)  # Tekrarları önlemek için set kullan
                channels.add(new_channel)
                channel_str = ",".join(str(c) for c in channels)
                
                # .env dosyasını güncelle
                dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
                set_key(dotenv_path, 'TELEGRAM_CHANNEL_IDS', channel_str)
                logger.info(f"Kanal {new_channel} eklendi")
                logger.info("Değişikliklerin etkili olması için programı yeniden başlatın")
                
            except ValueError:
                logger.error("Geçersiz kanal ID. Sayısal bir değer girin")
                
        elif command == "remove" and len(args) == 2:
            try:
                remove_channel = int(args[1])
                channels = set(TELEGRAM_CHANNEL_IDS)
                if remove_channel in channels:
                    channels.remove(remove_channel)
                    channel_str = ",".join(str(c) for c in channels)
                    
                    # .env dosyasını güncelle
                    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
                    set_key(dotenv_path, 'TELEGRAM_CHANNEL_IDS', channel_str)
                    logger.info(f"Kanal {remove_channel} kaldırıldı")
                    logger.info("Değişikliklerin etkili olması için programı yeniden başlatın")
                else:
                    logger.error(f"Kanal {remove_channel} listede bulunamadı")
                    
            except ValueError:
                logger.error("Geçersiz kanal ID. Sayısal bir değer girin")
        else:
            logger.error("Geçersiz komut. Kullanım: channels [list|add ID|remove ID]") 