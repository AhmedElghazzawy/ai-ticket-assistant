# Etiket Tanımları

Ticket'ları etiketlemek için kural kitabı. Hem ben etiketlerken hem de classifier prompt'unda kullanılır.
Etiket ID'leri (`account_access` vb.) kodda kullanıldığı için İngilizce kalır.

## Kategoriler (7)

### `account_access` (Hesap Erişimi) → Bilgi İşlem Daire Başkanlığı
- **Buraya girer:** öğrenci bir üniversite hesabına giriş yapamıyor (OBS, üniversite e-postası, LMS): şifreyi unutma, şifre sıfırlama e-postasının gelmemesi, kilitlenen hesap, iki adımlı doğrulama (2FA) sorunları, hesabın ele geçirilmiş olabileceği durumlar.
- **Buraya girmez:** öğrenci giriş yapabiliyor ama bir sistem veya cihaz çalışmıyor → `it_support`.
- **Örnek:** "Çok fazla yanlış şifre girdiğim için OBS hesabım kilitlendi."

### `it_support` (Teknik Destek) → Bilgi İşlem Daire Başkanlığı
- **Buraya girer:** giriş yapmanın sorun olmadığı teknik problemler: Wi-Fi, kampüs bilgisayarları, yazıcılar, yazılım lisansları, LMS hataları, e-postanın senkronize olmaması.
- **Buraya girmez:** sorun giriş yapmaksa → `account_access`.
- **Örnek:** "Kütüphanede kampüs Wi-Fi bağlantısı sürekli kopuyor."

### `registration` (Ders Kaydı) → Öğrenci İşleri Daire Başkanlığı
- **Buraya girer:** bu dönem derslere kayıt: ekle-bırak, kontenjanı dolu şubeler, ön koşul hataları, ders çakışmaları, kayıt tarihleri.
- **Buraya girmez:** notlar, transkript, geçmiş kayıtlar → `academic_records`. Ödenmemiş harç nedeniyle kayıt engeli → `billing`.
- **Örnek:** "CENG 301 dersini ekleyemiyorum, sistem ön koşulu sağlamadığımı söylüyor."

### `academic_records` (Akademik Kayıtlar) → Öğrenci İşleri Daire Başkanlığı
- **Buraya girer:** öğrencinin resmi kaydı: kayıtta görünen notlar, GNO, transkript, öğrenci belgesi, mezuniyet durumu, kayıttaki kişisel bilgilerin düzeltilmesi.
- Staj evrakları da buraya girer: staj formu, SGK girişi, stajın kredi olarak sayılması.
- Akıllı Kart (öğrenci kimlik kartı) da buraya girer: kayıp, çalınma, basılmaması, hatalı bilgi.
- Disiplin soruşturması da buraya girer (Öğrenci İşleri yürütür; escalation kural 6).
- **Buraya girmez:** bu dönem ders seçme veya değiştirme → `registration`. Staj yeri bulma, kariyer tavsiyesi → `other`.
- **Örnek:** "Staj başvurum için resmi transkripte ihtiyacım var."

### `billing` (Ödemeler) → Öğrenci İşleri, İstatistik Disiplin ve Harçlar Şube Müdürlüğü
- **Buraya girer:** öğrenci ile üniversite arasındaki para işleri: harç / katkı payı, harç muafiyeti, üniversite bursları (başvuru dahil), kısmi zamanlı öğrenci ödemeleri, çift çekim, iadeler, makbuzlar, harçtan kaynaklanan kayıt engelleri.
- **Buraya girmez:** KYK yurt ücreti, KYK burs ve kredisi (devlet, üniversite değil) → yurt için `campus_life`, burs/kredi için `other`. Yemekhane fiyatları → `campus_life`.
- **Örnek:** "Bu dönem harç ücreti hesabımdan iki kez çekildi."

### `campus_life` (Kampüs Yaşamı) → Sağlık, Kültür ve Spor (SKS) Daire Başkanlığı
- **Buraya girer:** kampüsteki günlük yaşam: yemekhane, öğrenci kulüpleri ve etkinlikler, kampüse ulaşım, psikolojik danışmanlık randevusu, spor tesisleri, kütüphane (çalışma saatleri, salonlar). Kütüphane veritabanlarına kampüs dışından erişim ise `it_support`'tur. Yurt soruları da buraya girer: Bilecik'teki yurtlar KYK'ya aittir, bu yüzden cevap öğrenciyi KYK'ya yönlendirir.
- **Buraya girmez:** öğrencinin üniversiteye ödediği para → `billing`. Psikolojik danışmanlık randevusu isteyen bir ticket kriz belirtisi içerse bile `campus_life`'tır (ama `escalate = true`). Bir öğrenci veya personelden gelen tehdit ve taciz ise `other`'dır.
- **Örnek:** "Yemekhanede vejetaryen menü var mı?"

### `other` (Diğer) → Öğrenci İşleri nöbetçi personeli
- **Buraya girer:** yukarıdaki 6 kategoriye uymayan gerçek talepler: kayıp eşya, kariyer ve staj yeri bulma, KYK burs ve kredisi, engelli öğrenci birimi ve erişilebilirlik soruları, somut talebi olmayan şikâyetler, anlaşılmayan ticket'lar.
- Bir öğrenci veya personelden gelen tehdit ve taciz de buraya girer: kategori `other`'dır, asıl işi escalation (kural 1) yapar.
- **Buraya girmez:** ticket 6 kategoriden birine uyuyorsa, belirsiz olsa bile o kategori kullanılır.
- **Örnek:** "Kampüste kayıp eşya bürosu nerede?"

