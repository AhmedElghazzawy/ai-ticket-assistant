# Sunum notları: hocama güncel durum (05.11.2026)

Bu belge benim için bir hazırlık kâğıdıdır: ne göstereceğim, hangi sırayla, hangi sayıları söyleyeceğim
ve hangi soruları bekliyorum. Son gösterilen sürüm v0.9 idi (16.10.2026); burada o günden sonra
yapılanlar var. Bütün sayılar README'deki ve `eval/` klasöründeki kayıtlı sonuçlardır.

## Sunumdan önce (sabah)

- [ ] Canlı demoyu sunumdan **en az 2 dakika önce** aç: https://bseu-helpdesk.onrender.com
      (ücretsiz sunucu uyuyor; ilk açılış yaklaşık 30-60 saniye sürüyor).
- [ ] Aşağıdaki demo sorularını bir kez dene; cevaplar modelden geldiği için her seferinde kelimesi
      kelimesine aynı olmayabilir.
- [ ] İnternet yoksa yedek: README'deki ekran görüntüleri (`docs/images/`) ve yerelde `make up`.
- [ ] GitHub sayfası ikinci sekmede açık: README, "Hocam, nereden başlamalı?" tablosu.

## 5 dakikalık akış

1. **Problem (30 sn).** Öğrenciler aynı soruları tekrar tekrar soruyor; personelin zamanı gidiyor.
   Sistem talebi okur, etiketler, resmî belgelerde cevabı arar ve ya kaynaklı cevabı gönderir ya da
   taslakla birlikte doğru birime yönlendirir.
2. **Otomatik cevap (1 dk).** Ana sayfada sor: *"Kütüphane hafta sonu açık mı?"* veya
   *"Spor salonu ücreti ne kadar?"* (yeni eklenen resmî belgeler). Kaynak kartını ve
   **"Nasıl karar verildi?"** izini göster: kararın 6 kontrolü sade koddur, yapay zekâ değil.
3. **Yönlendirme ve ön bilgi (1 dk).** Sor: *"Kaydımı sildirirsem harç iade edilir mi? Ayrıca
   danışmanım ders kaydımı onaylamıyor."* İki sorunlu bir talep olduğu için büyük olasılıkla birime
   gider (sabah denemede kontrol et); gittiğinde belgelerin cevapladığı kısım öğrenciye hemen
   "Ön bilgi" olarak gösterilir (karar kaydı 0008).
4. **Güvenlik (1 dk).** Sor: *"Hesabım ele geçirildi, birisi notlarımı değiştirmiş olabilir."*
   Escalation: öğrenciye yapay zekâ metni gösterilmez, doğrudan insana gider. Prompt injection
   savunmasını anlat: alıntılanan her cümle belgede birebir aranır (karar kaydı 0010).
5. **Personel paneli (1 dk).** `/staff` → **Demo olarak dene**: birime göre kuyruk, yönlendirme
   nedenleri, düzenlenebilir kaynaklı taslak, İstatistikler sayfası (her sayının yanında n).
6. **Sonuçlar ve sınırlar (30 sn).** Aşağıdaki tablo ve "dürüst notlar".

## v0.9'dan bu yana yapılanlar

- **Gerçekçi ikinci kilitli test seti** (Phase 8): uzun, yazım hatalı, karışık dilli 40 talep; etiketleri ben verdim.
- **%95 güven aralıkları** (Wilson) bütün değerlendirmelerde.
- **Ön bilgi**: yönlendirilen taleplerde öğrenci boş beklemiyor (dev: 15/79 → 27/80).
- **Kaynaklar kodla oluşturuluyor**: model kaynak adı yazmıyor, uydurma kaynak gösteremez.
- **Öğrenci için**: Taleplerim (gizli kodla talep takibi), çalışan geri bildirim, "Nasıl karar verildi?".
- **Personel için**: İstatistikler sayfası.
- **Prompt injection savunması**: çit + alıntının kodla doğrulanması; 12/12 saldırı denemesi güvenli.
- **Kod yapısı**: katmanlı paket (`core ← domain ← ai/retrieval/storage/api`), tipli ayarlar,
  `LLMProvider` arayüzü (model değiştirmek tek bir sınıf); 12 karar kaydı.
- **Bilgi tabanı genişletmesi** (bu hafta canlıda): 13 konu × 2 dil = 26 belge, 180 parça; 2026-2027
  ücretleri, diploma, ders kaydı kuralları, UZEM, engelli öğrenciler, kütüphane, yemekhane, spor,
  psikolojik danışmanlık. 119 alıntının 119'u resmî metinle birebir kontrol edildi.
- **Kalite**: 189 otomatik test (Postgres üzerinde), mypy strict, CI'da tarayıcı testleri, CodeQL.

## Söyleyeceğim sayılar (hepsi örnek sayısıyla)

| Ölçüt | Sonuç | n |
|---|---|---|
| Kaçırılan escalation (en tehlikeli hata), gerçekçi set | **0 / 11** (iki çalıştırmada da) | 40 talep |
| Hatalı otomatik gönderim, gerçekçi set | **0** | 40 talep |
| Üç etiketin üçü de doğru, gerçekçi set | %72,5 (%57–84) | 40 talep |
| İnsansız cevaplanan, gerçekçi set | 15/40 (%24–53) | 40 talep |
| Doğru belge ilk 3 sonuçta, gerçekçi set | %100 (%89–100) | 30 talep |
| Saldırı denemelerinde güvenli sonuç | 12/12 (%76–100) | 12 deneme |

## Dürüst notlar (sormadan söyleyeceğim)

- Veri sentetik: talepleri ben yazdım veya Claude taslak yazdı, etiketleri ben verdim. Gerçek öğrenci
  verisi yok (KVKK).
- Örnekler küçük; bu yüzden aralıklar geniş. "0 kaçırılan escalation" gerçek oranın %0 olduğunu
  kanıtlamaz (11 talepte üst sınır yaklaşık %26).
- Bilgi tabanı genişletmesinin etkisi **henüz ölçülmedi**. Boşluklar dev setindeki sorulara bakılarak
  seçildi, bu yüzden dev setindeki artış iyimser olacaktır; adil ölçü yeni taleplerle yapılacak.
- Ücretsiz katman: model Gemini Flash-Lite, günlük istek sınırı var; ilk açılış yavaş.

## Beklediğim sorular

- **Neden karar yapay zekâda değil?** Çünkü test edilebilir olmalı: "acil talep asla otomatik
  gönderilmez" gibi kurallar kodda yazılı ve her biri testli (`decision.py`). Model yalnızca
  etiketler ve taslak yazar.
- **Model uydurursa?** Model önce belgeden cümle alıntılar; kod bu cümleyi belgede birebir arar.
  Bulamazsa cevap otomatik gönderilmez.
- **Neden fine-tuning değil, RAG?** Kurallar her yıl değişiyor (ücretler); RAG'de belgeyi güncellemek
  yeterli, modeli yeniden eğitmek gerekmez. Kaynak da gösterilebiliyor.
- **Test setine göre prompt ayarlamadın mı?** Hayır: iki kilitli set var, prompt'lar yalnızca dev
  setiyle geliştirildi (karar kaydı 0003).
- **Gerçekten kullanılabilir mi?** Demo seviyesinde. Üretim için: gerçek talepler, öğrenci girişi
  (SSO), e-posta bildirimi, maliyet ve hata izleme, belgelerin yıllık güncellenmesi.

## Sıradaki adımlar

1. Bilgi tabanı genişletmesini yeni taleplerle ölçmek.
2. Etiket tutarlılığı: birkaç gün sonra kendi etiketlerimi yeniden vermek.
3. Tek komutla sürümlü değerlendirme raporu ve 3-4 modelin karşılaştırılması.
4. Türkçe rapor ve v1.0.

Hocama soracaklarım: resmî BŞEÜ logosunu kullanabilir miyim? Raporun biçimi ve teslim tarihi?
