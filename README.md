# Üniversite Yardım Masası Ticket Asistanı

**Çalışma Tasarımı I** · Bilecik Şeyh Edebali Üniversitesi (BŞEÜ), Bilgisayar Mühendisliği

Öğrencilerin yardım masasına yazdığı ticket'ları okuyan bir AI asistanı. Sistem ticket'ı etiketler (kategori, öncelik, escalation), ileride üniversitenin resmi belgelerinde cevabı arayacak (RAG), kaynağını gösteren bir taslak cevap yazacak ve karar verecek: cevabı otomatik göndermek mi, yoksa taslakla birlikte doğru birime (bir insana) yönlendirmek mi.

## Akış (pipeline)

```
ticket → sınıflandırma → belge arama (RAG) → kaynaklı taslak cevap → karar → otomatik gönder / birime yönlendir
```

| Aşama | Durum |
|---|---|
| Sınıflandırma (classification) | ✅ Phase 1 |
| Değerlendirme (evaluation) | ✅ Phase 1 |
| Belge arama (RAG retrieval) | ⏳ Phase 3 |
| Kaynaklı taslak cevap (answer generation) | ⏳ Phase 4 |
| Gönder / gönderme kararı ve yönlendirme | ⏳ Phase 4 |

## Kategoriler ve birimler (7 kategori)

| Kategori | Kapsam (örnekler) | Yönlendirilen BŞEÜ birimi |
|---|---|---|
| `account_access` (Hesap Erişimi) | OBS / SOFRA / e-posta girişi, şifre, 2FA, ele geçirilmiş hesap | Bilgi İşlem Daire Başkanlığı |
| `it_support` (Teknik Destek) | Wi-Fi / eduroam, UZEM, yazıcı, laboratuvar yazılımı (giriş sorunu olmadan) | Bilgi İşlem Daire Başkanlığı |
| `registration` (Ders Kaydı) | Ekle-bırak, kontenjan, ön koşul, ders çakışması, AKTS sınırı | Öğrenci İşleri Daire Başkanlığı |
| `academic_records` (Akademik Kayıtlar) | Transkript, öğrenci belgesi, notlar, kayıt dondurma, muafiyet, staj evrakları, disiplin, mezuniyet | Öğrenci İşleri Daire Başkanlığı |
| `billing` (Ödemeler) | Harç / katkı payı, üniversite bursu, iade, harç muafiyeti | Öğrenci İşleri, İstatistik Disiplin ve Harçlar Şube Müdürlüğü |
| `campus_life` (Kampüs Yaşamı) | Yemekhane, kulüpler, ulaşım, psikolojik danışmanlık, kütüphane, KYK yurt yönlendirmesi | Sağlık, Kültür ve Spor (SKS) Daire Başkanlığı |
| `other` (Diğer) | Kayıp eşya, kariyer, KYK burs/kredi, tehdit ve taciz, konu dışı veya anlaşılmayan ticket'lar | Öğrenci İşleri nöbetçi personeli |

**Öncelik (priority):** `urgent`, `high`, `medium`, `low`. Öncelik = sorunun öğrenciyi ne kadar engellediği × ne kadar acil olduğu.

**Escalation (insana yönlendirme):** şu durumlardan herhangi biri varsa: güvenlik tehdidi, taciz veya kriz belirtisi; ele geçirilmiş olabilecek hesap; kural istisnası; para veya resmi kayıt hatası (iade/düzeltme); not veya sınav itirazı ya da sınavın geçerliliği hakkında karar; hukuki tehdit, disiplin süreci veya cevapsız tekrarlanan başvuru. Sadece sinirli olmak escalation sebebi değildir.

Tüm kurallar ve sınır durumları: [`docs/labels.md`](docs/labels.md). Araştırmaya dayalı sorun listesi: [`docs/problem_catalog.md`](docs/problem_catalog.md).

## Veri seti

- **80 geliştirme (dev) ticket'ı:** 40 Türkçe + 40 İngilizce, [`data/tickets/tickets.jsonl`](data/tickets/tickets.jsonl) (her satır bir JSON: `id`, `text`, `language`, `category`, `priority`, `escalate`).
- Her kategoride 10-12 ticket; dört öncelik seviyesi de var; ticket'ların %26'sı escalation gerektiriyor.
- Zor durumlar bilerek eklendi: iki sorunlu ticket'lar, çok kısa ("help", "obs calismiyor"), Türkçe karakter olmadan yazım, karışık dil, sinirli ama basit, kibar ama ciddi, gizli kriz belirtisi, prompt injection.
- Ticket'lar gerçek BŞEÜ sistem adlarını kullanır: OBS, SOFRA, UZEM, @ogrenci.bilecik.edu.tr, Akıllı Kart.
- **Phase 2:** 40 yeni ticket (20 TR + 20 EN) **kilitli test seti** olacak: prompt'u ayarlamak için asla kullanılmaz, sadece son skor için.

## Sınıflandırma yöntemi

- Model: `gemini-3.5-flash-lite` (Google Gemini API, ücretsiz katman). Model adı `.env` dosyasında, kod değişmeden değiştirilebilir.
- **System prompt = kural kitabı:** [`docs/labels.md`](docs/labels.md) olduğu gibi prompt'a eklenir. Tek bir doğruluk kaynağı.
- **Structured output:** model sadece bizim JSON şemamıza uyan bir cevap verebilir (geçersiz kategori imkânsız).
- **`reason` alanı önce:** model önce gerekçesini yazar, sonra etiketleri seçer.
- **Temperature 1.0 (varsayılan):** Google'ın resmi Gemini 3 önerisi; daha düşük değerler döngü veya performans kaybına yol açabilir.
- **Thinking level `high`:** `low` ile karşılaştırıldı ve daha iyi çıktı (aşağıda).