## Eşitlik kuralı: iki sorun içeren ticket
Öğrenciyi en acil şekilde engelleyen sorunun kategorisi seçilir. Örnek: sınavdan önce giriş yapamayan ve aynı zamanda transkript isteyen öğrenci → `account_access`.

Escalation ise ticket'taki **tüm** sorunlara bakar: sorunlardan biri escalation gerektiriyorsa `escalate = true`.

## Ek kurallar

**Altın kural:** öğrencinin üniversiteye olan ödemeleri ve üniversiteden alacakları (harç, üniversite bursu, iade) `billing`'e gider. Yemekhane fiyatları veya KYK ödemeleri gibi öğrencinin üniversite hesabıyla ilgisi olmayan para konuları `billing` değildir.

**Dil kuralı:** `language` alanı, ticket'ın çoğunun yazıldığı dildir. Türkçe ve İngilizce karışık bir ticket hangi dilde daha çok yazılmışsa o dili alır.

**Bilinen sınırlama (v1):** her ticket tek bir kategori alır. İki farklı birimi ilgilendiren ticket'larda (ör. giriş sorunu + not itirazı) sorunlardan biri yanlış birime gidebilir.

## Öncelikler (4)

Öncelik = sorunun öğrenciyi ne kadar engellediği × ne kadar acil olduğu.

| Öncelik | Anlamı | Örnek |
|---|---|---|
| `urgent` (Acil) | Güvenlik riski, tehdit, taciz veya kriz belirtisi (hafif bir dille ifade edilse bile), ele geçirilmiş olabilecek hesap veya **24 saat içinde** önemli bir şeyin engellenmesi | "Sınavım 2 saat sonra başlıyor ve LMS'e giriş yapamıyorum." |
| `high` (Yüksek) | Önemli bir şeyin **birkaç gün içinde** engellenmesi veya hatalı para çekimi | "Harç ücreti hesabımdan iki kez çekildi." |
| `medium` (Orta) | Gerçek bir sorun, ama geçici bir çözüm var veya yakın bir son tarih yok | "Kütüphanedeki yazıcı bozuk, üst kattaki çalışıyor." |
| `low` (Düşük) | Bilgi sorusu, hiçbir şey engellenmiyor | "Bahar dönemi ders kaydı ne zaman başlıyor?" |

**Kurallar:**
1. Sadece sinirli bir üslup önceliği yükseltmez. "BU ÇOK SAÇMA, ders kaydı ne zaman açılıyor??" yine `low`'dur.
2. Öncelik ve escalation birbirinden bağımsızdır. Bir ticket `low` olup yine de insana gidebilir (kibar bir not itirazı) veya `urgent` olup otomatik cevaplanabilir (sınav öncesi unutulan şifre).
3. Giriş veya erişim sorunu, ticket'ta bir son tarih belirtilmemişse `medium`'dur.

## Escalation (insana yönlendirme)

Aşağıdakilerden **herhangi biri** varsa `escalate = true`:

| # | Durum | Örnek |
|---|---|---|
| 1 | Güvenlik tehdidi, taciz veya kriz belirtisi | "Yurtta biri beni sürekli tehdit ediyor, kendimi güvende hissetmiyorum." |
| 2 | Hesabın ele geçirilmiş olabileceği | "E-postamdan benim göndermediğim mesajlar gitmiş." |
| 3 | Öğrencinin bir kural istisnasına ihtiyacı var | "Ekle-bırak süresi geçti ama hastalık nedeniyle dersi bırakmam gerekiyor." |
| 4 | Para veya resmi kayıt hatası: iade ya da düzeltme gerekiyor (öğrenci sistemin veya kaydın yanlış olduğunu söylüyor). Bir kayıt veya belge hakkında sadece soru sormak bu kural değildir. | "Harç iki kez çekildi, fazla ödememin iadesini istiyorum." / "Sistem ön koşulu almadığımı söylüyor ama dersi geçen yıl geçtim." |
| 5 | Not veya sınav itirazı, ya da sınavın geçerliliği hakkında karar gereken durum (ör. sınav sırasında sistem çöktü) | "Final notumun sisteme yanlış girildiğini düşünüyorum." / "UZEM sınav sırasında dondu, sınavım kapandı." |
| 6 | Hukuki tehdit, disiplin süreci veya cevapsız tekrarlanan başvuru | "Üçüncü kez yazıyorum, cevap gelmezse hukuki yola başvuracağım." / "Hakkımda disiplin soruşturması açılmış." |

**Escalation sebebi değildir:** öğrencinin sadece sinirli veya üzgün olması.

**Normal işlemler tek başına istisna değildir (kural 3 değil):** belgeli mazeret sınavı başvurusu, ders muafiyeti / intibak başvurusu, kayıt dondurma (akademik izin), iade hakkı hakkında soru sormak, makbuz veya belge istemek. İstisna, süresi geçmiş bir işlemi yapmak veya bir kuralın dışına çıkmak istemektir.

**Not:** `escalate` etiketi sadece bu 6 kurala bakar. `other` kategorisindeki ticket'ların insana gitmesi etiketin değil, sonraki karar adımının (decision) işidir.
