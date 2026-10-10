# Üniversite Yardım Masası Ticket Asistanı

**Çalışma Tasarımı I** · Bilecik Şeyh Edebali Üniversitesi (BŞEÜ), Bilgisayar Mühendisliği

Öğrencilerin yardım masasına yazdığı ticket'ları okuyan bir AI asistanı. Sistem ticket'ı etiketler (kategori, öncelik, escalation), üniversitenin resmî belgelerinde cevabı arar (RAG), kaynağını gösteren bir cevap yazar ve karar verir: cevabı otomatik göndermek mi, yoksa doğru birime (bir insana) yönlendirmek mi.

## Akış (pipeline)

```
ticket → sınıflandırma → belge arama (RAG) → kaynaklı taslak cevap → karar → otomatik gönder / birime yönlendir
```

| Aşama | Durum |
|---|---|
| Sınıflandırma (classification) | ✅ Phase 1 |
| Değerlendirme (evaluation) | ✅ Phase 1 |
| Kilitli test seti (güvenilir skor) | ✅ Phase 2 |
| Belge arama (RAG retrieval) | ✅ Phase 3 |
| Kaynaklı cevap (answer generation) | ✅ Phase 4 |
| Gönder / gönderme kararı ve yönlendirme | ✅ Phase 4 |
| Web sayfası (FastAPI) ve otomatik testler (pytest) | ✅ Phase 5 |

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

## Güvenilir skor: kilitli test seti (Phase 2)

40 yeni ticket (20 TR + 20 EN), prompt'u ayarlamak için hiç kullanılmadı. 2 çalıştırmanın ortalaması:

| Ölçüt | Dev (80) | **Test (40)** |
|---|---|---|
| Kategori | %98,1 | **%90,0** |
| Öncelik (tam) | %88,1 | **%85,0** |
| Escalation | %96,2 | **%88,8** |
| Üçü de doğru | %84,4 | **%73,8** |
| **Kaçırılan escalation** | 0 | **0** |

Dev skoru yaklaşık 10 puan iyimserdi. Kaçırılan escalation testte de 0: kural kitabında olmayan durumlar (oturma izni, gıda zehirlenmesi, intihardan bahseden bir arkadaş) bile insana yönlendirildi. Not: test ticket'larını araştırmaya dayanarak Claude taslak olarak yazdı; sınıf arkadaşlarından toplanan gerçek ticket'lar daha güçlü bir test olur.

## Bilgi tabanı ve belge arama (Phase 3)

