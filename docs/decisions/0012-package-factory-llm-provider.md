# 0012: Katmanlı paket, app factory ve LLMProvider arayüzü

**Durum:** Kabul edildi (2026-10-24).

## Bağlam
Backend `src/` altında düz modüllerdi ve yalnızca `pythonpath = ["src"]` sayesinde import ediliyordu. `api.py` 551 satırdı; ayarlar altı yerde `os.getenv` ile okunuyordu; testler modül değişkenlerini (pool, limitler, DEMO_MODE) monkeypatch ile değiştiriyordu; Gemini sınıflandırıcıya ve cevap adımına doğrudan bağlıydı, bu yüzden yol haritasındaki model karşılaştırması (madde 9) kod değişikliği gerektirirdi.

## Karar
1. **Paket:** `src/helpdesk/` (core, domain, ai, retrieval, storage, api, evals); katmanlar yalnızca içe doğru bağımlıdır. Modelin çıktı şemaları `domain/outputs.py`'de, böylece karar kodu yapay zekâ katmanını import etmez.
2. **Tek ayar modülü:** `core/settings.py` (`AppSettings`, `GeminiSettings`); başka hiçbir yerde ortam değişkeni okunmaz; hatalı değer uygulamayı başlangıçta durdurur.
3. **App factory:** `api/app.py::create_app()`; uygulamanın servisleri (`api/deps.py::Services`) dependency injection ile verilir; her test kendi uygulamasını kurar.
4. **LLMProvider (`ai/provider.py`):** tek metot, `generate_json`. Gemini bunun bir uygulamasıdır (`ai/gemini.py::GeminiProvider`). Embedding modeli bu arayüzün dışında kalır (indeksin parçasıdır).

## Sonuçlar
- Davranış aynı: API şeması byte düzeyinde aynı; Gemini'ye giden istekler (prompt, şema, ayarlar, içerik) eski kodla byte düzeyinde karşılaştırıldı, aynı. 188 test, kapsam %83.
- Başka bir model yalnızca bir sınıf yazarak denenebilir; promptlar ve karar değişmez.
- macOS'ta `.venv` dosyalarının "hidden" işaretlenmesi yüzünden editable kurulum görülmeyebilir; testler, mypy ve Makefile `src/` yolunu ayrıca verir.

## Alternatifler
- Düz modüllerde kalmak: çalışıyordu, ama globaller ve dağınık ayarlar her yeni özellikle büyüyecekti.
- LangChain gibi bir soyutlama: tek metotluk ihtiyaç için ağır bir bağımlılık.
