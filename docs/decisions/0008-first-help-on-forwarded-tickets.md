# 0008: Yönlendirilen taleplerde "ön bilgi"

**Durum:** Kabul edildi (2026-10-23).

## Bağlam
Phase 8 ölçümünde 40 talepten yalnızca 15'i (%37,5) insana gitmeden cevaplandı. Yönlendirilen taleplerde öğrenci yalnızca "İlgili birime iletildi" mesajını görüyordu; belgeler sorunun bir kısmını cevaplasa bile (ör. en-p17: sınav programı belgede var, servis yok). Daha önce taslak, yönlendirilen talepte öğrenciye hiç gösterilmiyordu, çünkü kontrolden geçmemişti.

## Karar
Yönlendirilen bir talepte taslak, öğrenciye **"Ön bilgi"** olarak gösterilir; ancak yalnızca şu koşulların hepsi sağlanırsa (`src/decision.py`, `show_first_help`):
- Talep **escalate edilmemiştir** (kriz, taciz, ele geçirilmiş hesap, iade, not itirazı, disiplin: bunlarda öğrenciye yapay zekâ metni gösterilmez; yalnızca birim, talep numarası ve acilse 112 düğmesi).
- Belge eşleşmesi **zayıf değildir** (konu dışı bir belge "ön bilgi" olarak görünmesin).
- Taslak **en az bir kaynak gösterir** ve gösterdiği her kaynak bu talep için gerçekten bulunan parçalardandır.

Talep yine ilgili birime gider; bir personel de cevaplar. Cevap modeli, belgeler sorunun yalnızca bir kısmını cevaplıyorsa o kısmı kaynağıyla cevaplar ve geri kalanının birime iletildiğini söyler.

## Sonuçlar
- Daha fazla öğrenci hemen yardım alır; ölçüm: `eval/pipeline_results_dev.json` (`helped_now`, `first_help_on_escalated` boş kalmalıdır).
- Escalate edilmesi gerekip sınıflandırıcının kaçırdığı bir talepte ön bilgi gösterilebilir. Bu yüzden "kaçırılan escalation" en önemli ölçüt olmaya devam eder (Phase 8: 0/11).
- Kategori `other` ve `urgent` talepler de ön bilgi alabilir: kaynaklı bir cevap öğrenciye bugün yardım eder, personel ayrıca ilgilenir.

## Alternatifler
- Escalate edilen taleplerde de taslağı göstermek: daha fazla yardım, ama hassas durumlarda kontrol edilmemiş yapay zekâ metni. Reddedildi.
- Yalnızca belgeden kelimesi kelimesine alınan cümleleri (evidence) göstermek, escalate edilen taleplerde bile: daha güvenli olabilir, ileride değerlendirilecek.
- Hiç göstermemek (eski durum): güvenli ama öğrenci yardım almadan bekler.
