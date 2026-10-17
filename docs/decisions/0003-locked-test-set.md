# 0003: Kilitli test seti

**Durum:** Kabul edildi (Phase 2).

## Bağlam
Kural kitabı ve prompt 80 dev talebine bakılarak düzeltildi. Aynı talepler üzerinde ölçülen skor iyimserdir (ilk denemede %85 böyle bir skordu).

## Karar
40 ayrı talep (20 TR + 20 EN), [`data/tickets/test_tickets.jsonl`](../../data/tickets/test_tickets.jsonl), **kilitlidir**: prompt'u, kural kitabını veya eşikleri ayarlamak için asla kullanılmaz; yalnızca son skor için çalıştırılır. Web sayfası ve örnek seçici yalnızca dev dosyasını okur.

## Sonuçlar
- Dev skoru yaklaşık 10 puan iyimser çıktı (üçü de doğru: dev %84,4, test %73,8). Bu fark, kilidin neden gerekli olduğunu gösterir.
- 40 talep küçüktür; güven aralıkları geniştir (yaklaşık %60–86). Sonuçlar örnek sayısıyla birlikte raporlanır.
- Test talepleri de sentetiktir; sınıf arkadaşlarından gerçek talepler daha güçlü bir test olurdu.

## Alternatifler
- Çapraz doğrulama (cross-validation): prompt ayarı elle yapıldığı için uygun değil.
