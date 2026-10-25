# 0002: Otomatik gönderim kararı sade kod

**Durum:** Kabul edildi (Phase 4; "acil → insan" kuralı sonradan eklendi).

## Bağlam
En tehlikeli hata, bir insanın görmesi gereken bir talebe otomatik cevap gitmesidir. LLM hata yapabilir ve kararını tam açıklayamaz. Benzerlik puanları tek başına yeterli değildir: cevabı olmayan bir talep 0,730, cevaplanabilir bir talep 0,635 alabildi.

## Karar
Karar [`src/helpdesk/domain/decision.py`](../../src/helpdesk/domain/decision.py) içinde sade Python kodudur. Cevap yalnızca şu 6 kontrolün **hepsi** geçerse otomatik gönderilir:
1. kategori `other` değil,
2. model escalation istemedi,
3. öncelik `urgent` değil (acil bir durumda bir insan bugün harekete geçebilir),
4. en iyi belge eşleşmesi ≥ 0,65 (yalnızca alt sınır),
5. model belgelerin talebi cevapladığını söyledi (`covered`),
6. cevap, gerçekten bulunan bir belgeyi kaynak gösteriyor.

Biri bile kalırsa talep, taslak ve kalma nedenleriyle birlikte ilgili birime gider.

## Sonuçlar
- Her kural bir testle korunur (`tests/test_decision.py`); bir kural kaldırılırsa testler kırılır.
- Personel, talebin neden otomatik gönderilmediğini görür (nedenler kaydedilir).
- Temkinlidir: kilitli testte 40 talebin yalnızca 3'ü otomatik gönderildi. Daha fazla otomasyon için önce daha fazla kanıt gerekir.
- En zayıf halka 5. kontroldür (modelin kendi yargısı); kilitli testteki tek hatalı otomatik gönderim buradan geldi.

## Alternatifler
- LLM'in "gönder / gönderme" demesi: açıklanamaz ve test edilemez.
- Yalnızca benzerlik eşiği: puan aralıkları çakıştığı için güvenilmez.
