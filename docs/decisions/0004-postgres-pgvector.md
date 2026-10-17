# 0004: Postgres + pgvector

**Durum:** Kabul edildi (Phase 10, 2026-10-13). SQLite ve bellek içi aramanın yerini aldı.

## Bağlam
Talepler önce SQLite dosyasında, belge arama Python belleğinde yapılıyordu. Ücretsiz barındırma servisleri diski yeniden başlatmada sildiği için veriler kayboluyordu. Ayrıca şirketlerin gerçekte kullandığı altyapıya yakın olmak istedik.

## Karar
- Talepler, personel hesapları ve bilgi tabanı parçaları Postgres 18'de; vektör araması pgvector ile (`<=>` cosine distance).
- Embedding'ler bir kez hesaplanıp `data/kb_index.json` dosyasında sürümlenir; uygulama başlarken tabloya kopyalanır. Boş bir veritabanı API çağrısı yapmadan dolar.
- **HNSW index yok:** ~112 parça için her satırı tam taramak hızlıdır ve hiçbir sonucu kaçırmaz. Binlerce parçaya çıkılırsa eklenir.
- Şema sürümlüdür (migration'lar, veritabanı kilidiyle); testler gerçek Postgres'te, her test kendi boş şemasında çalışır.

## Sonuçlar
- Arama sonuçları eski Python aramasıyla birebir aynı ölçüldü (120 talep, aynı ilk 3 parça ve puanlar).
- Yerelde Docker (compose), üretimde Neon; aynı kod.
- Bir servis daha çalıştırmak gerekir (yerelde `docker compose up -d db`).

## Alternatifler
- SQLite: tek dosya, basit; ama ücretsiz barındırmada kalıcı değil.
- Ayrı bir vektör veritabanı (Pinecone, Qdrant): bu boyut için gereksiz karmaşıklık.
