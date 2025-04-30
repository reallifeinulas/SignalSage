from telethon import TelegramClient, events
from loguru import logger
from config import (
    TELEGRAM_API_ID, 
    TELEGRAM_API_HASH, 
    TELEGRAM_PHONE,
    TELEGRAM_CHANNEL_IDS
)
from binance_client import BinanceClient
import re
import asyncio
from datetime import datetime
import json
import os
import sys

# Loglama yapılandırması
logger.remove()  # Varsayılan logger'ı kaldır

# Konsol için renkli loglama
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Dosya için detaylı loglama
logger.add(
    "logs/telegram.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation="1 MB",
    retention=5,
    encoding='utf-8',
    mode='a'
)

class TelegramHandler:
    def __init__(self):
        logger.info("TelegramHandler başlatılıyor...")
        self.client = TelegramClient('signal_session', TELEGRAM_API_ID, TELEGRAM_API_HASH)
        self.binance = BinanceClient()  # Binance client'ı aktif et
        self.last_messages = []  # Son mesajları tutacak liste
        self.signals_dir = "signals"  # Sinyallerin kaydedileceği klasör
        
        # Sinyal klasörünü oluştur
        if not os.path.exists(self.signals_dir):
            os.makedirs(self.signals_dir)
            logger.info(f"Sinyal klasörü oluşturuldu: {self.signals_dir}")
        
    async def connect(self):
        """Telegram'a bağlan ve gerekirse telefon doğrulaması yap"""
        logger.info("Telegram bağlantısı kuruluyor...")
        await self.client.start(phone=TELEGRAM_PHONE)
        logger.info("Telegram bağlantısı başarılı")
        return TELEGRAM_CHANNEL_IDS

    async def start_monitoring(self):
        """Kanal mesajlarını dinlemeye başla"""
        channel_ids = await self.connect()
        
        # İzlenecek kullanıcı ID'si
        user_id = 5288263135
        
        # Hem kanalları hem de kullanıcıyı dinle
        @self.client.on(events.NewMessage(chats=[*channel_ids, user_id]))
        async def handle_new_message(event):
            try:
                message = event.message.text
                if not message:  # Mesaj boşsa atla
                    return
                    
                # Mesaj kaynağını belirle
                if hasattr(event.message.peer_id, 'channel_id'):
                    source_type = "Kanal"
                    source_id = event.message.peer_id.channel_id
                elif hasattr(event.message.peer_id, 'user_id'):
                    source_type = "Kullanıcı"
                    source_id = event.message.peer_id.user_id
                else:
                    return  # Diğer tür mesajları atla
                
                # Yeni mesajı anında işle
                logger.info(f"Yeni mesaj alındı ({source_type} ID: {source_id})")
                logger.info(f"Mesaj içeriği:\n{message}")
                
                # Yeni mesajı listeye ekle
                message_info = {
                    'source_type': source_type,
                    'source_id': source_id,
                    'date': event.message.date,
                    'text': message
                }
                self.last_messages.append(message_info)
                # Listeyi 50 mesajla sınırla
                if len(self.last_messages) > 50:
                    self.last_messages.pop(0)
                
                # Mesajı analiz et ve işle
                signal = self.parse_signal(message)
                if signal:
                    logger.info(f"Sinyal tespit edildi ({source_type} ID: {source_id}), işleme alınıyor...")
                    await self.process_signal(signal)
                else:
                    logger.debug(f"Bu mesaj bir sinyal değil, atlanıyor ({source_type} ID: {source_id})")
                    
            except Exception as e:
                logger.error(f"Mesaj işleme hatası: {e}")
                logger.debug(f"Hata detayı: {type(e).__name__}", exc_info=True)

        logger.info(f"Kanallar dinlemeye başlandı: {channel_ids}")
        await self.client.run_until_disconnected()

    def run(self):
        """Ana döngüyü başlat"""
        loop = asyncio.get_event_loop()
        try:
            # Programı başlat
            loop.run_until_complete(self.start_monitoring())
        except KeyboardInterrupt:
            logger.info("Bot durduruluyor...")
            
            # Telegram client'ı düzgün bir şekilde kapat
            try:
                loop.run_until_complete(self.client.disconnect())
                logger.info("Telegram bağlantısı düzgün bir şekilde kapatıldı")
            except Exception as e:
                logger.error(f"Telegram bağlantısı kapatılırken hata: {e}")
                
        except Exception as e:
            logger.error(f"Beklenmeyen hata: {e}")
        finally:
            try:
                # Tüm bekleyen görevleri tamamla
                pending = asyncio.all_tasks(loop=loop)
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                
                # Event loop'u kapat
                loop.close()
                logger.info("Program düzgün bir şekilde kapatıldı")
            except Exception as e:
                logger.error(f"Program kapatılırken hata: {e}")

    def display_last_messages(self):
        """Son mesajları göster"""
        if not self.last_messages:
            logger.info("Henüz hiç mesaj alınmamış")
            return
            
        logger.info("\n=== SON MESAJLAR ===")
        # Mesajları tarihe göre sırala (en yeni en üstte)
        sorted_messages = sorted(self.last_messages, 
                               key=lambda x: x['date'], 
                               reverse=True)
        
        for msg in sorted_messages:
            date_str = msg['date'].strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"\nKanal: {msg['source_id']}")
            logger.info(f"Tarih: {date_str}")
            logger.info(f"Mesaj:\n{msg['text']}\n")
            logger.info("-" * 50)
        
    def clean_message(self, message: str) -> str:
        """Mesajı temizle ve standart formata getir"""
        try:
            # Orijinal mesajı logla
            logger.info("Mesaj temizleme başlıyor")
            logger.info(f"Orijinal mesaj:\n{message}")
            
            # Mesajın bir kopyasını al
            cleaned = message
            
            # Görünmez karakterleri temizle (newline ve tab hariç)
            original_length = len(cleaned)
            cleaned = ''.join(char for char in cleaned if char.isprintable() or char in ['\n', '\t'])
            if len(cleaned) != original_length:
                logger.info(f"{original_length - len(cleaned)} adet görünmez karakter temizlendi")
            
            # Satır sonlarındaki boşlukları temizle ama satır içi boşluklara dokunma
            cleaned = '\n'.join(line.strip() for line in cleaned.split('\n'))
            
            # Birden fazla boş satırı teke indir
            original_lines = cleaned.count('\n')
            cleaned = '\n'.join(line for line in cleaned.split('\n') if line.strip() or line.strip() == '')
            if cleaned.count('\n') != original_lines:
                logger.info(f"{original_lines - cleaned.count('\n')} adet fazla boş satır temizlendi")
            
            # Temizlenmiş mesajı logla
            if cleaned != message:
                logger.info("Mesaj temizleme tamamlandı")
                logger.info(f"Temizlenmiş mesaj:\n{cleaned}")
            else:
                logger.info("Mesajda temizlenecek bir şey bulunamadı")
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Mesaj temizleme sırasında hata: {e}")
            logger.error(f"Hata detayı: {type(e).__name__}")
            # Hata durumunda orijinal mesajı geri döndür
            return message

    def validate_signal_format(self, message: str) -> bool:
        """Sinyal formatının geçerli olup olmadığını basit bir şekilde kontrol et"""
        try:
            # Sadece temel kontroller yap
            if '#' not in message:
                logger.warning("Sembol işareti (#) bulunamadı")
                return False
                
            if not any(word in message.upper() for word in ['LONG', 'SHORT']):
                logger.warning("İşlem yönü (LONG/SHORT) bulunamadı")
                return False
                
            if 'x' not in message:
                logger.warning("Kaldıraç bilgisi (örn: 20x) bulunamadı")
                return False
                
            # "son 10" kontrolü ekle
            if 'son 10' not in message.lower():
                logger.warning("'son 10' ifadesi bulunamadı")
                return False
                
            # Mesajda | karakteri varsa ve sayısal değerler varsa, muhtemelen bir sinyaldir
            if '|' in message and any(c.isdigit() for c in message):
                return True
                
            logger.warning("Sinyal formatı için gerekli karakterler bulunamadı")
            return False
            
        except Exception as e:
            logger.error(f"Format doğrulama hatası: {e}")
            return False

    def parse_signal(self, message: str) -> dict:
        try:
            # Mesajı temizle
            message = self.clean_message(message)
            
            # Temel format kontrolü
            if not self.validate_signal_format(message):
                logger.error("Temel sinyal formatı geçerli değil")
                logger.error(f"Ham mesaj:\n{message}")
                return None
            
            # Özel karakterleri standartlaştır
            normalized_message = message.replace('․', '.').replace('，', ',').replace('：', ':')
            
            # Debug: Normalize edilmiş mesajı göster
            logger.debug(f"Normalize edilmiş mesaj:\n{normalized_message}")
            
            # Sembol ve işlem tipini bul - daha esnek regex
            symbol_match = re.search(r'#(\w+)', normalized_message)
            type_match = re.search(r'(LONG|SHORT)', normalized_message, re.IGNORECASE)
            leverage_match = re.search(r'(\d+)\s*x', normalized_message)
            
            if not all([symbol_match, type_match, leverage_match]):
                logger.error("Temel bilgiler eksik")
                return None
                
            symbol = symbol_match.group(1)
            trade_type = type_match.group(1).upper()
            leverage = int(leverage_match.group(1))
            margin_type = 'Cross'  # Varsayılan olarak Cross kullan
            
            # Sayısal değerleri bul - çok daha esnek regex
            entry_pattern = r'(\d+)\s*\|[^|]*?[`"]?([\d.]+)[`"]?[^|]*?\(.*?([\d.]+)%'
            entry_lines = re.findall(entry_pattern, normalized_message)
            
            if not entry_lines:
                logger.error("Giriş seviyeleri bulunamadı, daha esnek arama yapılıyor...")
                # Alternatif pattern dene
                entry_pattern = r'(\d+)\s*[-|]+\s*[`"]?([\d.]+)[`"]?\s*[-|]+\s*([\d.]+)'
                entry_lines = re.findall(entry_pattern, normalized_message)
            
            entries = []
            for match in entry_lines:
                try:
                    level = int(match[0])
                    price = float(match[1].strip().replace('`', ''))
                    risk = float(match[2].strip().replace('%', ''))
                    entries.append({
                        "level": level,
                        "price": price,
                        "risk_percentage": risk
                    })
                    logger.debug(f"Giriş seviyesi ayrıştırıldı: Seviye {level}, Fiyat: {price}, Risk: {risk}%")
                except (ValueError, IndexError) as e:
                    logger.warning(f"Giriş seviyesi ayrıştırma hatası, atlanıyor: {e}")
                    continue
            
            if not entries:
                logger.error("Hiçbir giriş seviyesi ayrıştırılamadı")
                return None
            
            # Hedef seviyeleri için daha esnek pattern
            target_patterns = [
                # Ana pattern: 1 | `0.5788` | 100% | 130%
                r'(\d+)\s*\|\s*[`"]?([\d.]+)[`"]?\s*\|\s*(\d+)%\s*\|\s*(-?\d+)%',
                # Alternatif pattern: 1 | 0.5788 | 100 | 130
                r'(\d+)\s*\|\s*[`"]?([\d.]+)[`"]?\s*\|\s*(\d+)\s*\|\s*(-?\d+)',
                # Daha esnek pattern
                r'(\d+)\s*[-|]+\s*[`"]?([\d.]+)[`"]?\s*[-|]+\s*(\d+)[%]?\s*[-|]+\s*(-?\d+)[%]?'
            ]
            
            targets = []
            for pattern in target_patterns:
                target_lines = re.findall(pattern, normalized_message)
                logger.debug(f"Hedef pattern '{pattern}' için bulunan eşleşmeler: {len(target_lines)}")
                
                if target_lines:
                    for match in target_lines:
                        try:
                            level = int(match[0])
                            price = float(match[1].strip().replace('`', ''))
                            success = int(match[2].strip().replace('%', ''))
                            profit = int(match[3].strip().replace('%', ''))
                            
                            targets.append({
                                "level": level,
                                "price": price,
                                "success_rate": success,
                                "profit_percentage": profit
                            })
                            logger.debug(f"Hedef seviyesi ayrıştırıldı: Seviye {level}, Fiyat: {price}, Başarı: {success}%, Kar: {profit}%")
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Hedef seviyesi ayrıştırma hatası, atlanıyor: {e}")
                            continue
                    
                    if targets:  # Eğer hedefler bulunduysa diğer pattern'leri denemeye gerek yok
                        break
            
            if not targets:
                logger.error("Hiçbir hedef seviyesi ayrıştırılamadı")
                # Debug: Hedef olabilecek satırları göster
                for line in normalized_message.split('\n'):
                    if '|' in line and '%' in line:
                        logger.debug(f"Potansiyel hedef satırı: {line}")
                return None
            
            # Stop loss için daha esnek arama
            stop_patterns = [
                r'(?:Stop|SL|Stop\s*Loss)[^0-9]*?[`"]?([\d.]+)[`"]?',
                r'[Ss]top\s*@?\s*[`"]?([\d.]+)[`"]?',
                r'SL\s*[-=:@]?\s*[`"]?([\d.]+)[`"]?'
            ]
            
            stop_loss = None
            for pattern in stop_patterns:
                match = re.search(pattern, normalized_message)
                if match:
                    try:
                        stop_loss = float(match.group(1).replace('`', ''))
                        logger.debug(f"Stop loss bulundu: {stop_loss}")
                        break
                    except ValueError:
                        continue
            
            if stop_loss is None:
                logger.error("Stop loss seviyesi bulunamadı")
                return None
            
            # Take profit için 5. hedefi bul
            take_profit = None
            for target in targets:
                if target['level'] == 5:
                    take_profit = target['price']
                    break
            
            signal = {
                'symbol': f"{symbol}USDT",
                'type': trade_type,
                'leverage': leverage,
                'margin_type': margin_type,
                'entries': entries,
                'targets': targets,
                'stop_loss': stop_loss,
                'take_profit': take_profit,  # 5. hedef fiyatını kullan
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info("=== Ayrıştırılan Sinyal ===")
            logger.info(f"Sembol: {signal['symbol']}")
            logger.info(f"Yön: {signal['type']}")
            logger.info(f"Kaldıraç: {leverage}x")
            logger.info("\nGiriş Seviyeleri:")
            for entry in entries:
                logger.info(f"  Seviye {entry['level']}: {entry['price']} ({entry['risk_percentage']}%)")
            logger.info("\nHedefler:")
            for target in targets:
                logger.info(f"  Seviye {target['level']}: {target['price']} ({target['profit_percentage']}%)")
            logger.info(f"\nStop Loss: {stop_loss}")
            logger.info(f"Take Profit (5. hedef): {take_profit}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Sinyal ayrıştırma hatası: {e}")
            logger.error(f"Ham mesaj:\n{message}")
            return None

    def save_signal(self, signal: dict) -> bool:
        """Sinyali JSON formatında kaydet"""
        try:
            # Dosya adını oluştur: symbol_timestamp.json
            filename = f"{signal['symbol']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(self.signals_dir, filename)
            
            # Sinyal verilerini kontrol et
            required_fields = ['symbol', 'type', 'entries', 'targets', 'stop_loss']
            for field in required_fields:
                if field not in signal:
                    logger.error(f"Eksik zorunlu alan: {field}")
                    return False
                    
            if not signal['entries']:
                logger.error("Giriş seviyeleri boş")
                return False
                
            if not signal['targets']:
                logger.error("Hedef seviyeleri boş")
                return False
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(signal, f, ensure_ascii=False, indent=4)
                
            logger.info(f"Sinyal başarıyla kaydedildi: {filepath}")
            return True
            
        except json.JSONEncodeError as e:
            logger.error(f"JSON dönüştürme hatası: {e}")
            return False
        except IOError as e:
            logger.error(f"Dosya yazma hatası: {e}")
            return False
        except Exception as e:
            logger.error(f"Sinyal kaydetme sırasında beklenmeyen hata: {e}")
            return False

    def get_latest_signal(self, symbol: str = None) -> dict:
        """En son sinyali veya belirli bir sembolün en son sinyalini getir"""
        try:
            if not os.path.exists(self.signals_dir):
                logger.error(f"Sinyal klasörü bulunamadı: {self.signals_dir}")
                return None
                
            # Tüm sinyal dosyalarını al
            signal_files = [f for f in os.listdir(self.signals_dir) if f.endswith('.json')]
            
            if not signal_files:
                logger.error("Hiç sinyal dosyası bulunamadı")
                return None
                
            # Sembol filtresi varsa uygula
            if symbol:
                signal_files = [f for f in signal_files if f.startswith(symbol)]
                if not signal_files:
                    logger.error(f"Belirtilen sembol için sinyal bulunamadı: {symbol}")
                    return None
            
            # En son dosyayı bul
            latest_file = max(signal_files, key=lambda x: os.path.getctime(os.path.join(self.signals_dir, x)))
            filepath = os.path.join(self.signals_dir, latest_file)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    signal = json.load(f)
                    
                # Sinyal verilerini doğrula
                required_fields = ['symbol', 'type', 'entries', 'targets', 'stop_loss']
                for field in required_fields:
                    if field not in signal:
                        logger.error(f"Sinyal dosyasında eksik alan: {field}")
                        return None
                        
                return signal
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON okuma hatası: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Sinyal okuma sırasında beklenmeyen hata: {e}")
            return None

    async def process_signal(self, signal: dict):
        """Sinyali işler ve pozisyon açar."""
        try:
            if not signal:
                logger.error("Geçersiz sinyal verisi")
                return False

            # Önce sinyali kaydet
            if not self.save_signal(signal):
                logger.error("Sinyal kaydedilemedi")
                return False

            symbol = signal['symbol']
            trade_type = signal['type']
            leverage = signal['leverage']
            entries = signal['entries']
            stop_loss = signal['stop_loss']
            
            # 5. hedefi take profit olarak al
            take_profit = None
            for target in signal['targets']:
                if target['level'] == 5:  # 5. hedefi bul
                    take_profit = target['price']
                    break
                    
            if not take_profit:
                logger.error("5. hedef seviyesi bulunamadı")
                return False

            logger.info(f"İşlem başlatılıyor...")
            logger.info(f"Sembol: {symbol}")
            logger.info(f"Tip: {trade_type}")
            logger.info(f"Kaldıraç: {leverage}x")
            logger.info(f"Giriş Seviyeleri: {[entry['price'] for entry in entries]}")
            logger.info(f"Stop Loss: {stop_loss}")
            logger.info(f"Take Profit (5. hedef): {take_profit}")

            # Kaldıracı ayarla
            self.binance.set_leverage_and_margin_type(symbol, leverage, signal['margin_type'])
            logger.info(f"Kaldıraç {leverage}x olarak ayarlandı")

            # Kademeli pozisyon aç
            orders = self.binance.open_staged_position(
                symbol=symbol,
                side='BUY' if trade_type == 'LONG' else 'SELL',
                entries=[{
                    "price": entry["price"],
                    "risk_percentage": entry["risk_percentage"]
                } for entry in entries],
                stop_loss=stop_loss,
                take_profit=take_profit
            )

            if orders:
                logger.info("Pozisyon başarıyla açıldı")
                # İşlem başarılı olduğunda dosyayı işlenmiş olarak işaretle
                self.mark_signal_processed(signal)
                return True
            else:
                logger.error("Pozisyon açılamadı")
                return False

        except Exception as e:
            logger.error(f"Sinyal işlenirken hata oluştu: {e}")
            logger.error(f"Hata detayı: {type(e).__name__}")
            return False

    def mark_signal_processed(self, signal: dict):
        """Sinyali işlenmiş olarak işaretle"""
        try:
            # En son oluşturulan sinyal dosyasını bul
            signal_files = [f for f in os.listdir(self.signals_dir) 
                          if f.startswith(signal['symbol']) and f.endswith('.json')]
            
            if not signal_files:
                logger.error(f"Sinyal dosyası bulunamadı: {signal['symbol']}")
                return
                
            # En son oluşturulan dosyayı bul (timestamp'e göre)
            latest_file = max(signal_files, 
                            key=lambda x: os.path.getctime(os.path.join(self.signals_dir, x)))
            filepath = os.path.join(self.signals_dir, latest_file)
            
            # İşlenmiş klasörü oluştur
            processed_dir = os.path.join(self.signals_dir, "processed")
            if not os.path.exists(processed_dir):
                os.makedirs(processed_dir)
                logger.info(f"İşlenmiş sinyaller klasörü oluşturuldu: {processed_dir}")
                
            # Dosyayı taşı
            new_filename = f"processed_{latest_file}"
            new_path = os.path.join(processed_dir, new_filename)
            
            os.rename(filepath, new_path)
            logger.info(f"Sinyal işlenmiş olarak işaretlendi: {new_path}")
            
        except Exception as e:
            logger.error(f"Sinyal işaretleme hatası: {e}")
            logger.error(f"Hata detayı: {type(e).__name__}") 