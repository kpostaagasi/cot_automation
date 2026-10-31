# BV Portföy CFTC COT Haftalık Rapor

CFTC Commitments of Traders (COT) verisinden haftalık PDF rapor üreten ve onayla ekibe gönderen otomasyon.

Her Pazartesi 09:00'da (İstanbul) rapor hazırlanır ve önizlemesi onaylayan kişiye gider. Rapor, onay verilmeden ekibe gitmez.

**Teknoloji:** Python, GitHub Actions, cron-job.org

## Onay akışı
1. `1 - COT Rapor Hazırla` (Pazartesi 09:00 veya manuel) raporu üretir, `out/` paketini artifact olarak yükler ve sana `[ONAY BEKLİYOR]` konulu önizleme maili atar (PDF ekli, alıcı listesi görünür).
2. Onaylıyorsan maildeki linke tıkla > `2 - COT Ekibe Gönder (ONAY)` > Run workflow. Aynı PDF ve aynı metin ekibe gider, rapor yeniden üretilmez.
3. Onaylamıyorsan hiçbir şey yapma; paket 7 gün sonra artifact ile birlikte düşer.
4. `run_id` alanı boş bırakılırsa en son **başarılı** hazırlık run'ının paketi gönderilir; eski bir paketi göndermek için run id gir.

## Davranış
- Veri doğrulaması başarısızsa ekibe gitmez, sadece sana [HATA] maili gelir.
- Son COT haftası 11 günden eskiyse (CFTC gecikmesi) ekibe gitmez, sana [UYARI] gelir.
- Canlı fiyat alınamazsa sabit fiyat kullanılır ve mailde belirtilir.
- Loglara e-posta adresi yazılmaz (public repoda Actions logları herkese açıktır).
- Zamanlama cron-job.org'dadır (Pazartesi 09:00 İstanbul, `workflow_dispatch`). Saati değiştirmek için oradaki işi düzenle. GitHub schedule'ı bu hesapta 4-6 saat geciktiği için kullanılmıyor.

## Kurulum
1. Bu klasörü bir GitHub reposuna yükle (public veya private).
2. Gmail: Google Hesabı > Güvenlik > 2 Adımlı Doğrulama açık olmalı > "Uygulama şifreleri" > yeni şifre oluştur (16 hane).
3. Repo > Settings > Secrets and variables > Actions > New repository secret:
   - `SMTP_USER`: gmail adresin
   - `SMTP_PASS`: uygulama şifresi
   - `MAIL_TO`: alıcılar, virgülle (ör. `a@bvportfoy.com,b@bvportfoy.com`)
   - `MAIL_CC`: opsiyonel
   - `PACKAGE_KEY`: uzun rastgele bir parola (ör. `openssl rand -base64 32`). Hazırlanan paket artifact'e bu anahtarla şifreli yüklenir; public repoda artifact'leri herkes indirebildiği için zorunludur.
4. Actions sekmesi > "1 - COT Rapor Hazırla" > Run workflow ile test et. MAIL_TO'yu ilk testte sadece kendi adresin yap.
5. cron-job.org'da Pazartesi 09:00 (İstanbul) için `cot_1_hazirla.yml` `workflow_dispatch` çağrısı tanımla.

## Lokal çalıştırma
    pip install -r requirements.txt
    SMTP_USER=... SMTP_PASS=... MAIL_TO=... python send_weekly.py prepare

## Lisans
Kod MIT lisanslıdır (bkz. `LICENSE`). `bv_logo_white.png` ve BV Portföy adı/markası lisans kapsamında değildir.
