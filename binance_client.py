#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ccxt
from loguru import logger
from config import BINANCE_API_KEY, BINANCE_API_SECRET, RISK_MULTIPLIER
from typing import List, Dict
import json
from datetime import datetime
import sys
import os

class BinanceClient:
    def __init__(self):
        if not BINANCE_API_KEY or not BINANCE_API_SECRET:
            raise ValueError("Binance API anahtarları eksik. Lütfen .env dosyasını kontrol edin.")
            
        try:
            # CCXT exchange nesnesini oluştur
            self.exchange = ccxt.binance({
                'apiKey': BINANCE_API_KEY,
                'secret': BINANCE_API_SECRET,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',
                    'adjustForTimeDifference': True,
                    'recvWindow': 60000,
                    'warnOnFetchOpenOrdersWithoutSymbol': False,
                },
                'timeout': 30000,
                'headers': {
                    'Content-Type': 'application/json',
                    'User-Agent': 'SignalSage/1.0'
                }
            })
            
            # API bağlantısını test et
            self.test_connection()
            logger.info("Binance Futures bağlantısı başarıyla kuruldu")
            
        except ccxt.NetworkError as e:
            logger.error(f"Binance ağ hatası: {e}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Binance borsa hatası: {e}")
            raise
        except Exception as e:
            logger.error(f"Binance bağlantı hatası: {e}")
            raise

    def test_connection(self):
        """API bağlantısını test et"""
        try:
            self.exchange.fetch_balance()
        except Exception as e:
            logger.error(f"Bağlantı testi başarısız: {e}")
            raise

    def get_futures_balance(self) -> float:
        """Futures hesap bakiyesini al"""
        try:
            balance = self.exchange.fetch_balance()
            usdt_balance = balance['USDT']['free']
            return usdt_balance
        except Exception as e:
            logger.error(f"Futures bakiye alma hatası: {e}")
            return 0.0

    def calculate_position_size(self, symbol: str, risk_percentage: float, entry_price: float) -> float:
        """
        Pozisyon büyüklüğünü hesapla
        :param symbol: İşlem sembolü
        :param risk_percentage: Risk yüzdesi (örn: 1.5 for 1.5%)
        :param entry_price: Giriş fiyatı
        :return: Pozisyon büyüklüğü (coin miktarı)
        """
        try:
            # Config'den risk çarpanını tekrar yükle
            from config import RISK_MULTIPLIER
            logger.info(f"Mevcut risk çarpanı (RISK_MULTIPLIER): {RISK_MULTIPLIER}")
            
            balance = self.get_futures_balance()
            logger.info(f"Futures bakiyesi: {balance} USDT")
            
            # Risk yüzdesini risk çarpanı ile çarp
            adjusted_risk = risk_percentage * RISK_MULTIPLIER
            logger.info(f"Orijinal risk yüzdesi: {risk_percentage}%")
            logger.info(f"Risk çarpanı: {RISK_MULTIPLIER}x")
            logger.info(f"Ayarlanmış risk yüzdesi: {adjusted_risk}%")
            
            # Risk tutarını hesapla (bu bizim gerçek yatıracağımız USDT miktarı)
            risk_amount = balance * (adjusted_risk / 100)
            logger.info(f"Hesaplanan risk tutarı (yatırılacak USDT): {risk_amount} USDT")
            
            # Kaldıraçlı işlem hacmini hesapla (20x)
            leveraged_position_value = risk_amount * 20  # 20x kaldıraç
            logger.info(f"Kaldıraçlı işlem hacmi: {leveraged_position_value} USDT")
            
            # Coin miktarını hesapla (kaldıraçlı hacim / giriş fiyatı)
            position_size = leveraged_position_value / entry_price
            logger.info(f"Giriş fiyatı: {entry_price}")
            logger.info(f"Hesaplanan coin miktarı: {position_size}")
            
            # Minimum işlem büyüklüğü kontrolü (5.1 USDT)
            min_notional = 5.1  # Binance minimum işlem büyüklüğü + güvenlik payı
            position_value = position_size * entry_price / 20  # Gerçek yatırılan USDT
            
            if position_value < min_notional:
                logger.warning(f"Hesaplanan işlem değeri ({position_value} USDT) minimum limitin altında!")
                logger.warning(f"Minimum limit: {min_notional} USDT")
                # Minimum limite göre pozisyon büyüklüğünü ayarla
                position_size = (min_notional * 20) / entry_price
                logger.info(f"Pozisyon büyüklüğü minimum limite göre ayarlandı: {position_size}")
            
            position_size = round(position_size, 3)
            final_value = position_size * entry_price
            real_cost = final_value / 20
            
            logger.info("\n=== Son Pozisyon Detayları ===")
            logger.info(f"Son pozisyon büyüklüğü: {position_size} {symbol.replace('USDT', '')}")
            logger.info(f"Kaldıraçlı işlem değeri: {final_value} USDT")
            logger.info(f"Gerçek maliyet: {real_cost} USDT")
            logger.info(f"Kullanılan risk yüzdesi: {adjusted_risk}%")
            
            return position_size
            
        except Exception as e:
            logger.error(f"Pozisyon büyüklüğü hesaplama hatası: {e}")
            logger.error(f"Hata detayı: {type(e).__name__}")
            return 0.0

    def set_leverage_and_margin_type(self, symbol: str, leverage: int, margin_type: str = 'Cross'):
        """Kaldıraç ve margin türünü ayarla"""
        try:
            # Önce margin türünü ayarla
            self.exchange.set_margin_mode(
                marginMode=margin_type.upper(),
                symbol=symbol
            )
            logger.info(f"{symbol} için margin türü {margin_type} olarak ayarlandı")
            
            # Sonra kaldıracı ayarla
            self.exchange.set_leverage(
                leverage=leverage,
                symbol=symbol
            )
            logger.info(f"{symbol} için kaldıraç {leverage}x olarak ayarlandı")
            
        except Exception as e:
            logger.error(f"Kaldıraç ve margin türü ayarlama hatası: {e}")
            raise

    def check_balance_sufficient(self, required_margin: float) -> bool:
        """İşlem açmak için yeterli bakiye var mı kontrol et"""
        try:
            balance = self.get_futures_balance()
            if balance >= required_margin:
                logger.info(f"Yeterli bakiye mevcut: {balance} USDT")
                return True
            else:
                logger.warning(f"Yetersiz bakiye! Gerekli: {required_margin} USDT, Mevcut: {balance} USDT")
                return False
        except Exception as e:
            logger.error(f"Bakiye kontrol hatası: {e}")
            return False

    def calculate_required_margin(self, position_size: float, entry_price: float, leverage: int) -> float:
        """Gerekli marjin miktarını hesapla"""
        return (position_size * entry_price) / leverage

    def check_symbol_trading_active(self, symbol: str) -> bool:
        """Sembolün işleme açık olup olmadığını kontrol et"""
        try:
            # Önce piyasa bilgisini al
            ticker = self.exchange.fetch_ticker(symbol)
            
            # Son işlem fiyatı varsa ve sıfırdan büyükse, sembol aktif demektir
            if ticker and ticker['last'] > 0:
                logger.info(f"{symbol} işleme açık, son fiyat: {ticker['last']}")
                return True
                
            logger.warning(f"{symbol} için fiyat bilgisi alınamadı!")
            return False
            
        except Exception as e:
            logger.error(f"Sembol durum kontrolü hatası: {e}")
            # Hata durumunda True döndür çünkü bu genelde API hatası olabilir
            # ve gerçekte sembol işleme açık olabilir
            logger.warning("API hatası nedeniyle işleme devam ediliyor")
            return True

    def validate_order_limits(self, symbol: str, quantity: float, price: float = None) -> bool:
        """Emir miktarı ve fiyatının minimum/maksimum limitler içinde olup olmadığını kontrol et"""
        try:
            market = self.exchange.market(symbol)
            
            # Miktar kontrolü
            min_amount = market['limits']['amount']['min']
            max_amount = market['limits']['amount']['max']
            if quantity < min_amount or quantity > max_amount:
                logger.warning(f"Miktar limitlerin dışında! Min: {min_amount}, Max: {max_amount}, İstenen: {quantity}")
                return False
                
            # Limit emirler için fiyat kontrolü
            if price:
                min_price = market['limits']['price']['min']
                max_price = market['limits']['price']['max']
                if price < min_price or price > max_price:
                    logger.warning(f"Fiyat limitlerin dışında! Min: {min_price}, Max: {max_price}, İstenen: {price}")
                    return False
                    
            return True
        except Exception as e:
            logger.error(f"Limit kontrolü hatası: {e}")
            return False

    def check_and_set_position_mode(self, symbol: str):
        """Pozisyon modunu One-way Mode olarak ayarla"""
        try:
            # Doğrudan Binance Futures API'sini kullan
            self.exchange.fapiPrivatePostPositionSideDual({
                'dualSidePosition': 'false'  # One-way Mode için false
            })
            logger.info("Pozisyon modu One-way Mode olarak ayarlandı")
        except Exception as e:
            if "No need to change position side" in str(e):
                logger.info("Pozisyon modu zaten One-way Mode")
            else:
                logger.error(f"Pozisyon modu ayarlama hatası: {e}")

    def cancel_all_orders(self, symbol: str):
        """
        Belirli bir sembol için tüm bekleyen emirleri iptal et.
        Diğer sembollerin emirlerine dokunmaz.
        
        :param symbol: İşlem sembolü (örn: 'BTCUSDT')
        :return: True başarılı ise, False hata durumunda
        """
        try:
            logger.info(f"{symbol} için bekleyen emirler kontrol ediliyor...")
            
            # Sadece bu sembol için açık emirleri al
            open_orders = self.exchange.fetch_open_orders(symbol)
            
            if not open_orders:
                logger.info(f"{symbol} için bekleyen emir bulunmuyor")
                return True
                
            logger.info(f"{symbol} için {len(open_orders)} adet bekleyen emir bulundu")
            cancelled = []
            
            # Her bir emri iptal et
            for order in open_orders:
                try:
                    self.exchange.cancel_order(order['id'], symbol)
                    cancelled.append(order['id'])
                    logger.info(f"{symbol} için emir iptal edildi: {order['id']} ({order['type']} - {order['side']} - {order.get('price', 'market')})")
                except Exception as e:
                    logger.error(f"{symbol} için emir iptal edilirken hata: {order['id']} - {e}")
            
            success_rate = len(cancelled) / len(open_orders) * 100 if open_orders else 100
            logger.info(f"{symbol} için toplam {len(cancelled)} emir iptal edildi (Başarı oranı: {success_rate:.1f}%)")
            return True
            
        except Exception as e:
            logger.error(f"{symbol} için emirleri iptal ederken hata: {e}")
            return False

    def open_staged_position(self, 
                           symbol: str, 
                           side: str,
                           entries: List[Dict[str, float]],
                           stop_loss: float,
                           take_profit: float,
                           margin_type: str = 'Cross'):
        """
        Kademeli pozisyon açma
        İlk seviye market order, sonraki seviyeler için limit emirler
        Tüm pozisyon için tek bir stop-loss emri
        4. hedef seviyesi take-profit olarak kullanılır
        Take profit tetiklendiğinde tüm bekleyen emirler iptal edilir
        """
        try:
            # Sembol kontrolü
            if not self.check_symbol_trading_active(symbol):
                logger.error(f"{symbol} işleme kapalı, pozisyon açılamıyor")
                return None

            # Pozisyon modunu One-way Mode olarak ayarla
            self.check_and_set_position_mode(symbol)

            # Önce margin türünü ve kaldıracı ayarla
            self.set_leverage_and_margin_type(symbol, leverage=20, margin_type=margin_type)
            
            orders = []
            current_position = 0  # Toplam pozisyon büyüklüğü
            
            # İlk seviye için market order
            first_entry = entries[0]
            first_quantity = self.calculate_position_size(
                symbol=symbol,
                risk_percentage=first_entry["risk_percentage"],
                entry_price=first_entry["price"]
            )

            # Miktar kontrolü
            if not self.validate_order_limits(symbol, first_quantity):
                logger.error("İlk giriş miktarı geçersiz, işlem iptal ediliyor")
                return None

            # Marjin kontrolü
            required_margin = self.calculate_required_margin(first_quantity, first_entry["price"], 20)
            if not self.check_balance_sufficient(required_margin):
                logger.error("Yetersiz bakiye, işlem iptal ediliyor")
                return None
            
            # İlk seviye için market order - Önce parametresiz dene
            try:
                first_order = self.exchange.create_order(
                    symbol=symbol,
                    type='MARKET',
                    side=side,
                    amount=first_quantity
                )
            except Exception as e:
                if "reduceOnly" in str(e):
                    logger.info(f"{symbol} için reduceOnly parametresi gerekli, tekrar deneniyor...")
                    first_order = self.exchange.create_order(
                        symbol=symbol,
                        type='MARKET',
                        side=side,
                        amount=first_quantity,
                        params={
                            'reduceOnly': False
                        }
                    )
                else:
                    raise e

            orders.append(first_order)
            current_position += first_quantity
            
            # Sonraki seviyeler için limit emirler
            for entry in entries[1:]:
                quantity = self.calculate_position_size(
                    symbol=symbol,
                    risk_percentage=entry["risk_percentage"],
                    entry_price=entry["price"]
                )

                # Miktar ve fiyat kontrolü
                if not self.validate_order_limits(symbol, quantity, entry["price"]):
                    logger.warning(f"Limit emir miktarı/fiyatı geçersiz, bu seviye atlanıyor: {entry}")
                    continue
                
                # Limit order - Önce parametresiz dene
                try:
                    limit_order = self.exchange.create_order(
                        symbol=symbol,
                        type='LIMIT',
                        side=side,
                        amount=quantity,
                        price=entry["price"]
                    )
                except Exception as e:
                    if "reduceOnly" in str(e):
                        logger.info(f"{symbol} için reduceOnly parametresi gerekli, tekrar deneniyor...")
                        limit_order = self.exchange.create_order(
                            symbol=symbol,
                            type='LIMIT',
                            side=side,
                            amount=quantity,
                            price=entry["price"],
                            params={
                                'reduceOnly': False
                            }
                        )
                    else:
                        raise e

                orders.append(limit_order)
                current_position += quantity
            
            # Stop loss kontrolü
            if not self.validate_order_limits(symbol, current_position, stop_loss):
                logger.warning("Stop loss değeri limitlerin dışında, düzeltme gerekebilir")
            
            # Tüm pozisyon için tek bir stop-loss emri
            stop_order = self.exchange.create_order(
                symbol=symbol,
                type='STOP_MARKET',
                side='SELL' if side == 'BUY' else 'BUY',
                amount=current_position,
                params={
                    'stopPrice': stop_loss,
                    'closePosition': True,  # Pozisyonu tamamen kapat
                    'priceProtect': True,  # Fiyat koruması aktif
                    'workingType': 'MARK_PRICE',  # Mark fiyatını kullan
                    'autoClose': True  # Diğer emirleri otomatik iptal et
                }
            )
            orders.append(stop_order)
            
            # Take-profit kontrolü
            if not self.validate_order_limits(symbol, current_position, take_profit):
                logger.warning("Take profit değeri limitlerin dışında, düzeltme gerekebilir")
            
            # Take-profit emri (tüm pozisyon için)
            tp_order = self.exchange.create_order(
                symbol=symbol,
                type='TAKE_PROFIT_MARKET',
                side='SELL' if side == 'BUY' else 'BUY',
                amount=current_position,
                params={
                    'stopPrice': take_profit,
                    'closePosition': True,  # Pozisyonu tamamen kapat
                    'priceProtect': True,  # Fiyat koruması aktif
                    'workingType': 'MARK_PRICE',  # Mark fiyatını kullan
                    'autoClose': True  # Diğer emirleri otomatik iptal et
                }
            )
            orders.append(tp_order)
            
            logger.info(f"Kademeli pozisyon emirleri oluşturuldu:")
            logger.info(f"Margin Türü: {margin_type}")
            logger.info(f"Toplam pozisyon büyüklüğü: {current_position}")
            logger.info(f"Stop-loss seviyesi: {stop_loss}")
            logger.info(f"Take-profit seviyesi: {take_profit} (5. hedef)")
            
            return orders
            
        except Exception as e:
            logger.error(f"Kademeli pozisyon açma hatası: {e}")
            # Hata durumunda tüm emirleri iptal et
            self.cancel_all_orders(symbol)
            return None

    def close_position(self, symbol: str):
        try:
            position = self.exchange.fetch_position(symbol)
            if position['contracts'] > 0:
                side = 'SELL' if position['side'] == 'long' else 'BUY'
                self.exchange.create_order(
                    symbol=symbol,
                    type='MARKET',
                    side=side,
                    amount=position['contracts']
                )
                logger.info(f"Pozisyon kapatıldı: {symbol}")
                return True
            return False
        except Exception as e:
            logger.error(f"Pozisyon kapatma hatası: {str(e)}")
            return False

    def process_signal_file(self, signal_file: str):
        """Sinyal dosyasını oku ve işlem yap"""
        try:
            with open(signal_file, 'r', encoding='utf-8') as f:
                signal = json.load(f)
                
            symbol = signal['symbol']
            side = 'BUY' if signal['type'] == 'LONG' else 'SELL'
            
            # Açık pozisyon kontrolü
            open_positions = self.get_open_positions()
            for pos in open_positions:
                if pos['symbol'] == symbol:
                    logger.warning(f"DİKKAT: {symbol} için zaten açık bir pozisyon var!")
                    logger.warning(f"Mevcut pozisyon: {pos['side']}, Miktar: {pos['amount']}, Giriş: {pos['entryPrice']}")
                    logger.warning(f"Yeni sinyal: {side}, Hedef giriş: {signal['entries'][0]['price']}")
                    logger.warning("Mevcut pozisyonu kapatmadan yeni pozisyon açılmayacak.")
                    return None
            
            # Kaldıracı ayarla
            self.set_leverage_and_margin_type(symbol, leverage=20)
            
            # Take profit bilgisini al
            take_profit = signal['take_profit']
            
            # Kademeli pozisyon aç
            orders = self.open_staged_position(
                symbol=symbol,
                side=side,
                entries=[{
                    "price": entry["price"],
                    "risk_percentage": entry["risk_percentage"]
                } for entry in signal['entries']],
                stop_loss=signal['stop_loss'],
                take_profit=take_profit
            )
            
            if orders:
                logger.info(f"Kademeli pozisyon açıldı:")
                logger.info(f"Sembol: {symbol}")
                logger.info(f"Yön: {signal['type']}")
                for entry in signal['entries']:
                    logger.info(f"Seviye {entry['level']}: {entry['price']} ({entry['risk_percentage']}%)")
                logger.info(f"Stop: {signal['stop_loss']}")
                logger.info(f"Take-profit (5. hedef): {take_profit}")
                
                # İşlem başarılı olduğunda dosyayı işlenmiş olarak işaretle
                self.mark_signal_processed(signal_file)
                
            return orders
            
        except Exception as e:
            logger.error(f"Sinyal işleme hatası: {e}")
            return None

    def mark_signal_processed(self, signal_file: str):
        """Sinyal dosyasını işlenmiş olarak işaretle"""
        try:
            # Dosya adını değiştir
            processed_dir = os.path.join(os.path.dirname(signal_file), "processed")
            if not os.path.exists(processed_dir):
                os.makedirs(processed_dir)
                
            new_filename = f"processed_{os.path.basename(signal_file)}"
            new_path = os.path.join(processed_dir, new_filename)
            
            os.rename(signal_file, new_path)
            logger.info(f"Sinyal işlenmiş olarak işaretlendi: {new_path}")
            
        except Exception as e:
            logger.error(f"Sinyal işaretleme hatası: {e}")

    def get_unprocessed_signals(self) -> list:
        """İşlenmemiş sinyal dosyalarını getir"""
        try:
            signals_dir = "signals"
            if not os.path.exists(signals_dir):
                return []
                
            # İşlenmemiş sinyal dosyalarını bul
            signal_files = [f for f in os.listdir(signals_dir) 
                          if f.endswith('.json') and not f.startswith('processed_')]
            
            return [os.path.join(signals_dir, f) for f in signal_files]
            
        except Exception as e:
            logger.error(f"İşlenmemiş sinyalleri getirme hatası: {e}")
            return []

    def get_spot_balance(self) -> float:
        """Spot hesap bakiyesini al"""
        try:
            # Spot hesabı için farklı bir exchange nesnesi oluştur
            spot_exchange = ccxt.binance({
                'apiKey': BINANCE_API_KEY,
                'secret': BINANCE_API_SECRET,
                'enableRateLimit': True
            })
            
            balance = spot_exchange.fetch_balance()
            usdt_balance = balance['USDT']['free']
            return usdt_balance
        except Exception as e:
            logger.error(f"Spot bakiye alma hatası: {e}")
            return 0.0
            
    def get_open_positions(self):
        """Açık pozisyonları getir"""
        try:
            positions = self.exchange.fetch_positions()
            
            # Sadece açık pozisyonları filtrele (pozisyon büyüklüğü 0'dan farklı olanlar)
            open_positions = []
            for pos in positions:
                try:
                    amount = float(pos.get('contracts', '0'))
                    if amount == 0:  # Pozisyon yoksa atla
                        continue
                        
                    entry_price = float(pos.get('entryPrice', '0'))
                    mark_price = float(pos.get('markPrice', '0'))
                    unrealized_pnl = float(pos.get('unrealizedPnl', '0'))
                    
                    position_info = {
                        'symbol': pos.get('symbol', ''),
                        'side': 'BUY' if pos.get('side') == 'long' else 'SELL',
                        'amount': abs(amount),
                        'entryPrice': entry_price,
                        'markPrice': mark_price,
                        'unrealizedProfit': unrealized_pnl
                    }
                    open_positions.append(position_info)
                    logger.info(f"Açık pozisyon bulundu: {position_info}")
                    
                except (ValueError, KeyError) as e:
                    logger.warning(f"Pozisyon verisi ayrıştırma hatası, atlanıyor: {e}")
                    continue
            
            return open_positions
            
        except Exception as e:
            logger.error(f"Açık pozisyonları alma hatası: {e}")
            return [] 