# Karar kayıtları (Architecture Decision Records)

Projedeki önemli seçimler, her biri kısa bir dosyada: bağlam, karar, sonuçlar ve düşünülen alternatifler. Amaç: "neden böyle yapıldı?" sorusunun cevabı koddan değil, buradan okunabilsin.

| No | Karar | Durum |
|---|---|---|
| [0001](0001-llm-gemini-flash-lite.md) | LLM: Gemini Flash-Lite, structured output, temperature 1.0, thinking `high` | Kabul edildi |
| [0002](0002-decision-is-plain-code.md) | Otomatik gönderim kararı yapay zekâ değil, sade kod; 6 kontrolün hepsi geçmeli | Kabul edildi |
| [0003](0003-locked-test-set.md) | Kilitli test seti: prompt ayarında asla kullanılmaz | Kabul edildi |
| [0004](0004-postgres-pgvector.md) | Talepler ve belge arama için Postgres + pgvector (SQLite ve bellek içi arama yerine) | Kabul edildi |
| [0005](0005-hosting-render-neon.md) | Barındırma: Render (ücretsiz, Frankfurt) + Neon (ücretsiz Postgres) | Kabul edildi |
| [0006](0006-demo-mode-keeps-login.md) | Personel girişi kalır; herkese açık deneme için ayrı demo modu | Kabul edildi |
| [0007](0007-client-ip-header.md) | Rate limit için ziyaretçi adresi: yalnızca güvenilen proxy başlığı | Kabul edildi |

Yeni bir önemli karar alındığında bir sonraki numarayla yeni dosya eklenir. Bir karar değişirse eski dosya silinmez: durumu "Yerini aldı: 00XX" olur.
