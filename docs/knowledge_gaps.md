# Bilgi tabanı boşlukları (knowledge gaps)

Tarih: 2026-10-27. Kaynak: `eval/pipeline_results_dev.json` (yalnızca dev set, 80 ticket). Kilitli test
setlerine (`test_tickets.jsonl`, `phase8_tickets.jsonl`) bakılmadı.

## Neden bu belge
Dev setteki son pipeline eval'de 80 ticket'ın yalnızca 17'si otomatik cevaplandı. İnsana gitme
nedenlerinin en büyüğü `not_covered` oldu (56 ticket): model, getirilen (retrieved) belgelerde cevabı
bulamadı. Cevaplar tek tek okundu: model doğru davranmış, eksik olan bilgi tabanıydı (knowledge base).
Bilgi uydurmasına izin vermek yerine bilgi tabanı resmî BŞEÜ kaynaklarıyla büyütülür.

## Boşluklar ve resmî kaynakları
Escalation gerektirmeyen ve `not_covered` olan 39 dev ticket'tan, resmî bir kaynakta cevabı bulunanlar:

| Ticket | Eksik bilgi | Resmî kaynak | Eklenen yer |
|---|---|---|---|
| tr-021, en-023 | 2026-2027 katkı payı / öğrenim ücreti tutarları (yabancı uyruklu dahil) | Öğrenci İşleri duyurusu "Katkı Payı ve Öğrenim Ücretleri" (07.09.2026) ve ekleri | harc_ucretler |
| en-014 | Taksitle ödeme (yıllık tutar + güz taksiti) | aynı ücret tablosu | harc_ucretler |
| en-025 | Ödeme dekontu | Tahsilat Rehberi | harc_ucretler |
| tr-007 | Akademik izinde harç | ÖİDB SSS, Akademik İzin | harc_ucretler |
| en-019 | Diplomanın teslimi, mezuniyet tarihi | ÖİDB SSS, Mezuniyet İşlemleri | belgeler_hesaplar |
| en-040 | Transkript (e-Devlet, ıslak imzalı), diploma eki | 2025-2026 Oryantasyon Sunumu; ÖİDB SSS | belgeler_hesaplar |
| tr-011 | Danışmanın görevi ve onayı | Ön Lisans ve Lisans Eğitim-Öğretim Yönetmeliği Madde 6 | ders_kaydi |
| en-036 | Ön koşullu ders | Yönetmelik Madde 4 | ders_kaydi |
| tr-036 | Ders çakışması | Yönetmelik Madde 15 | ders_kaydi |
| en-021 | Öğretim dili | Yönetmelik Madde 14 | ders_kaydi |
| tr-006, en-028, tr-016 | UZEM girişi, teknik destek, şifre ve telefon doğrulama | UZEM Sıkça Sorulan Sorular | bilisim_hesaplar |
| en-009 | Kampüse ulaşım (otobüs hatları) | 2025-2026 Oryantasyon Sunumu | kampus_yasami |
| tr-010 | Engelli öğrencilere sınav düzenlemeleri | Engelli Öğrenciler Birim Koordinatörlüğü Yönergesi Madde 8 | engelli_ogrenciler (yeni) |
| tr-015 | Kütüphane salonlarının çalışma saatleri | Kütüphane, Çalışma Saatlerimiz | kampus_yasami |
| en-032 | Yemekhane saatleri | SKS, Beslenme Hizmetleri SSS | sks_hizmetleri (yeni) |
| tr-029 | Glutensiz / diyet yemek | SKS, Beslenme Hizmetleri SSS | sks_hizmetleri |
| tr-030 | Spor salonu ücreti ve saatleri | SKS, Spor Hizmetleri SSS, Tesisler, Fiyatlar | sks_hizmetleri |
| tr-019 | Konferans salonu talebi | SKS, Kültür Hizmetleri SSS ve Konferans Salonları | sks_hizmetleri |
| tr-038 | Mezun olunca öğrenci e-postası | Bilgi İşlem, E-posta Ayarları (Öğrenci) | bilisim_hesaplar |
| en-029 | E-posta kotası ve sınırları (olası neden) | Bilgi İşlem, E-posta Ayarları (Öğrenci) | bilisim_hesaplar |

## Resmî kaynağı bulunamayanlar (insana gitmeye devam eder)
Kayıp eşya, Office 365 lisansı, UZEM dosya boyutu sınırı, burs ödemesinin gecikmesi, hafta sonu
servis saatleri, İngilizce transkriptin hazırlanma süresi. Ayrıca bilgi tabanının hiçbir zaman cevaplayamayacağı
ticket'lar vardır: arıza bildirimi (yazıcı, projektör, Wi-Fi kopması), belirsiz ticket ("help",
"obs calismiyor") ve konu dışı sorular (hava durumu).

## Dürüst not
Eklenen bölümler dev setteki gerçek öğrenci sorularına bakılarak seçildi; bu yüzden dev setteki artış
biraz iyimser olacaktır. Asıl ölçü, kilitli setlerdeki son çalıştırmadır (yalnızca istendiğinde).
`expected_docs.jsonl` içindeki kilitli ticket'ların beklenen belgeleri bu adımda değiştirilmedi: yeni
bölümlerin kilitli ticket'ları cevaplayıp cevaplamadığı, son çalıştırmadan önce model çıktılarına
bakmadan ayrıca etiketlenmelidir.
