# BV Portföy CFTC COT Haftalık Rapor

Her Pazartesi 08:30'da (İstanbul) raporu üretir, önizlemeyi sana yollar. Ekibe gönderim SENİN ONAYINLA olur.

## Kurulum
1. Bu klasörü **private** bir GitHub reposuna yükle.
2. Gmail: Google Hesabı > Güvenlik > 2 Adımlı Doğrulama açık olmalı > "Uygulama şifreleri" > yeni şifre oluştur (16 hane).
3. Repo > Settings > Secrets and variables > Actions > New repository secret:
   - `SMTP_USER`: gmail adresin
   - `SMTP_PASS`: uygulama şifresi
   - `MAIL_TO`: alıcılar, virgülle (ör. `a@bvportfoy.com,b@bvportfoy.com`)
   - `MAIL_CC`: opsiyonel
4. Repo > Settings > Environments > New environment: `ekip-gonderim` > Required reviewers: kendi GitHub kullanıcın > Save.
5. Actions sekmesi > "CFTC COT Haftalık Rapor" > Run workflow ile test et. MAIL_TO'yu ilk testte sadece kendi adresin yap.

## Davranış
- Veri doğrulaması başarısızsa ekibe gitmez, sadece sana [HATA] maili gelir.
- Son COT haftası 11 günden eskiyse (CFTC gecikmesi) ekibe gitmez, sana [UYARI] gelir.
- Canlı fiyat alınamazsa sabit fiyat kullanılır ve mailde belirtilir.
- Gönderim saatini değiştirmek için `.github/workflows/cot_weekly.yml` içindeki cron'u düzenle (UTC).

## Lokal çalıştırma
    pip install -r requirements.txt
    SMTP_USER=... SMTP_PASS=... MAIL_TO=... python send_weekly.py

## Onay akışı
1. `prepare` job raporu üretir, sana `[ONAY BEKLİYOR]` konulu önizleme maili atar (PDF ekli, alıcı listesi görünür).
2. GitHub da "review pending" bildirimi gönderir. Mail içindeki linke tıkla > Review deployments.
3. **Approve**: aynı PDF ve aynı metin ekibe gider (yeniden üretilmez). **Reject**: hiçbir şey gitmez.
4. Onay verilmezse iş 30 gün sonra kendiliğinden düşer.

Not: Private repoda Environment reviewer için GitHub Pro gerekir (GitHub Student Developer Pack ile ücretsiz).
