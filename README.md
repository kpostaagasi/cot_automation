# BV Portföy CFTC COT Haftalık Rapor

Her Pazartesi 08:30'da (İstanbul) raporu üretir ve **onay beklemeden** `MAIL_TO` listesine yollar.

## Kurulum
1. Bu klasörü **private** bir GitHub reposuna yükle.
2. Gmail: Google Hesabı > Güvenlik > 2 Adımlı Doğrulama açık olmalı > "Uygulama şifreleri" > yeni şifre oluştur (16 hane).
3. Repo > Settings > Secrets and variables > Actions > New repository secret:
   - `SMTP_USER`: gmail adresin
   - `SMTP_PASS`: uygulama şifresi
   - `MAIL_TO`: alıcılar, virgülle (ör. `a@bvportfoy.com,b@bvportfoy.com`)
   - `MAIL_CC`: opsiyonel
4. Actions sekmesi > "CFTC COT Haftalık Rapor" > Run workflow ile test et. MAIL_TO'yu ilk testte sadece kendi adresin yap (mail doğrudan gider).

## Davranış
- Veri doğrulaması başarısızsa ekibe gitmez, sadece sana [HATA] maili gelir.
- Son COT haftası 11 günden eskiyse (CFTC gecikmesi) ekibe gitmez, sana [UYARI] gelir.
- Canlı fiyat alınamazsa sabit fiyat kullanılır ve mailde belirtilir.
- Gönderim saatini değiştirmek için `.github/workflows/cot_weekly.yml` içindeki cron'u düzenle (UTC).

## Lokal çalıştırma
    pip install -r requirements.txt
    SMTP_USER=... SMTP_PASS=... MAIL_TO=... python send_weekly.py prepare

## Akış
1. `prepare` raporu üretir, `out/` içine PDF + `mail.json` yazar; mail atmaz.
2. `send` aynı job içinde bu paketi ekibe yollar (rapor yeniden üretilmez).
3. `out/` klasörü her run'da artifact olarak 7 gün saklanır (gönderilen PDF'in arşivi).
