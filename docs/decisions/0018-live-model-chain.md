# 0018: Canlı API için model zinciri, hedged request ve süre sınırı

**Durum:** Kabul edildi (2026-11-14). ADR 0014'ün (tek yedek model) ve ADR 0015'in (canlı ana model
gemini-3.1-flash-lite) yerini alır. Eval'ler değişmez: hâlâ tek bir modeli (`GEMINI_MODEL`) ölçer.

## Bağlam
2026-11-14'te canlı site yine "Şu anda cevap veremiyoruz" dedi: `POST /api/tickets` 12,26 saniye sonra
503 döndü. Yerelde tekrarlandı: ana model (`gemini-3.1-flash-lite`) 12 saniyelik sınırı aştı, yedek
(`gemini-3.5-flash-lite`) o anda 503 "high demand" verdi; her modele tek şans vardı, öğrenci cevapsız kaldı.
Cevap gelse bile yavaştı.

Aynı gün gerçek classify + answer çağrılarıyla ölçüm (dev tarzı bir soru, kilitli setlerden değil):

| Model | Classify | Answer | Not |
|---|---|---|---|
| gemini-3.1-flash-lite | 3–16 sn | 16,8 sn'ye kadar, 504'ler | güvenilmez |
| gemini-3.5-flash-lite | 4–5 sn | ~6,6 sn | istikrarlı |
| gemini-4-hydrogen | 5,4 sn | 12,9 sn | çalışıyor |
| gemini-3.5-flash | 53 sn | 504 | kullanılamaz |
| gemini-3.8-flash | 99 sn sonra 503 | – | aşırı yüklü |

Google'ın fiyat sayfasında 3.1-flash-lite, 3.5-flash-lite ve gemini-4-hydrogen ücretsiz katmanda
listeleniyor (2026-11-14'te kontrol edildi). Model başına RPM/RPD sınırları yalnızca AI Studio'da görünür.

## Karar
Canlı API (`GeminiProvider(live=True)`) tek model yerine sıralı bir zincir kullanır:
`gemini_live_models` = `gemini-3.5-flash-lite`, `gemini-4-hydrogen`, `gemini-3.1-flash-lite`
(`core/settings.py`, `GEMINI_LIVE_MODELS` ile değiştirilebilir). Orkestrasyon `ai/resilience.py`'dedir
ve Gemini'den habersizdir, sahte modellerle test edilir.
- **Meşgul model işi hemen devreder:** 429/500/503/504, zaman aşımı, kopan veya kurulamayan bağlantı
  (`httpx.TransportError`; 2026-11-18'de eklendi), boş veya şemaya uymayan cevap gelirse sıradaki model
  beklemeden başlar.
- **Yavaş modele eşlik edilir (hedged request, Google'ın "The Tail at Scale" makalesi):** 9 saniye
  içinde cevap yoksa sıradaki model de başlar; ilk gelen cevap kazanır, diğeri yok sayılır.
- **Süre sınırı:** hiçbir öğrenci 25 saniyeden fazla beklemez; sonra 503 ve yalnızca hata türü loglanır.
- **Dinlenen modeller (circuit breaker):** hata veren veya yarışı kaybeden model 120 saniye boyunca
  sona alınır, ama son çare olarak yine sorulur.
- **400 gibi istek hataları devredilmez:** hata bizim isteğimizdedir, görülmelidir.
- **Embedding:** öğrencinin sorusunun embedding'i 8 saniye sınır ve 3 kısa denemeyle alınır
  (`embed_query`); bilgi tabanı indekslemesi sabırlı sınırları korur.

## Sonuçlar
- Yerel uçtan uca test (5 dev tarzı soru): 5/5 otomatik cevap, 3,6–7,1 sn; embedding ~0,5 sn. Ana model
  bilerek yavaş bir modele (`gemini-3.8-flash`) ayarlandığında hedge iki talebi de ~14 sn'de kurtardı;
  yarışı kaybeden modelin dinlendirilmesi bundan sonra eklendi, böylece sonraki talepler beklemez.
- Risk: canlıda cevabı hangi modelin verdiği değişebilir. Skorlar `gemini-3.5-flash-lite` ile ölçüldü
  (zincirin ilki); `gemini-4-hydrogen` dev setinde henüz ölçülmedi. Her cevap yine aynı kaynak, alıntı
  ve karar kontrollerinden (`decision.py`) geçer; log satırı cevabı veren modeli yazar.
- Hedge, yavaş anlarda bir talep için iki çağrı yapabilir: ücretsiz katmanın dakika sınırını biraz daha
  hızlı tüketir. Günlük talep sınırı (`DAILY_TICKET_CAP`) bunu sınırlar.
- Sağlık durumu süreç içinde tutulur (paylaşılan bellek yok): tek Render örneği için yeterli; birden
  çok örnekte her biri kendi durumunu öğrenir.

## Alternatifler
- Daha uzun tek zaman aşımı: yavaş anlarda öğrenci yine 30+ saniye bekler. Reddedildi.
- Tüm modellere aynı anda sormak: en hızlısı ama her talep kotayı 3 kat tüketir. Reddedildi.
- Ücretli bir model veya sağlayıcı: proje ücretsiz kalmalı. Reddedildi.
