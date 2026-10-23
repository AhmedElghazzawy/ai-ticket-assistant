# 0009: Öğrencinin kendi talebi: gizli kod ile durum ve geri bildirim

**Durum:** Kabul edildi (2026-10-23).

## Bağlam
Personelin cevabı kaydediliyordu ama öğrenciye hiç ulaşmıyordu; öğrenci talebinin durumunu göremiyordu. Ayrıca "Bu cevap işinize yaradı mı?" düğmeleri hiçbir şey kaydetmiyordu. Öğrenci hesabı (giriş) yoktur; yalnızca talep numarası ile erişim olsaydı, numarayı tahmin eden biri başkasının talebini okuyabilir veya ona geri bildirim verebilirdi.

## Karar
- Her talep gönderildiğinde rastgele bir **gizli kod** (128 bit) üretilir ve öğrenciye **bir kez** gösterilir. Veritabanında yalnızca kodun SHA-256 özeti saklanır (personel oturumlarıyla aynı yöntem).
- Tarayıcı, öğrencinin taleplerini ve kodlarını yalnızca kendi içinde hatırlar ("Taleplerim" sayfası); öğrenci kodu elle kopyalamak zorunda kalmaz.
- `POST /api/tickets/lookup` (numara + kod): durum ve öğrenciye gönderilmiş cevap (otomatik cevap veya personelin cevabı). Kontrol edilmemiş taslak asla gösterilmez. Kod adreste değil gövdede gönderilir, böylece sunucu loglarına girmez.
- `POST /api/tickets/{id}/feedback` (kod + evet/hayır): son seçim geçerlidir.
- Yanlış kod ile var olmayan numara **aynı** 404 cevabını alır: hangi numaraların var olduğu anlaşılamaz. Her iki uç nokta da ziyaretçi başına dakikada 30 istekle sınırlıdır (yapay zekâ maliyeti yok, ama sınırsız da değil).

## Sonuçlar
- Personelin cevabı öğrenciye ulaşır (e-posta olmadan); geri bildirim istatistiklerde kullanılabilir.
- Öğrenci tarayıcı verilerini silerse veya başka bir cihaz kullanırsa eski taleplerini göremez. Gerçek bir kurulumda üniversitenin tek oturum açma (SSO) sistemi veya e-posta bildirimi bunu çözer.
- Bu karardan önceki talepler için kod yoktur; onlar öğrenci tarafından görüntülenemez.

## Alternatifler
- Yalnızca talep numarası: tahmin edilebilir, başkasının talebi okunabilirdi. Reddedildi.
- Öğrenci hesabı ve girişi: daha güçlü ama bu prototip için ağır; gerçek kurulumda SSO önerilir.
- E-posta ile cevap: e-posta adresi kişisel veridir ve bir e-posta servisi gerektirir; ileride değerlendirilecek.
