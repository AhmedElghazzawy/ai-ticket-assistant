# 0016: Öğrenci otomatik cevaptan sonra bir uzman isteyebilir

**Durum:** Kabul edildi (2026-11-14). ADR 0009'u (gizli kod) kullanır; 0002, 0008 ve 0013 değişmez.

## Bağlam
Bir talebi kimin cevaplayacağına yalnızca sistem karar veriyordu. Otomatik cevaplanan bir talep
(`auto_sent`) hemen kapanıyor ve hiçbir personel onu görmüyordu. Cevap öğrencinin sorununu çözmediyse
öğrencinin bir insana ulaşma yolu yoktu: "işime yaramadı" düğmesi yalnızca oyu kaydediyordu. Gerçek bir
yardım masasında yapay zekâ kolay talepleri cevaplar, ama bir insan her zaman bir tık uzaklıktadır.

## Karar
- Her otomatik cevabın altında ve "Taleplerim" sayfasında **"Sorununuz çözülmedi mi? Bir uzmana gönder"**
  düğmesi vardır. Düğme, talebin gideceği birimin adını gösterir.
- `POST /api/tickets/{id}/human` (gövdede gizli kod): yalnızca `auto_sent` bir talep `open` olur ve
  kategorisine göre **kodun seçtiği** birimin kuyruğuna girer (`domain/offices.py`). Birimi model seçmez.
  `human_requested_at` zamanı kaydedilir (migration 5).
- Zaten `open` olan bir talepte (bir insan zaten bakıyor) veya tekrar istekte hiçbir şey değişmez.
  Personelin cevapladığı (`handled`) bir talep yeniden açılamaz (409): aksi hâlde personel sonsuz bir
  döngüye girebilirdi; öğrenci yeni bir talep açabilir.
- Yanlış kod ve var olmayan numara aynı 404'ü alır; uç nokta, sorgulama ile aynı ziyaretçi sınırını
  kullanır (ADR 0009). Loglarda yalnızca talep numarası vardır, metin veya kod yoktur.
- `auto_send` değişmez: modelin ve kuralların **kararını** kaydeder. `status` talebin **şu an** nerede
  olduğunu söyler. Böylece eval'ler ve istatistikler sistemin kararını doğru ölçmeye devam eder.
- Personel kuyrukta ve talep sayfasında "Otomatik cevaptan sonra öğrenci uzman istedi" işaretini görür;
  öğrenci "Taleplerim"de aldığı otomatik cevabı görmeye devam eder. İstatistikler sayfası kaç otomatik
  cevabın uzmana gönderildiğini gösterir (otomatik cevap yetmedi sinyali).

## Sonuçlar
- Otomatik cevap yanlış veya eksikse öğrenci takılı kalmaz; bu sistemin en önemli güvenlik ağıdır.
- "Otomatik cevaplanan" oranı artık "yapay zekâ ile kapanan" anlamına gelir: uzmana gönderilen talepler
  bekleyen olarak sayılır. Uzmana gönderilme sayısı gerçek kullanımda cevap kalitesinin ölçüsüdür, ama
  küçük örneklemdir (her zaman n ile gösterilir).
- Kötüye kullanım riski: bir öğrenci her cevabı uzmana gönderebilir. Personel yükü, talep başına sınır
  (dakikada 5 talep, günlük üst sınır) ile zaten sınırlıdır. Gerçek kurulumda öğrenci girişi (SSO) gerekir.
- Yapay zekâ çağrısı yoktur: özelliğin maliyeti sıfırdır.

## Alternatifler
- "İşime yaramadı" oyunu otomatik olarak personele göndermek: oy ile istek karışır; öğrenci yalnızca
  geri bildirim vermek isteyebilir. Reddedildi; iki ayrı ve açık eylem tercih edildi.
- Modelin "uzmana gönder" demesine izin vermek: yönlendirme kararı koddadır (ADR 0002); model yalnızca
  tavsiye verir. Reddedildi.
- Personelin cevapladığı talebi yeniden açmak: takip mesajları ayrı ve daha büyük bir özelliktir
  (roadmap). Şimdilik reddedildi.
