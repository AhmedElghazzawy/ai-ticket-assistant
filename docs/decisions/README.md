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
| [0008](0008-first-help-on-forwarded-tickets.md) | Yönlendirilen taleplerde güvenli "ön bilgi" (escalate edilenlerde asla) | Kabul edildi |
| [0009](0009-student-ticket-access-code.md) | Öğrencinin kendi talebi: gizli kod ile durum, personel cevabı ve geri bildirim | Kabul edildi |
| [0010](0010-prompt-injection-defence.md) | Prompt injection savunması: talebi çitle, alıntıyı kodla doğrula | Kabul edildi |
| [0011](0011-agent-instructions-and-guardrails.md) | Claude Code için tek, kısa talimat dosyası (CLAUDE.md), kurallar kod olarak (hook'lar) | Kabul edildi |
| [0012](0012-package-factory-llm-provider.md) | Katmanlı paket, app factory ve LLMProvider arayüzü | Kabul edildi |

Yeni bir önemli karar alındığında bir sonraki numarayla yeni dosya eklenir. Bir karar değişirse eski dosya silinmez: durumu "Yerini aldı: 00XX" olur.
