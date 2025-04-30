# SignalSage - Akıllı Kripto Sinyal Botu 🤖

SignalSage, Telegram kanallarından gelen kripto para sinyallerini otomatik olarak işleyen ve Binance Futures hesabınızda pozisyon açan/kapatan gelişmiş bir trading botudur.

## 🌟 Özellikler

### 📊 Trading Özellikleri
- Otomatik LONG ve SHORT pozisyon açma/kapama
- Akıllı risk yönetimi ve pozisyon büyüklüğü hesaplama
- Stop-loss ve take-profit emirlerinin otomatik yerleştirilmesi
- Trailing stop desteği
- Çoklu coin desteği
- Risk çarpanı ayarlama

### 🤖 Telegram Entegrasyonu
- Telegram kanallarından sinyal okuma
- Özel sinyal formatı desteği
- Otomatik sinyal ayrıştırma
- İşlem bildirimleri
- Hata ve uyarı mesajları

### 📈 Binance Futures Entegrasyonu
- USDT-M ve COIN-M vadeli işlemler desteği
- Kaldıraç ayarlama
- Margin türü seçimi (Isolated/Cross)
- Emir türleri (Market, Limit)
- Pozisyon modu ayarları

### 📝 Loglama ve İzleme
- Detaylı işlem logları
- Telegram bildirimleri
- Hata raporlama
- Performans metrikleri

## 🚀 Kurulum

### 1. Gereksinimler
- Python 3.8 veya üzeri
- Binance Futures hesabı
- Telegram bot token'ı
- Telegram kanal erişimi

### 2. Paket Kurulumu
```bash
# Projeyi klonlayın
git clone https://github.com/yourusername/SignalSage.git
cd SignalSage

# Gerekli paketleri yükleyin
pip install -r requirements.txt
```

### 3. Yapılandırma
`.env` dosyasını oluşturun ve aşağıdaki değişkenleri ayarlayın:
```env
# Binance API Bilgileri
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# Telegram Bilgileri
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL_ID=your_channel_id

# Trading Ayarları
RISK_MULTIPLIER=1.3
DEFAULT_LEVERAGE=20
MARGIN_TYPE=isolated
```

### 4. Risk Ayarları
`risk_settings.json` dosyasında risk çarpanını ayarlayabilirsiniz:
```json
{
    "risk_multiplier": 1.3
}
```

## 📋 Sinyal Formatı

Bot aşağıdaki formattaki sinyalleri işleyebilir:

```
LONG BTCUSDT Entry: 50000 SL: 49000 TP: 52000
SHORT BTCUSDT Entry: 50000 SL: 51000 TP: 48000
```

### Sinyal Parametreleri
- `LONG/SHORT`: İşlem yönü
- `BTCUSDT`: Trading çifti
- `Entry`: Giriş fiyatı
- `SL`: Stop-loss seviyesi
- `TP`: Take-profit seviyesi

## ⚙️ Komutlar

Bot aşağıdaki komutları destekler:
- `/start` - Botu başlatır
- `/stop` - Botu durdurur
- `/status` - Mevcut durumu gösterir
- `/settings` - Ayarları gösterir
- `/help` - Yardım menüsünü gösterir

## 🔒 Güvenlik

- API anahtarlarınızı güvende tutun
- `.env` dosyasını asla paylaşmayın
- Sadece güvenilir kanallardan gelen sinyalleri kullanın
- Risk yönetimi ayarlarını dikkatli yapılandırın
- Test ortamında deneyin

## ⚠️ Uyarılar

- Kripto para ticareti yüksek risk içerir
- Sadece kaybetmeyi göze alabileceğiniz miktarla işlem yapın
- Bot kullanımından doğacak kayıplardan sorumlu değiliz
- Her zaman risk yönetimi kurallarına uyun

## 🤝 Katkıda Bulunma

1. Fork'layın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'feat: Add amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun
