# BŞEÜ Yardım Masası Ticket Asistanı

[![CI](https://github.com/AhmedElghazzawy/ai-ticket-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/AhmedElghazzawy/ai-ticket-assistant/actions/workflows/ci.yml)
[![CodeQL](https://github.com/AhmedElghazzawy/ai-ticket-assistant/actions/workflows/codeql.yml/badge.svg)](https://github.com/AhmedElghazzawy/ai-ticket-assistant/actions/workflows/codeql.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/AhmedElghazzawy/ai-ticket-assistant/badges/coverage.json)](https://github.com/AhmedElghazzawy/ai-ticket-assistant/actions/workflows/ci.yml?query=branch%3Amain)
![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Canlı demo](https://img.shields.io/badge/demo-canl%C4%B1-c8102e)](https://bseu-helpdesk.onrender.com)

🇬🇧 [English](README.md)

**Resmî belgelerden, doğrulanmış kaynaklarla cevap veren bir öğrenci yardım masası; bir insanın ne
zaman devralacağına model değil, testli kod karar verir.**

Üniversite yardım masası için bir AI asistanı. Öğrencinin yazdığı talebi (ticket, Türkçe veya
İngilizce) okur, etiketler, cevabı üniversitenin resmî belgelerinde arar (RAG), kaynağını gösteren bir
taslak cevap yazar ve ardından sade, testli kodla karar verir: cevabı **otomatik göndermek** mi, yoksa
talebi taslakla birlikte **doğru birime yönlendirmek** mi.

**Canlı demo:** https://bseu-helpdesk.onrender.com: öğrenci olarak bir soru yazın veya `/staff` →
**Demo olarak dene** ile personel panelini örnek taleplerle açın (ücretsiz sunucu: bir süre ziyaretçi
olmazsa ilk açılış yaklaşık 1 dakika sürer).

> Bilecik Şeyh Edebali Üniversitesi (BŞEÜ) Bilgisayar Mühendisliği öğrencisinin kişisel projesidir;
> **BŞEÜ'nün resmî bir hizmeti değildir.** Renkler bilecik.edu.tr'nin stil dosyasından alınmıştır,
> resmî logo kullanılmaz.

![Başlangıç ekranı](docs/images/student_home.jpg)

## Öne çıkanlar

- **Önce güvenlik:** 40 gerçekçi talepten oluşan kilitli sette, insana gitmesi gereken **11 talepten
  hiçbiri kaçırılmadı** ve gönderilmemesi gereken **hiçbir cevap otomatik gönderilmedi** (2026-10-23
  ölçümü; o zamandan beri değişenler için [Sonuçlar](#sonuçlar)).
- **Son kararı yapay zekâ vermez.** Gönder / yönlendir kararı [`decision.py`](src/helpdesk/domain/decision.py)
  içinde yedi açık kontroldür ve her biri testlidir.
- **Kaynaklı cevaplar:** alıntılanan her kural, bulunan belgede kodla **birebir** aranır; kaynak kartları
  model tarafından yazılmaz, doğrulanmış parça (chunk) kimliklerinden kodla oluşturulur.
- **Yönlendirilen talepte de yardım:** talep personele gitse bile belgelerin cevapladığı kısım öğrenciye
  hemen "ön bilgi" olarak gösterilir; hassas taleplerde asla.
- **Dürüst değerlendirme:** ayar için hiç kullanılmayan iki kilitli test seti; her ölçüt örnek sayısı ve
  %95 Wilson güven aralığıyla.
- **Üretim alışkanlıkları:** katman kuralları bir testle zorunlu tutulan katmanlı kod, her talep
  değişikliğinin değiştirilemeyen geçmişi (audit trail), tipli ayarlar, mypy strict, gerçek Postgres
  üzerinde 314 test, tarayıcı testleri, CodeQL, Dependabot, Docker, öğrenci metni içermeyen
  yapılandırılmış loglar, 18 karar kaydı (ADR).

## Nasıl çalışır

```mermaid
flowchart LR
    T[Öğrenci talebi<br/>TR / EN] --> C[Sınıflandırma<br/>kategori · öncelik · escalation]
    C --> R[Belge arama - RAG<br/>pgvector, ilk 3 parça]
    R --> A[Kaynaklı taslak<br/>önce alıntı, sonra cevap]
    A --> D{Karar<br/>sade kod, 7 kontrol}
    D -->|hepsi geçti| S[Öğrenciye otomatik cevap]
    D -->|biri bile kaldı| H[Birimin kuyruğu<br/>taslak + nedenler]
    H -.->|escalation yok, kaynak doğrulandı| F[Ön bilgi<br/>cevabın kaynaklı kısmı]
```

1. **Sınıflandırma.** Gemini talebe bir kategori (7 birim), bir öncelik (`urgent`, `high`, `medium`,
   `low`) ve insana gidip gitmeyeceğini (`escalate`) verir. Etiket kural kitabı
   ([`docs/labels.md`](docs/labels.md)) system prompt'tur; çıktı bir JSON şemasıyla sınırlıdır ve model
   etiketlerden önce gerekçesini yazar.
2. **Belge arama.** Talebin embedding'i çıkarılır (`gemini-embedding-2`, çok dilli) ve en yakın üç parça
   Postgres'te pgvector ile, talebin dilinde bulunur.
3. **Taslak.** Model önce dayandığı kuralı aynen alıntılar, sonra belgelerin soruyu cevaplayıp
   cevaplamadığını söyler, sonra cevabı yazar.
4. **Karar.** Cevap yalnızca şunların **hepsi** sağlanırsa otomatik gönderilir: kategori `other` değil,
   escalation yok, öncelik `urgent` değil, en iyi eşleşme ≥ 0,65, belgeler soruyu cevaplıyor ve cevap
   gerçekten bulunan bir belgeyi kaynak gösteriyor ve alıntı o belgede gerçekten var. Aksi hâlde talep, taslak ve nedenlerle birlikte
   birimin kuyruğuna gider.

Escalation şunları kapsar: güvenlik tehdidi, taciz veya kriz belirtisi, ele geçirilmiş olabilecek hesap,
kural istisnası, para veya resmî kayıt hatası, not ve sınav itirazı, hukuki tehdit ve disiplin süreci.
Sadece sinirli olmak bir neden değildir.

Ayrıntılar, diyagramlar, kullanım senaryoları ve değişmez kurallar: [ARCHITECTURE.md](ARCHITECTURE.md)
(İngilizce). Tüm belgeler: [docs/README.md](docs/README.md).

## Tasarım kararları

Her birinin bir karar kaydı var: [`docs/decisions/`](docs/decisions/).

| Karar | Neden | Kayıt |
|---|---|---|
| **LangChain veya LangGraph yok** | Sistemin bir modelden tek ihtiyacı belirli bir şemada JSON. Tek metotluk bir `LLMProvider` protokolü ve sade bir pipeline fonksiyonu bunu karşılar; bir framework büyük bir bağımlılık ekler ve prompt'ları gizler. Akışta gerçek döngüler olursa yeniden değerlendirilir. | [0012](docs/decisions/0012-package-factory-llm-provider.md) |
| **Son kararı model vermez** | Göndermek ya da yönlendirmek sade kodda yedi açık kontroldür, her biri test edilir; model yalnızca etiketleri ve taslağı verir. | [0002](docs/decisions/0002-decision-is-plain-code.md) |
| **Kaynaklar kodla kontrol edilir** | Alıntı, getirilen bölümde kelimesi kelimesine geçmelidir; kaynak kartları doğrulanmış parça kimliklerinden oluşturulur. Bu, talebin içine yerleştirilen sahte kuralları da etkisiz kılar. | [0010](docs/decisions/0010-prompt-injection-defence.md) |
| **Postgres + pgvector, ayrı vektör veritabanı yok** | Talepler, geçmiş ve vektörler tek veritabanında, transaction'larla; 190 parça için ayrı bir depo gerekmez. | [0004](docs/decisions/0004-postgres-pgvector.md) |
| **İki kilitli test seti** | Prompt'lar yalnızca dev setinde geliştirilir; kilitli setler hiç ayar yapılmamış skorlar verir ve bir hook onlarda her değişikliği engeller. | [0003](docs/decisions/0003-locked-test-set.md) |
| **Ücretsiz modellerden hedge'li bir zincir** | Ücretsiz katmandaki modeller sık sık meşgul: meşgul model işi hemen devreder, yavaş olanla 9 sn sonra yarışılır, hiçbir öğrenci 25 sn'den fazla beklemez. | [0018](docs/decisions/0018-live-model-chain.md) |
| **Resmî bilgi ve genel bilgi ayrı** | Resmî cevap ve etiketli genel tavsiye ayrı alanlardır; "resmî değildir" etiketini model değil sayfa koyar. | [0013](docs/decisions/0013-direct-answer-and-general-help.md) |

## Sonuçlar

Bütün sayılar [`eval/`](eval/) klasöründeki kayıtlı çalıştırmalardan gelir. Köşeli parantezler %95
Wilson güven aralığıdır; örnekler küçük olduğu için aralıklar geniştir.

> **Hangi sürümü ölçüyorlar.** Sınıflandırıcı ve arama sayıları güncel kodla aynıdır. Pipeline sayıları
> (otomatik gönderim, ön bilgi) 2026-10-23/24'te, cevap adımı doğrudan cevap ve genel bilgi verecek
> şekilde değiştirilmeden (2026-11-05, ADR 0013) **önce** ölçüldü. 2026-11-17'deki dev tekrarı Gemini
> yoğunluğu yüzünden yarım kaldı (80 talepten 52'si ölçüldü) ve iki sorunlu bir talepte **bir güvensiz
> otomatik gönderim** buldu (yazıcı arızası ve GPA sorusu: GPA kısmı cevaplandı, yazıcı sorunu Bilgi
> İşlem'e hiç ulaşmadı). Bu düzeltiliyor; tablo tam bir çalıştırmayla güncellenecek.

**Gerçekçi kilitli set** (40 talep, 20 TR + 20 EN, ayar için hiç kullanılmadı): uzun ve dağınık
mesajlar, yazım hataları, Türkçe karakter kullanılmayan metinler, karışık dil, iki sorunlu talepler, takip
mesajları, başka kurumların işi, hafifçe yazılmış taciz ve kriz belirtileri, bir prompt injection.

| Ölçüt | Sonuç | Örnek |
|---|---|---|
| **Kaçırılan escalation** (en tehlikeli hata) | **0 / 11** (iki çalıştırmada da) | 11 escalation talebi |
| **Hatalı otomatik gönderim** | **0** | 40 talep |
| Yanlış belge gösteren cevap | 0 | 40 talep |
| Üç etiketin üçü de doğru | %72,5 [%57–84] | 40 talep |
| Kategori / öncelik / escalation | %92,5 / %85,0 / %95,0 | 40 talep |
| İnsansız çözülen | 15 / 40 [%24–53] | 40 talep |
| Doğru belge ilk 3 sonuçta (hit@3) | %100 [%89–100] | cevaplanabilir 30 talep |

**İlk kilitli set** (40 talep): üç etiketin üçü de doğru %73,8 (iki çalıştırmanın ortalaması, %72,5 ve
%75,0; her biri yaklaşık %57–86), kaçırılan escalation 0 / 14, cevaplanabilir 17 talepte hit@3 %100
[%82–100], 1 zararsız hatalı otomatik gönderim (Bilişim Hesapları belgesi eklenerek kapatıldı).

**Prompt injection denemeleri:** 12 / 12 güvenli [%76–100] (sahte kural, çiti kırma, "kurallarını unut",
talimatları yazdırma, rol yapma, kanarya kelimesi). Kaynak gösteren cevaplardaki alıntıların 35 / 36'sı
belgelerde birebir bulundu [%86–99,5].

**Ön bilgi** (dev seti, 80 talep): hemen yardım alan öğrenci 15 / 79'dan 27 / 80'e çıktı [%24–45];
escalation gerektiren hiçbir talepte gösterilmedi.

### Bu sayılar neyi göstermez

- Talepler sentetiktir: hepsini ben yazdım veya etiketledim (gerçekçi seti, gerçek öğrenci sorunları
  üzerine yapılan araştırmadan Claude taslak olarak yazdı; etiketlerin hepsi benim). Gerçek talepler daha
  dağınıktır.
- 0 / 11 kaçırılan escalation, gerçek oranın sıfır olduğunu kanıtlamaz: üst sınır yaklaşık %26'dır.
- Prompt'lar dev setiyle yazıldı, bu yüzden dev skorları iyimserdir (ilk çalıştırmada kilitli setten
  yaklaşık 10 puan yüksek).
- Güncel cevap adımı (ADR 0013) ve büyüyen bilgi tabanı için henüz tam bir pipeline çalıştırması yok
  (yukarıdaki nota bakın).

## Özellikler

**Öğrenciler için**
- Türkçe veya İngilizce cevap ve resmî sayfaya bağlanan kaynak kartları.
- **"Nasıl karar verildi?"**: kararın arkasındaki gerçek kontrollerin adım adım izi.
- **Taleplerim**: gizli bir erişim koduyla talebi takip etme ve personelin cevabını okuma (veritabanında
  yalnızca kodun özeti saklanır, [ADR 0009](docs/decisions/0009-student-ticket-access-code.md)).
- **"Bir uzmana gönder"**: otomatik cevap sorunu çözmediyse tek tıkla talep doğru birimin kuyruğuna
  girer, personel için işaretlenir ([ADR 0016](docs/decisions/0016-student-can-ask-for-a-person.md)).
- Geri bildirim düğmeleri, kriz taleplerinde acil durum (112) düğmesi ve dürüst bir bekleme göstergesi.

**Personel için**
- Birime göre giriş (Argon2id şifreler, HttpOnly oturum çerezi, CSRF koruması, hatalı girişlerde
  engelleme); personel yalnızca kendi biriminin taleplerini görür.
- İnceleme kuyruğu: önce acil olanlar, sonra en uzun bekleyen; kaynaklı taslağı düzenleyip gönderme veya
  birim değiştirme.
- İstatistikler: toplam, otomatik cevap, ön bilgi, bekleyen, medyan cevap süresi, faydalı bulunma;
  her biri örnek sayısıyla; her grafik tablo olarak da görülebilir.
- Demo modu: yalnızca örnek talepler, gerçek taleplerden tamamen ayrı
  ([ADR 0006](docs/decisions/0006-demo-mode-keeps-login.md)).

| Kaynaklı otomatik cevap | Yönlendirilen talepte ön bilgi |
|---|---|
| ![Öğrenci cevabı](docs/images/student_answer.jpg) | ![Ön bilgi](docs/images/student_first_help.jpg) |

| Personel inceleme kuyruğu | Kaynaklı taslakla yönlendirilen talep |
|---|---|
| ![İnceleme kuyruğu](docs/images/staff_queue.jpg) | ![Talep ayrıntısı](docs/images/staff_ticket.jpg) |

## Bilgi tabanı

14 konu × 2 dil = 28 belge ve 190 parça, yalnızca resmî BŞEÜ kaynaklarından: Ön Lisans ve Lisans
Eğitim-Öğretim Yönetmeliği, Muafiyet ve İntibak, Yaz Okulu, Staj, Öğrenci Kulüpleri ve Engelli
Öğrenciler yönergeleri, Öğrenci İşleri SSS, SKS sayfaları, Kütüphane sayfaları, Bilgi İşlem e-posta
sayfası, 2026-2027 katkı payı tabloları, Tahsilat Rehberi, UZEM SSS ve 2025-2026 oryantasyon
sunumları. Tırnak içindeki her cümle resmî metinle birebir kontrol edildi (önce 119; notlar belgesinin 11 alıntısı 2026-11-05'te eklenip kontrol edildi). Vektörler
[`data/kb_index.json`](data/kb_index.json) dosyasında saklanır ve uygulama başlarken Postgres'e
kopyalanır; böylece boş bir veritabanı API çağrısı yapmadan dolar. Hangi boşluğun neden kapatıldığı:
[`docs/knowledge_gaps.md`](docs/knowledge_gaps.md).

## Güvenlik ve kişisel veri

- **Prompt injection:** öğrencinin metni her iki prompt'ta çitle ayrılır ve alıntı kontrolü, bulunan
  kurallarda olmayan her alıntıyı reddeder ([ADR 0010](docs/decisions/0010-prompt-injection-defence.md)).
- **Loglarda kişisel veri yok:** bir talebin yalnızca uzunluğu loglanır, metni veya e-posta adresi asla;
  bunu bir test garanti eder.
- **Kötüye kullanım sınırları:** herkese açık uç noktalarda rate limit, günlük talep sınırı, güvenilir
  istemci IP başlığı ([ADR 0007](docs/decisions/0007-client-ip-header.md)), SQL yalnızca yer tutucularla.
- **Gizli bilgiler** yalnızca ortam değişkenlerindedir; imaj root olmayan bir kullanıcıyla çalışır.

Güvenlik açığı bildirmek için: [SECURITY.md](SECURITY.md).

## Teknolojiler

| Katman | Araçlar |
|---|---|
| LLM | Google Gemini, ücretsiz katman: canlıda model zinciri `gemini-3.5-flash-lite` → `gemini-4-hydrogen` → `gemini-3.1-flash-lite`, 9 sn sonra hedge, 25 sn sınır (ADR 0018; aşağıdaki skorlar 3.5-flash-lite ile ölçüldü), `gemini-embedding-2` |
| Backend | Python 3.12, FastAPI, pydantic-settings, structlog, psycopg 3 |
| Veritabanı | PostgreSQL 18 + pgvector (üretimde Neon) |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Router + Query; API istemcisi OpenAPI şemasından üretilir |
| Kalite | uv, ruff, mypy (strict), kapsam eşikli pytest, Playwright, Biome, CodeQL, Dependabot |
| Dağıtım | Docker (çok aşamalı, root olmayan), GitHub Actions, Render (Frankfurt) |

Her önemli seçimin nedeni: [`docs/decisions/`](docs/decisions/).

## Hızlı başlangıç

**Docker ile** (yalnızca Docker ve bir [Gemini API anahtarı](https://aistudio.google.com/apikey) gerekir):

```sh
cp .env.example .env           # sonra .env içine kendi API anahtarınızı yazın
docker compose up --build      # http://127.0.0.1:8000 adresini açın
```

**Geliştirme için** (Python 3.12, [uv](https://docs.astral.sh/uv/), Node.js 24 LTS):

```sh
make install                   # uv sync --locked + frontend/ içinde npm ci
make db                        # yerel Postgres 18 + pgvector, port 5433
make serve                     # otomatik yenilenen API: http://127.0.0.1:8000
cd frontend && npm run dev     # web arayüzü: http://localhost:5173 (öğrenci) ve /staff
```

Personel hesabı oluşturma (herkese açık kayıt yoktur):

```sh
uv run python tools/add_staff.py ad@bilecik.edu.tr "Ad Soyad" --office it   # it, student_affairs, fees, sks, duty
```

**Kontroller** (API çağrısı yok): `make check`, CI'daki her şeyi çalıştırır: ruff, mypy, Postgres
üzerinde pytest, OpenAPI uyumu ve frontend kontrolleri. `make help` tüm komutları listeler.

**Değerlendirmeler** modeli çağırır: `make eval SUITE=classifier|pipeline|retrieval|security`; `SET=dev`
(varsayılan), `SET=test` veya `SET=realistic` ile. Kayıtlı her sonuç, onu üreten git commit'ini, prompt
hash'lerini, veri seti ve bilgi tabanı hash'lerini ve modeli içerir. Kilitli setlerde yalnızca ölçülür,
asla ayar yapılmaz.

## Proje yapısı

```
src/helpdesk/        Backend paketi; her katman yalnızca altındaki katmanları import eder (tests/test_architecture.py)
  core/              Ayarlar (başlangıçta doğrulanır), dosya yolları, yapılandırılmış loglar
  domain/            Saf kurallar ve veri: karar, alıntı kontrolü, birimler, etiketler, kayıtlı talep, çıktı şemaları
  ai/                Gemini istemcisi, hedge'li canlı model zinciri, sınıflandırıcı, kaynaklı cevap, injection çiti
  storage/           Tek SQL katmanı: bağlantı havuzu, eklemeli migration'lar, talepler ve geçmişi, personel
  retrieval/         Parçalara bölme, embedding, index senkronu ve pgvector araması
  services/          Kullanım senaryoları (use case): akış, öğrenci talepleri, personel masası, giriş, istatistik
  api/               FastAPI uygulama fabrikası ve ince router'lar (öğrenci, giriş, personel)
  evals/             Sınıflandırma, arama, tüm akış ve güvenlik değerlendirmeleri; Wilson aralıkları
frontend/            React uygulaması (öğrenci sohbeti, Taleplerim, personel paneli) ve Playwright testleri
data/knowledge_base/ Resmî kaynaklı 28 belge (TR + EN)
data/tickets/        Etiketli talepler: dev (80), kilitli test (40), kilitli gerçekçi set (40)
eval/                Kayıtlı değerlendirme sonuçları
docs/                Dizin, etiket kural kitabı, karar kayıtları, yol haritası, sorun kataloğu, günlük
tests/               Gerçek Postgres üzerinde 314 pytest testi; her AI çağrısı taklit edilir
tools/               Personel hesapları, demo verisi, OpenAPI dışa aktarma, veri seti denetimi
```

## Sınırlar

- Her talep tek bir kategori alır: iki birimi ilgilendiren bir talebin bir kısmı yanlış birime gidebilir.
- Personelin cevabı öğrenciye yalnızca aynı tarayıcıdaki "Taleplerim" sayfasında ulaşır; e-posta
  bildirimi ve öğrenci girişi (SSO) henüz yoktur.
- Ücretler, yemek fiyatları ve çalışma saatleri her yıl değişir; belgeler elle güncellenir.
- Kayıp eşya, Office 365 lisansı, arıza bildirimleri ve resmî kaynağı olmayan her konu insana gider.
- Staj kuralları yalnızca Mühendislik Fakültesi içindir; KYK yurt bölümü resmî olmayan bir kaynağa
  dayanır ve bunu belirtir.
- Ücretsiz katmanın dakika ve gün başına istek sınırları vardır; bu yüzden Flash-Lite kullanılır ve
  çağrılar arasında beklenir.

## Yol haritası

| Alan | Durum |
|---|---|
| Sınıflandırıcı, kaynaklı cevaplar, karar kuralları, personel konsolu, öğrenci takibi, güvenlik, canlıya alma | ✅ Tamamlandı |
| Tek komutla sürümlü eval'ler | ✅ Tamamlandı (CI'da eval workflow'u ve model karşılaştırması sırada) |
| Hibrit arama (tam metin + pgvector, rank fusion), ölçülerek | ⏳ Sırada |
| Daha büyük etiketli dev seti, yerel açık bir model dahil model karşılaştırması | ⏳ Sırada |
| Talep başına tracing (OpenTelemetry) | ⏳ Sırada |
| E-posta bildirimi, öğrenci SSO | ⏳ Sonra |

Ayrıntılar: [docs/ROADMAP.md](docs/ROADMAP.md). Her değişiklik ve nedeni:
[docs/dev-notes/journal.md](docs/dev-notes/journal.md) (İngilizce).

## Nasıl geliştirildi

Ahmed Elghazzawy tarafından, yazılı kurallar altında eşli programcı olarak
[Claude Code](https://claude.com/claude-code) ile geliştirildi: [CLAUDE.md](CLAUDE.md) çalışma şeklini
tanımlar (keşfet, planla, önce test, doğrula, her kararı kaydet); [`.claude/`](.claude/) klasöründe
skill'ler, inceleme ajanları ve kilitli test setlerinde her değişikliği engelleyen bir hook bulunur
([ADR 0011](docs/decisions/0011-agent-instructions-and-guardrails.md)). Katkı için:
[CONTRIBUTING.md](CONTRIBUTING.md).

## Lisans

[MIT](LICENSE) © 2026 Ahmed Elghazzawy
