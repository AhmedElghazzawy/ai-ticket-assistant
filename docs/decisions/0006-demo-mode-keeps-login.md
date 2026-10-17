# 0006: Personel girişi kalır, ayrıca demo modu

**Durum:** Kabul edildi (2026-10-12).

## Bağlam
Personel sayfaları öğrencilerin mesajlarını gösterir (kişisel veri, KVKK). Canlı demoda hocamın personel panelini hesap olmadan görebilmesi isteniyordu. "Girişi şimdilik kaldıralım" önerisi düşünüldü.

## Karar
Giriş kalır (Argon2id şifreler, HttpOnly çerez oturumları, birime göre yetki, hatalı giriş sınırı, CSRF koruması). Ayrıca `DEMO_MODE=true` olan sitede "Demo olarak dene" düğmesi, **yalnızca örnek talepleri** gören bir demo personeli olarak giriş yapar. Örnek talepler veri setinden ve gerçek sonuçlarından üretilir, her demo girişinde sıfırlanır.

## Sonuçlar
- Herkes personel panelini deneyebilir; gerçek ziyaretçilerin mesajları demo hesabına asla görünmez (canlıda doğrulandı).
- Herkese açık kayıt yoktur; hesaplar yalnızca `tools/add_staff.py` ile açılır. Gerçek bir kurulumda üniversitenin tek oturum açma (SSO) sistemi kullanılmalıdır.

## Alternatifler
- Girişi kaldırmak: internetteki herkes her mesajı okuyabilirdi.
- Hocama ayrı bir hesap açmak: mümkün ama her ziyaretçi için çalışmaz.
