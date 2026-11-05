# 0014: Ana model aşırı yüklenince yedek model

**Durum:** Kabul edildi (2026-11-05). ADR 0001'i (gemini-3.5-flash-lite) değiştirmez, tamamlar.

## Bağlam
2026-11-05'te canlı site hiç cevap veremedi: `gemini-3.5-flash-lite` tek kelimelik bir isteğe bile
`503 UNAVAILABLE` ("This model is currently experiencing high demand") döndü; her talep 40 saniye sonra
"Şu anda cevap veremiyoruz" ile bitti. Aynı anda `gemini-3.1-flash-lite` aynı isteğe 0,9 saniyede cevap
verdi. Sorun bizim kodumuz, anahtarımız veya kotamız değil, Google tarafında tek bir modelin yoğunluğuydu.

## Karar
`GeminiProvider(use_fallback=True)` yalnızca canlı API'de kullanılır. Ana modelin çağrısı aşırı
yüklenme nedeniyle başarısız olursa (429, 500, 503, 504 veya zaman aşımı) aynı istek bir kez
`GEMINI_FALLBACK_MODEL` ile tekrarlanır (canlıda `gemini-3.1-flash-lite`: kararlı, ücretsiz katmanda).
Her geçiş `gemini_fallback` uyarısıyla loglanır; her çağrının log satırı cevabı veren modeli yazar.
- 400 gibi istek hataları yedeğe geçmez: hata bizim isteğimizdedir, başka model düzeltmez ve görülmelidir.
- Eval'ler yedek kullanmaz (`use_fallback=False`): bir skor her zaman tek bir modeli ölçer.
- Karar kodu (`decision.py`) değişmez: yedek modelin cevabı da aynı kaynak ve alıntı kontrollerinden geçer.

## Sonuçlar
- Bir modelin yoğunluğu siteyi kapatmaz. İlk gerçek test: ana model iki adımda da 503 verdi, yedek
  9,8 saniyede doğru, kaynaklı GPA cevabını verdi (otomatik gönderildi).
- Risk: yedek modelin bizim taleplerimizdeki doğruluğu henüz ölçülmedi. Phase C model karşılaştırması
  (dev seti) onu da ölçecek; özellikle kaçırılan escalation sayısı.
- Kayıtlı talep hangi modelin cevapladığını saklamaz, yalnızca loglar yazar. Gerekirse ileride bir
  migration ile eklenir.

## Alternatifler
- Ana modeli tamamen `gemini-3.1-flash-lite` yapmak: bugün çalışır, ama ölçülmemiş bir modeli her talep
  için kullanmak olur. Reddedildi; karşılaştırmadan sonra yeniden değerlendirilir.
- Başka bir sağlayıcı (Groq'ta açık kaynak modeller): ücretsiz limit dakikada ~8.000 token, bir talep
  ~6.000-7.000 token kullanır; dakikada yaklaşık bir öğrenci. Ana yedek için çok dar.
- Daha uzun bekleyip tekrar denemek: 503 dakikalarca sürdü; öğrenci yine cevap alamazdı.
