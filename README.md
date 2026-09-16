# BV Portföy CFTC COT Haftalık Rapor

Her Pazartesi 09:00'da (İstanbul) raporu üretir, önizlemeyi sana yollar. Ekibe gönderim SENİN ONAYINLA olur.

## Kurulum
1. Bu klasörü **private** bir GitHub reposuna yükle.
2. Gmail: Google Hesabı > Güvenlik > 2 Adımlı Doğrulama açık olmalı > "Uygulama şifreleri" > yeni şifre oluştur (16 hane).
3. Repo > Settings > Secrets and variables > Actions > New repository secret:
   - `SMTP_USER`: gmail adresin
   - `SMTP_PASS`: uygulama şifresi
   - `MAIL_TO`: alıcılar, virgülle (ör. `a@bvportfoy.com,b@bvportfoy.com`)
   - `MAIL_CC`: opsiyonel
4. Actions sekmesi > "1 - COT Rapor Hazırla" > Run workflow ile test et. MAIL_TO'yu ilk testte sadece kendi adresin yap.

## Davranış
- Veri doğrulaması başarısızsa ekibe gitmez, sadece sana [HATA] maili gelir.
- Son COT haftası 11 günden eskiyse (CFTC gecikmesi) ekibe gitmez, sana [UYARI] gelir.
- Canlı fiyat alınamazsa sabit fiyat kullanılır ve mailde belirtilir.
- Gönderim saatini değiştirmek için `.github/workflows/cot_1_hazirla.yml` içindeki cron'u düzenle (UTC).

## Lokal çalıştırma
    pip install -r requirements.txt
    SMTP_USER=... SMTP_PASS=... MAIL_TO=... python send_weekly.py prepare

## Onay akışı
1. `1 - COT Rapor Hazırla` (Pazartesi 09:00 veya manuel) raporu üretir, `out/` paketini artifact olarak yükler ve sana `[ONAY BEKLİYOR]` konulu önizleme maili atar (PDF ekli, alıcı listesi görünür).
2. Onaylıyorsan maildeki linke tıkla > `2 - COT Ekibe Gönder (ONAY)` > Run workflow. Aynı PDF ve aynı metin ekibe gider, rapor yeniden üretilmez.
3. Onaylamıyorsan hiçbir şey yapma; paket 7 gün sonra artifact ile birlikte düşer.
4. `run_id` alanı boş bırakılırsa en son **başarılı** hazırlık run'ının paketi gönderilir; eski bir paketi göndermek için run id gir.