- 11 konu × 2 dil = 22 belge, yalnızca resmî BŞEÜ kaynaklarından: Ön Lisans ve Lisans Eğitim-Öğretim Yönetmeliği (Resmî Gazete 07.07.2019), Muafiyet ve İntibak Yönergesi, Yaz Okulu Yönetmeliği, Mühendislik Fakültesi Staj Yönergesi, Öğrenci Kulüpleri Yönergesi, Öğrenci İşleri SSS, 2025-2026 Oryantasyon Sunumu (SOFRA, e-posta, OBS, UZEM, eduroam, kütüphane, yemekhane kartı). Tırnak içindeki 59 cümlenin 59'u resmî metinle birebir kontrol edildi.
- Her `##` bölümü bir parça (chunk): 112 parça. Embedding: `gemini-embedding-2` (768 boyut, çok dilli). Ticket hangi dildeyse o dilde aranır.
- Sonuç (doğru belge ilk 3 sonuçta, cevaplanabilir ticket'lar): **dev %100 (46), test %100 (17)**; ilk sırada: dev %91, test %94.
- Ticket'ların yalnızca yaklaşık yarısı belgelerle cevaplanabiliyor (dev 46/80, test 17/40).

## Kaynaklı cevap ve karar (Phase 4)

- Model önce kurallardan cümleyi aynen alıntılar (`evidence`), sonra cevabın belgelerde olup olmadığına karar verir (`covered`), sonra cevabı yazar ve kaynağı gösterir.
- Otomatik gönderim yalnızca şu kontrollerin **hepsi** geçerse: kategori `other` değil, escalation yok, öncelik `urgent` değil (acil durumda bir insan bugün harekete geçebilir), benzerlik puanı ≥ 0,65, belgeler cevaplıyor, cevap gerçekten bulunan bir belgeyi kaynak gösteriyor. Karar fonksiyonu yapay zekâ değil, sade koddur (test edilebilir).
- Dev sonucu (79 ticket): **hatalı otomatik gönderim 0**, yanlış belge gösteren cevap 0, otomatik gönderilen 15 cevaptan 11'i iyi, 1'i orta, 3'ü doğru ama az faydalı; hiçbirinde uydurma bilgi yok.
- Öğrenciye gönderilmeyen taslak sunucudan hiç çıkmaz (`reply: null`).

## Kapsam ve sınırlar (v1)

- Her ticket **tek bir kategori** alır; iki farklı birimi ilgilendiren bir ticket'ın bir kısmı yanlış birime gidebilir.
- Bilgi tabanı 11 konuyla sınırlı; tarihler ve ücret tutarları belgelerde yok, bu yüzden bu sorular insana yönlendirilir.
- Staj kuralları yalnızca Mühendislik Fakültesi içindir; KYK bölümü resmî olmayan bir kaynağa dayanır.
- KYK yurtları ve KYK burs/kredi devlete aittir; sistem bu konularda sadece yönlendirme yapar.
- Ücretsiz katmanın sınırları var (bir model için günde 20 istek görüldü; embedding için dakikada 100 metin); bu yüzden Flash-Lite kullanılıyor ve çağrılar arasında bekleniyor.

## Kurulum ve çalıştırma

Gereken: Python 3.12, [uv](https://docs.astral.sh/uv/) ve bir Gemini API anahtarı ([Google AI Studio](https://aistudio.google.com/apikey)).

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env          # sonra .env içine kendi API anahtarınızı yazın
```

```sh
.venv/bin/python src/tickets.py            # veri setini kontrol et ve özetini göster
.venv/bin/uvicorn api:app --app-dir src    # öğrenci sayfası: http://127.0.0.1:8000
.venv/bin/streamlit run src/app.py          # personel paneli: genel bakış, veri seti, değerlendirme
.venv/bin/pytest                             # otomatik testler (API çağrısı yok, 1 saniyeden kısa)
.venv/bin/python src/evaluate.py high       # sınıflandırma değerlendirmesi (yaklaşık 20 dakika)
.venv/bin/python src/evaluate_retrieval.py  # belge arama değerlendirmesi
.venv/bin/python src/evaluate_pipeline.py   # tüm sistem: hatalı otomatik gönderim sayısı
```

`.env` dosyası API anahtarını tutar ve `.gitignore` sayesinde asla GitHub'a yüklenmez.

## Proje yapısı

```
src/llm.py              Gemini bağlantısı: .env'den anahtar ve model, otomatik yeniden deneme (retry)
src/tickets.py          Geçerli bir ticket'ın tanımı (pydantic) ve tickets.jsonl yükleyicisi
src/classifier.py       Sınıflandırıcı: kural kitabından system prompt, structured output
src/evaluate.py         Değerlendirme: skorlar, escalation hataları, tutarlılık
src/knowledge_base.py   Belgeleri parçalara (chunk) böler
src/retrieval.py        Embedding ve belge arama
src/evaluate_retrieval.py  Belge arama değerlendirmesi (hit@1, hit@3)
src/answer.py           Kaynaklı cevap (önce alıntı, sonra cevap)
src/decision.py         Otomatik gönder / yönlendir kararı ve birimler
src/pipeline.py         Bir ticket için tüm adımlar
src/evaluate_pipeline.py   Tüm sistemin değerlendirmesi
src/api.py              FastAPI: öğrenci sayfası ve POST /api/tickets
src/app.py              Streamlit personel paneli (Türkçe / İngilizce)
web/                    Öğrenci sohbet sayfası (HTML, CSS, JavaScript; BŞEÜ stili, karanlık mod)
tests/                  pytest testleri (karar kuralları ve API)
data/knowledge_base/    22 resmî kaynaklı belge (TR + EN)
src/try_one_ticket.py   İlk API çağrısı testi (Step 1)
data/tickets/           Etiketli ticket'lar
eval/                   Kaydedilen değerlendirme sonuçları
docs/labels.md          Etiket kural kitabı
docs/problem_catalog.md Öğrenci sorunları kataloğu (araştırma)
docs/changelog.md       Projede yapılan her değişiklik ve nedeni
tools/make_context.py   Tüm projeyi tek dosyada toplar (öğrenmek için)
```

## Sonraki adımlar

- Daha fazla içerik: akademik takvim, ücret tablosu, psikolojik danışmanlık ve yemekhane menüsü.
- Sınıf arkadaşlarından gerçek ticket'lar toplayıp yeni bir kilitli test seti oluşturmak.
- Kilitli test setinde tüm sistemin (Phase 4) değerlendirmesi.
- LangGraph, insan inceleme kuyruğu, stres testleri (Phase 6-7).
