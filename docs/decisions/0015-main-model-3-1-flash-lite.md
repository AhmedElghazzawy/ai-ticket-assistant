# 0015: Canlı ana model gemini-3.1-flash-lite

**Durum:** Kabul edildi (2026-11-05). ADR 0001'in canlı model seçimini değiştirir; ADR 0014'teki
yedek mekanizması aynen kalır, yalnızca iki modelin yeri değişir.

## Bağlam
2026-11-05'te `gemini-3.5-flash-lite` saatlerce `503 high demand` döndü. Yedek model (ADR 0014) siteyi
ayakta tuttu, ama her uyanışta (Render'ın ücretsiz planı uyuyor) ilk talep önce ana modeli bekledi:
canlıda bir cevap 70 saniye sürdü. Yedek modelin doğruluğu da henüz ölçülmemişti.

## Ölçüm (classifier, dev seti, 80 talep, 1 run; kilitli setler kullanılmadı)
| Model | n | Üç etiket birden (95% CI) | Kaçırılan escalation | Gereksiz escalation | Hız |
|---|---|---|---|---|---|
| gemini-3.5-flash-lite (2026-10-09) | 80 | %83,8 | 0 | 3 | bugün 503 |
| gemini-3.1-flash-lite | 80 | %80,0 (%70-%87) | 0 | 4 | çağrı başına 2-4 sn, hata yok |
| gemini-3.6-flash | 12 | ölçülemedi | - | - | çağrı başına ~20 sn; 12. talepte ücretsiz günlük kota (429) bitti |

Sonuç dosyası: `eval/results_high_gemini-3.1-flash-lite.json`. 3.6-flash'ın yarım sonucu (n=12) bir
skor gibi okunmasın diye saklanmadı.

## Karar
`render.yaml`: `GEMINI_MODEL=gemini-3.1-flash-lite`, `GEMINI_FALLBACK_MODEL=gemini-3.5-flash-lite`.
Koddaki yedek varsayılanı (`gemini-3.1-flash-lite`) bilerek değişmedi: Render panosu `render.yaml`'ı
almazsa ana model eski haliyle 3.5 kalır ve yedek yine farklı bir model olur; site bugünkü gibi çalışır.

## Sonuçlar
- Canlı cevaplar hızlı ve kararlı bir modelden gelir; güvenlik kuralı (0 kaçırılan escalation) korunur.
- Dürüst sınır: farklar güven aralıkları içinde; 80 talep iki modeli ayırt etmeye yetmez. Tek run,
  run'lar arası gürültü ölçülmedi. Pipeline eval'i (cevap kalitesi) 3.1-flash-lite ile ayrıca koşulmalı.
- README ve eski skorlar 3.5-flash-lite ile ölçüldü; o sonuçlar o modele aittir.

## Alternatifler
- gemini-3.6-flash / 3.8-flash: daha güçlü olabilir ama bugün biri çok yavaş ve günlük kotası düşük,
  diğeri 503. Canlı demo için uygun değil.
- Ollama ile açık model: Render'ın ücretsiz planında (512 MB RAM, GPU yok) çalışmaz.
- Groq'taki açık modeller: ücretsiz limit dakikada ~8.000 token, bir talep ~6.000-7.000 token.
