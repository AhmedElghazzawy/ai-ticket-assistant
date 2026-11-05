# 0013: Doğrudan cevap ve etiketli "genel bilgi"

**Durum:** Kabul edildi (2026-11-05). ADR 0008'i genişletir; 0008'in escalation kuralı aynen kalır.

## Bağlam
Asistan neredeyse her soruyu insana yönlendiriyordu. Örnek: "GPA nasıl hesaplanır?" ve "öğrenci kartım
çalışmıyor" soruları yalnızca "İlgili birime iletildi" cevabı aldı. Dev setteki son pipeline eval'de
(2026-10-24, 80 ticket) `not_covered` 56 ticket'ta başarısız oldu ve cevaplanabilir 33 ticket'ın yalnızca
17'si otomatik gönderildi. Cevaplar tek tek okununca üç neden çıktı:
1. **Bilgi tabanı boşluğu:** harf notu tablosu ve not ortalaması formülü yoktu (Yönetmelik Madde 22-25).
2. **Hep-ya-hiç `covered`:** model asıl soruyu kaynağıyla cevaplasa bile, öğrencinin sorduğu küçük bir
   yan ayrıntı (ör. "ne kadar sürer?") belgede yoksa `covered = false` diyordu.
3. **Belgeler hiçbir şey söylemeyince** öğrenci hiçbir yardım almıyordu; Claude veya Gemini ile konuşan
   biri ise en azından genel, pratik bir tavsiye alır.

## Karar
Cevap modeli iki ayrı alan döner (`domain/outputs.py`, `Answer`):
- `reply`: yalnızca resmî kurallardan gelen bilgi. Asıl soruyu doğrudan cevaplar (kural, sayı, adım,
  hesap). `covered`, artık **asıl soru** kurallarla cevaplanıyorsa `true` olur. Kontroller (`decision.py`)
  değişmedi: alıntı kurallarda yoksa, kaynak gösterilmiyorsa veya eşleşme zayıfsa otomatik gönderilmez.
- `general_help`: kuralların cevaplamadığı kısım için genel, pratik tavsiye (denenecekler, hazırlanacak
  belgeler, birime ne sorulacağı). BŞEÜ'ye özgü bilgi (ücret, tarih, birim, telefon, bağlantı, prosedür)
  içermez. **Etiketi model değil sayfa koyar:** "Genel bilgi: BŞEÜ'nün resmî belgelerinden değildir."

Genel bilgi öğrenciye `show_general_help` ile gösterilir: talep **escalate edilmemişse** ve ticket'ın
içine sahte bir kural yerleştirilmemişse (`ungrounded`). Zayıf eşleşme ve kaynaksızlık genel bilgiyi
engellemez, çünkü genel bilgi hiçbir kaynağa dayandığını iddia etmez. Talep yine birime gider; sayfa
cevabı önce, "Talebiniz ayrıca ilgili birime iletildi" notunu sonra gösterir.

Escalate edilen taleplerde (kriz, taciz, ele geçirilmiş hesap, iade, not itirazı, disiplin) öğrenciye
yine yapay zekâ metni gösterilmez (ADR 0008): bu durumlarda doğru cevabı bir insan verir.

## Sonuçlar
- Belgelerin cevapladığı sorular doğrudan cevaplanır; belgelerin cevaplamadığı sorularda öğrenci beklerken
  de yardım alır.
- Yeni risk: genel bilgide modelin BŞEÜ'ye özgü bir bilgi uydurması. Kod bunu tam yakalayamaz (genel
  bilginin kaynağı yoktur). Önlemler: prompt kuralı, sayfadaki etiket, personel sayfasında görünmesi ve
  eval'de `general_help` metinlerinin okunması. `general_help_on_escalated` boş kalmalıdır.
- `covered` gevşedi: otomatik gönderilen cevaplar artmalı, ama `unsafe_auto_sends` boş kalmalıdır. Ölçüm:
  `eval/pipeline_results_dev.json` (yalnızca dev set; kilitli setlerde ayar yapılmaz).
- Veritabanı: migration 4, `tickets.general_help` sütunu (eski satırlarda boş).

## Alternatifler
- Kuralları gevşetip tek bir serbest cevap: tek kutu daha doğal görünür, ama resmî ve genel bilgi
  karışır; öğrenci hangisinin resmî olduğunu bilemez. Reddedildi.
- Genel bilgiyi escalate edilen taleplerde de göstermek: kriz ve taciz durumlarında kontrol edilmemiş
  yapay zekâ metni. Reddedildi (ADR 0008).
- `MIN_SCORE` eşiğini düşürmek: sorun eşik değildi; yanlış otomatik gönderim riskini artırırdı. Reddedildi.
