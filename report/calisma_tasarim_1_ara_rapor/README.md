# Çalışma Tasarım 1 – Ara Rapor

BM331 Bilgisayar Mühendisliği Tasarım Çalışması I dersi için ara rapor (Türkçe, LaTeX).

- **PDF:** [`calisma_tasarim_1_ara_rapor.pdf`](calisma_tasarim_1_ara_rapor.pdf) (kısaltılmış, 30 sayfa).
  İlk, 47 sayfalık tam sürüm [`calisma_tasarim_1_ara_rapor_tam_surum.pdf`](calisma_tasarim_1_ara_rapor_tam_surum.pdf)
  dosyasındadır; kaynağı `d95d87e` commit'indedir.
- **Şablon:** Bölümün resmî Bitirme/Tasarım Çalışması Overleaf şablonunun dosya düzeni
  (`0main.tex`, `1kapak.tex`, ... `17kaynaklar.tex`) korunmuştur. `BUB.cls`, şablonun PDF çıktısı ve
  "Bitirme Tezi/Tasarım Çalışması Yazım Kılavuzu" (11.02.2025) esas alınarak yeniden kurulmuştur
  (A4, kenar 3/3/2,5/2,5 cm, Times 12 pt, 1,5 satır, girinti 1,25 cm). Tasarım çalışması olduğu için
  jüri imza sayfası yoktur.
- **Derleme:** `latexmk -pdf 0main.tex` (pdfLaTeX + BibTeX, IEEEtran). Overleaf'e yüklenip
  `0main.tex` ana dosya seçilerek de derlenebilir.
- **Şekiller:** ekran görüntüleri `sekiller/` klasöründedir; diyagram ve grafikler TikZ/pgfplots ile
  çizilmiştir ve sayılar `eval/` klasöründeki kayıtlı sonuçlardan alınmıştır.
