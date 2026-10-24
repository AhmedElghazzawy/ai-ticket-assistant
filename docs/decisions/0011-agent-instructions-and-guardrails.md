# 0011: Kodlama ajanları için tek talimat dosyası ve kod olarak korumalar

**Durum:** Kabul edildi (2026-10-24).

## Bağlam
Proje bir kodlama ajanıyla (Claude Code, bazen Codex) geliştiriliyor. Kurallar 20 KB'lık tek bir CLAUDE.md dosyasındaydı ve AGENTS.md onun elle tutulan bir kopyasıydı: iki dosya her değişiklikte aynı şekilde güncellenmeliydi. Dosya kuralları, yol haritasını, proje tasarımını ve durum notlarını karıştırıyordu; ajan her oturumda hepsini okuyordu. En önemli kurallar (".env asla okunmaz", "kilitli test setleri değiştirilmez") yalnızca yazılı bir ricaydı: ajan unutursa onu durduran bir şey yoktu.

## Karar
1. **Tek kaynak:** AGENTS.md (birçok ajanın okuduğu açık standart) bütün kuralları tutar. CLAUDE.md yalnızca `@AGENTS.md` ile onu içe aktarır ve Claude Code'a özgü araçları listeler. Kopya kalmaz.
2. **Kısa talimat, ayrıntı bağlantıda:** yol haritası ve durum `docs/ROADMAP.md`'ye, kurs ve tasarım bilgisi `docs/PROJECT_BRIEF.md`'ye, mimari `ARCHITECTURE.md`'ye taşındı (metinler değiştirilmeden). Ajan bunları görev gerektirdiğinde okur.
3. **Kurallar kod olarak (`.claude/`):** `settings.json` `.env` dosyasını okumayı ve kilitli setleri düzenlemeyi reddeder; `hooks/guard_files.py` her araç çağrısından önce çalışır ve `.env`'e dokunan ya da kilitli seti değiştiren komutları engeller (tests/test_guard_files.py ile test edilir). Bulut oturumlarında `hooks/session_start.sh` testler için Postgres + pgvector başlatır.
4. **Tekrarlanan işler skill olarak:** quality-gate, teach-step, run-evals, new-adr, add-api-endpoint, db-migration. **Dar görevli alt ajanlar:** code-reviewer, test-writer, eval-analyst, security-auditor (çoğu salt okunur).

## Sonuçlar
- Kurallar tek yerde; ajan her oturumda daha az ama daha önemli metin okur.
- En tehlikeli iki hata (anahtarın sızması, kilitli sete dokunulması) artık ajanın dikkatine bağlı değil, kodla engelleniyor.
- Hook bir korkuluktur, güvenlik sınırı değildir: shell komutlarını desenle tanır, her olası yazma yolunu yakalayamaz. Asıl koruma hâlâ `.gitignore`, kod incelemesi ve CI'dır.
- Öğretme modu (teaching mode) aynen korunur; yalnızca adımları ayrıca bir skill olarak da yazıldı.

## Alternatifler
- İki dosyayı elle senkron tutmak (eski durum): unutulması kolay, aradaki farklar zaten küçük sapmalar göstermişti.
- AGENTS.md'yi CLAUDE.md'ye sembolik bağlantı yapmak: Windows'ta ve bazı araçlarda bozulur; `@` içe aktarma Claude Code'un belgelenmiş yoludur.
- Hiç hook kullanmamak, yalnızca izin listesine güvenmek: izin kuralları `cat .env` gibi shell komutlarını tam kapsamaz.
