# 0011: Claude Code için tek, kısa talimat dosyası ve kod olarak korumalar

**Durum:** Kabul edildi (2026-10-24).

## Bağlam
Proje terminalde Claude Code ile geliştiriliyor (seçilen araç budur; Codex kullanılmıyor). Kurallar 20 KB'lık tek bir CLAUDE.md dosyasındaydı ve AGENTS.md onun Codex için elle tutulan bir kopyasıydı: iki dosya her değişiklikte aynı şekilde güncellenmeliydi. Dosya kuralları, yol haritasını, proje tasarımını ve durum notlarını karıştırıyordu; Claude her oturumda hepsini okuyordu. En önemli kurallar (".env asla okunmaz", "kilitli test setleri değiştirilmez") yalnızca yazılı bir ricaydı: unutulursa onu durduran bir şey yoktu.

## Karar
1. **Tek dosya:** bütün kurallar CLAUDE.md'de. Kullanılmayan bir araç için tutulan kopya (AGENTS.md) kaldırıldı.
2. **Kısa talimat, ayrıntı bağlantıda:** yol haritası ve durum `docs/ROADMAP.md`'ye, kurs ve tasarım bilgisi `docs/PROJECT_BRIEF.md`'ye, mimari `ARCHITECTURE.md`'ye taşındı (metinler değiştirilmeden). Claude bunları görev gerektirdiğinde okur. CLAUDE.md'ye açık bir çalışma döngüsü (keşfet, planla, önce test, uygula, doğrula, kaydet, gönder) ve "bitti" tanımı eklendi.
3. **Kurallar kod olarak (`.claude/`):** `settings.json` `.env` dosyasını okumayı ve kilitli setleri düzenlemeyi reddeder; `hooks/guard_files.py` her araç çağrısından önce çalışır ve `.env`'e dokunan ya da kilitli seti değiştiren komutları engeller (tests/test_guard_files.py ile test edilir). Bulut oturumlarında `hooks/session_start.sh` testler için Postgres + pgvector başlatır.
4. **Tekrarlanan işler skill olarak:** quality-gate, teach-step, run-evals, new-adr, add-api-endpoint, db-migration. **Dar görevli alt ajanlar:** code-reviewer, test-writer, eval-analyst, security-auditor (çoğu salt okunur).

## Sonuçlar
- Kurallar tek yerde; Claude her oturumda daha az ama daha önemli metin okur.
- En tehlikeli iki hata (anahtarın sızması, kilitli sete dokunulması) artık dikkate bağlı değil, kodla engelleniyor.
- Hook bir korkuluktur, güvenlik sınırı değildir: shell komutlarını desenle tanır, her olası yazma yolunu yakalayamaz. Asıl koruma hâlâ `.gitignore`, kod incelemesi ve CI'dır.
- Öğretme modu (teaching mode) aynen korunur; adımları ayrıca bir skill olarak da yazıldı.
- İleride başka bir ajan kullanılırsa, tek satırlık bir AGENTS.md ("kurallar CLAUDE.md'de") yeterlidir.

## Alternatifler
- İki dosyayı elle senkron tutmak (eski durum): unutulması kolay ve kullanılmayan bir araç için emek.
- AGENTS.md'yi ana dosya yapıp CLAUDE.md'den `@AGENTS.md` ile içe aktarmak (bu PR'ın ilk hâli): birden çok ajan kullanan ekipler için iyi; yalnızca Claude Code kullanan bu projede gereksiz bir dolaylılık.
- Hiç hook kullanmamak, yalnızca izin listesine güvenmek: izin kuralları `cat .env` gibi shell komutlarını tam kapsamaz.
