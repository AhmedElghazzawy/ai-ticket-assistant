# 0001: LLM olarak Gemini Flash-Lite

**Durum:** Kabul edildi (2026-10-06). Phase 9'da yeniden değerlendirilecek.

## Bağlam
Sistem iki yerde LLM kullanır: talebi sınıflandırmak ve kaynaklı cevap yazmak. Gereksinimler: iyi Türkçe, JSON şemasına uyan çıktı (structured output), aynı sağlayıcıdan embedding, öğrenci projesi için ücretsiz katman. İlk seçilen `gemini-3.8-flash`, ücretsiz katmanda günde yaklaşık 20 istekle sınırlıydı; 80 talebi iki kez değerlendirmek mümkün değildi.

## Karar
- Model: `gemini-3.5-flash-lite`, her yerde aynı model (değerlendirme skoru, uygulamanın gerçekte yaptığıyla aynı olsun). Model adı `.env` içinde (`GEMINI_MODEL`), kod değişmeden değişir.
- **Structured output:** model yalnızca bizim şemamıza uyan JSON döndürebilir; geçersiz kategori imkânsızdır.
- **`reason` alanı önce:** model önce gerekçesini yazar, sonra etiketleri seçer.
- **Temperature 1.0 (varsayılan):** Google'ın resmî Gemini 3 önerisi; daha düşük değerler döngüye veya kaliteye zarar verebilir. Tutarlılık structured output ve net kurallardan gelir; iki çalıştırmayla ölçülür.
- **Thinking `high`:** `low` ile 80 dev talebinde karşılaştırıldı; üçü de doğru %70,6 → %84,4, öncelik tutarlılığı %89 → %96.

## Sonuçlar
- Ücretsiz ve hızlı; Türkçe ve İngilizce iyi.
- Flash-Lite en küçük model ailesidir; daha büyük bir model daha iyi olabilir. `low`/`high` karşılaştırması dev setinde yapıldı, bu yüzden kilitli test seti ayrıca ölçüldü.
- Kişisel veri Google'a gider; KVKK açısından gerçek bir üniversite kurulumunda yerinde (on-premise) bir model gerekebilir.

## Alternatifler
- Daha büyük Gemini, Claude, GPT, açık ağırlıklı bir model: Phase 9'da aynı kilitli test üzerinde doğruluk, kaçırılan escalation, 1.000 talep başına maliyet ve gecikmeye göre karşılaştırılacak.
- Düşük temperature: Google'ın Gemini 3 önerisine aykırı olduğu için seçilmedi.