## Değerlendirme yöntemi

[`src/evaluate.py`](src/evaluate.py) her ticket'ı **iki kez** sınıflandırır ve modelin etiketlerini bizim etiketlerimizle karşılaştırır:

- Her etiket için doğruluk (accuracy), üçü birden doğru, Türkçe ve İngilizce ayrı ayrı
- **Kaçırılan escalation:** insana gitmesi gerekip gitmeyen ticket (en tehlikeli hata)
- Gereksiz escalation (güvenli hata)
- Öncelik için "bir seviye yakın" doğruluk (öncelik öznel bir etikettir)
- **Tutarlılık (consistency):** aynı model aynı ticket'a ikinci çalıştırmada aynı etiketi veriyor mu?

Sonuçlar `eval/results_low.json` ve `eval/results_high.json` dosyalarına kaydedilir.

## İlk sonuçlar (80 dev ticket, 2 çalıştırmanın ortalaması)

| Ölçüt | thinking `low` | thinking `high` |
|---|---|---|
| Kategori | %98,1 | %98,1 |
| Öncelik (tam) | %75,6 | **%88,1** |
| Öncelik (bir seviye yakın) | %98,8 | %98,8 |
| Escalation | %94,4 | **%96,2** |
| Üçü de doğru | %70,6 | **%84,4** |
| **Kaçırılan escalation** | **0** | **0** |
| Tutarlılık (kategori / öncelik / escalation) | %99 / %89 / %96 | %99 / %96 / %98 |

`high`, 1. çalıştırma, dile göre (üçü de doğru): Türkçe %75,0, İngilizce %92,5.

### Bu skor neyi kanıtlamaz (önemli)

- **İyimser bir skordur.** Kural kitabı bu 80 ticket'a bakılarak netleştirildi ve `high` de bu ticket'larda seçildi. Güvenilir skor Phase 2'deki **kilitli test setinden** gelecek.
- **Rastgelelik var:** aynı model aynı ticket'larda iki çalıştırmada %73,8 ve %67,5 aldı (`low`, üçü de doğru). Tek bir skor kesin değildir.
- **Etiketler tartışmalı olabilir:** özellikle öncelik. Ticket'ları ve etiketleri biz yazdık; gerçek öğrenci ticket'ları daha dağınıktır.
- **Türkçe ticket'lar daha zor:** Türkçe skorlar İngilizceden düşük.

## Kapsam ve sınırlar (v1)

- Her ticket **tek bir kategori** alır; iki farklı birimi ilgilendiren bir ticket'ın bir kısmı yanlış birime gidebilir.
- Henüz cevaplar üniversite belgelerine dayanmıyor (RAG Phase 3'te). Web sayfasındaki taslak cevap bilgi uydurabilir.
- KYK yurtları ve KYK burs/kredi devlete aittir; sistem bu konularda sadece yönlendirme yapar.
- Ücretsiz katmanın günlük istek sınırları var (bir model için günde 20 istek görüldü); bu yüzden Flash-Lite kullanılıyor.

## Kurulum ve çalıştırma

Gereken: Python 3.12, [uv](https://docs.astral.sh/uv/) ve bir Gemini API anahtarı ([Google AI Studio](https://aistudio.google.com/apikey)).

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env          # sonra .env içine kendi API anahtarınızı yazın
```

```sh
.venv/bin/python src/tickets.py            # veri setini kontrol et ve özetini göster
.venv/bin/python src/evaluate.py high      # değerlendirme (yaklaşık 20 dakika, 160 API çağrısı)
.venv/bin/streamlit run src/app.py         # web sayfası: ticket dene, veri seti, değerlendirme
```

`.env` dosyası API anahtarını tutar ve `.gitignore` sayesinde asla GitHub'a yüklenmez.

## Proje yapısı

```
src/llm.py              Gemini bağlantısı: .env'den anahtar ve model, otomatik yeniden deneme (retry)
src/tickets.py          Geçerli bir ticket'ın tanımı (pydantic) ve tickets.jsonl yükleyicisi
src/classifier.py       Sınıflandırıcı: kural kitabından system prompt, structured output
src/evaluate.py         Değerlendirme: skorlar, escalation hataları, tutarlılık
src/app.py              Streamlit web sayfası (Türkçe / İngilizce)
src/try_one_ticket.py   İlk API çağrısı testi (Step 1)
data/tickets/           Etiketli ticket'lar
eval/                   Kaydedilen değerlendirme sonuçları
docs/labels.md          Etiket kural kitabı
docs/problem_catalog.md Öğrenci sorunları kataloğu (araştırma)
docs/changelog.md       Projede yapılan her değişiklik ve nedeni
tools/make_context.py   Tüm projeyi tek dosyada toplar (öğrenmek için)
```

## Sonraki adımlar

- **Phase 2:** 40 ticket'lık kilitli test seti, dev ve test skorlarının karşılaştırılması.
- **Phase 3 (RAG):** 8-10 kısa BŞEÜ politika belgesi (Türkçe ve İngilizce): ör. harç ve iade, kayıt dondurma, ders kaydı ve ekle-bırak, mazeret sınavı, OBS/SOFRA şifre işlemleri, Akıllı Kart, staj, KYK yönlendirmesi. Parçalara bölme (chunking), embedding, arama; doğru belgenin ilk 3 sonuçta olma oranı ölçülecek.
- **Phase 4:** kaynak gösteren taslak cevaplar, gönder / gönderme kararı ve birime yönlendirme.
- **Sonra:** FastAPI, pytest, LangGraph, insan inceleme kuyruğu, stres testleri.
