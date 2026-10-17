# 0005: Barındırma: Render + Neon

**Durum:** Kabul edildi (2026-10-17). İlk tercih Fly.io'nun yerini aldı.

## Bağlam
Hocamın ve başkalarının sistemi bir bağlantıyla deneyebilmesi için canlı bir demo gerekiyordu. Bütçe: sıfır. Veriler AB içinde, Türkiye'ye yakın olmalıydı.

## Karar
- **Render**, ücretsiz web servisi, Frankfurt: Dockerfile'dan derler, otomatik HTTPS. Ayarlar `render.yaml` içinde.
- **Neon**, ücretsiz Postgres, Frankfurt (`aws-eu-central-1`): pgvector destekli, kart gerektirmez.
- Gizli değerler (`GEMINI_API_KEY`, `DATABASE_URL`) yalnızca Render'ın panelinde; repoda asla yok.

## Sonuçlar
- Maliyet sıfır. Canlı: https://bseu-helpdesk.onrender.com
- Ücretsiz servis 15 dakika ziyaretçi olmazsa uyur; ilk açılış yaklaşık 1 dakika sürer. Neon da boştayken uyur ve bağlantıları kapatır; bağlantı havuzu her bağlantıyı kullanmadan önce kontrol eder (testle korunur).
- Servis Render CLI ile oluşturuldu, Blueprint olarak bağlı değil: `render.yaml` içindeki "yalnızca CI geçince deploy et" ayarı henüz etkin değil.
- Üretim için: uyumayan ücretli plan, izleme (monitoring) ve gerçek üniversitede kurum içi sunucu (KVKK).

## Alternatifler
- Fly.io (aylık ~$4, kalıcı disk): ilk öneriydi; Postgres'e geçince ücretsiz Render + Neon yeterli oldu.
- Railway, Azure for Students: AB bölgesi belirsiz veya ağ dosya sisteminde SQLite güvenilmez.
