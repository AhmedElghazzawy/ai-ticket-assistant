# 0017: Talep geçmişi: değiştirilemeyen bir denetim kaydı (audit trail)

**Durum:** Kabul edildi (2026-11-14).

## Bağlam
Bir personel talebi yanıtladığında veya başka birime aktardığında veritabanı **kimin** yaptığını
saklamıyordu; aktarmada eski birim de kayboluyordu. Bu bilgi yalnızca loglardaydı ve loglar kısa süre
tutulur, aranması zordur. Bir yardım masasında "bu talebe kim, ne zaman, ne yaptı?" sorusunun cevabı
şikâyetlerde, devirlerde ve KVKK incelemelerinde gerekir.

## Karar
- Yeni tablo `ticket_events` (migration 6): `ticket_id`, `at`, `kind` (`created`, `human_requested`,
  `replied`, `reassigned`), `staff_id` (sistem veya öğrenci için NULL) ve `detail` (yalnızca birim
  kimlikleri: `from`, `to`; öğrenci metni asla).
- Olay, değişiklikle **aynı SQL ifadesinde** yazılır (data-modifying CTE: `WITH ... UPDATE ... RETURNING`
  ardından `INSERT INTO ticket_events`). Bağlantılar autocommit olduğu için ayrı bir transaction'a gerek
  yoktur ve bir değişiklik olayı olmadan var olamaz. Reddedilen bir değişiklik (ikinci yanıt, yanıtlanmış
  talepte uzman isteği, aynı birime aktarma) olay yazmaz.
- Geçmiş yeniden yazılamaz: bir veritabanı trigger'ı her `UPDATE`'i reddeder ("append-only"). Silme
  yalnızca talep silinince olur (`ON DELETE CASCADE`: demo kuyruğunun sıfırlanması).
- Eski talepler için geçmiş, zaten bilinen sütunlardan kurulur (`created_at`, `human_requested_at`,
  `handled_at`); kimin yanıtladığı hiç saklanmadığı için bilinmez kalır.
- `GET /api/staff/tickets/{id}/history`, talebin kendisiyle aynı birim kuralını kullanır. Personel talep
  sayfasında "Geçmiş" zaman çizelgesini görür.

## Sonuçlar
- Her personel eylemi kişiye bağlanır; aktarmaların izi kalır; öğrencinin uzman isteği de görünür.
- Yeni bir eylem türü eklemek: `kind` CHECK listesine yeni bir migration ile eklemek, depolama
  fonksiyonunda olayı aynı ifadede yazmak ve bir test.
- Maliyet: her değişiklikte bir satır daha; bu ölçekte önemsiz. İndeks `(ticket_id, at, id)`.

## Alternatifler
- Yalnızca loglar: aranamaz, kısa ömürlü, veritabanıyla tutarlı olduğu garanti edilemez. Reddedildi.
- `tickets` tablosuna `handled_by` ve `reassigned_by` sütunları: yalnızca son durumu tutar, geçmişi değil.
  Reddedildi.
- Tam event sourcing (talebin durumu olaylardan hesaplanır): bu proje için gereksiz karmaşıklık;
  `tickets` güncel durum, `ticket_events` geçmiş olarak kalır. Reddedildi.
- Uygulama kodunda iki ayrı ifade ve bir transaction: doğru olur ama tek ifade daha basit ve atomik.
