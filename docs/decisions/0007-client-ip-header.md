# 0007: Rate limit için ziyaretçi adresi

**Durum:** Kabul edildi (2026-10-12), canlıda doğrulandı (2026-10-17).

## Bağlam
Her talep yaklaşık 3 Gemini çağrısıdır; bir bot ücretsiz kotayı bitirebilir. Bu yüzden ziyaretçi başına sınır var (dakikada 5, günde 30 talep; 20 hatalı girişte 15 dakika bekleme). Bir proxy arkasında tüm istekler proxy'den geliyormuş gibi görünür. `X-Forwarded-For` başlığının en soldaki değerini ziyaretçi kendisi yazabilir: bir bot her istekte yeni bir adres uydurarak sınırları atlatabilir.

## Karar
Adres tek bir yerde okunur (`client_ip()`). Hangi başlığa güvenileceği bir ayardır (`CLIENT_IP_HEADER`): varsayılan boş, yani hiçbir başlığa güvenilmez. Render'da Cloudflare'in koyduğu `CF-Connecting-IP` kullanılır. IP adresi kişisel veridir: yalnızca bellekte tutulur, diske veya loglara yazılmaz.

## Sonuçlar
Canlı test (2026-10-17):
- Kendi `CF-Connecting-IP` başlığını gönderen istek Cloudflare tarafından reddedildi ("error code: 1000"): bu başlık taklit edilemez.
- Her biri farklı sahte `X-Forwarded-For` taşıyan 20 hatalı girişten sonra 429 döndü: sahte başlık hiçbir şey değiştirmedi.
- Sayaçlar bellekte olduğu için tek sunucuda çalışır; birden fazla sunucuda ortak bir sayaç (ör. Redis) gerekir.

## Alternatifler
- `FORWARDED_ALLOW_IPS="*"`: en soldaki, taklit edilebilir adresi alır; reddedildi.
