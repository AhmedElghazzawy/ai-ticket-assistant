%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% BUB.cls - Bilecik Şeyh Edebali Üniversitesi, Bilgisayar Mühendisliği
%% Bitirme / Tasarım Çalışması rapor sınıfı.
%%
%% Bölümün resmî Overleaf şablonunun (Salim Ceyhan, Uğur Yüzgeç; CC BY 4.0)
%% PDF çıktısı ve "Bitirme Tezi/Tasarım Çalışması Yazım Kılavuzu" (11.02.2025)
%% esas alınarak yeniden kurulmuştur:
%%   A4; kenar boşlukları üst 3 cm, alt 3 cm, sol 2,5 cm, sağ 2,5 cm;
%%   Times, 12 punto; 1,5 satır aralığı; paragraf girintisi 1,25 cm;
%%   ana başlıklar büyük harf ve ortalı, alt başlıklar ilk harfi büyük.
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{BUB}[2025/02/11 BSEU BM Bitirme/Tasarim Calismasi raporu]
\LoadClass[12pt,a4paper,oneside]{report}

\RequirePackage[T1]{fontenc}
\RequirePackage[utf8]{inputenc}
\RequirePackage[turkish]{babel}
\AtBeginDocument{\shorthandoff{=}}
\RequirePackage{mathptmx}            % Times (şablonda NimbusRomNo9L)
\RequirePackage[scaled=0.92]{helvet}
\RequirePackage{courier}
\RequirePackage{amsmath,amssymb}
\RequirePackage[top=3cm,bottom=3cm,left=2.5cm,right=2.5cm]{geometry}
\RequirePackage{setspace}
\RequirePackage{graphicx}
\RequirePackage[table]{xcolor}
\RequirePackage{titlesec}
\RequirePackage{tocloft}
\RequirePackage{caption}
\RequirePackage{float}
\RequirePackage{booktabs,multirow,array,tabularx,longtable}
\RequirePackage{enumitem}
\RequirePackage{listings}
\RequirePackage{algorithm}
\RequirePackage{algpseudocode}
\RequirePackage{xurl}
\RequirePackage[hidelinks]{hyperref}

\onehalfspacing
\setlength{\emergencystretch}{3em}
\urlstyle{same}
\setlength{\parindent}{1.25cm}
\setlength{\parskip}{6pt}
\setlist{itemsep=1pt,topsep=4pt}
\raggedbottom

%--- Rapor bilgileri ------------------------------------------------------
\def\@baslik{}        \newcommand{\baslik}[1]{\def\@baslik{#1}}
\def\@baslikEN{}      \newcommand{\baslikEN}[1]{\def\@baslikEN{#1}}
\def\@ogrenci{}       \newcommand{\ogrenci}[1]{\def\@ogrenci{#1}}
\def\@ogrencino{}     \newcommand{\ogrencino}[1]{\def\@ogrencino{#1}}
\def\@danisman{}      \newcommand{\danisman}[1]{\def\@danisman{#1}}
\def\@ders{}          \newcommand{\ders}[1]{\def\@ders{#1}}
\def\@raportur{}      \newcommand{\raportur}[1]{\def\@raportur{#1}}
\def\@yil{}           \newcommand{\yil}[1]{\def\@yil{#1}}
\def\@tarih{}         \newcommand{\tarih}[1]{\def\@tarih{#1}}
\newcommand{\BaslikTR}{\@baslik}
\newcommand{\BaslikEN}{\@baslikEN}
\newcommand{\OgrenciAdi}{\@ogrenci}
\newcommand{\RaporTarihi}{\@tarih}

%--- Başlıklar: "1 GİRİŞ" ortalı, büyük, koyu; bölüm yeni sayfadan --------
\titleformat{\chapter}[block]{\centering\bfseries\large}{\thechapter}{0.6em}{\MakeUppercase}
\titlespacing*{\chapter}{0pt}{0pt}{18pt}
\titleformat{\section}{\bfseries\large}{\thesection}{1.2em}{}
\titlespacing*{\section}{0pt}{18pt}{8pt}
\titleformat{\subsection}{\bfseries\normalsize}{\thesubsection}{1em}{}
\titlespacing*{\subsection}{0pt}{14pt}{6pt}
\titleformat{\subsubsection}{\bfseries\itshape\normalsize}{\thesubsubsection}{1em}{}
\setcounter{secnumdepth}{3}
\setcounter{tocdepth}{2}

% Numarasız ön sayfa başlığı (ÖZET, ÖNSÖZ, ...): ortalı, büyük, koyu
\newcommand{\onbaslik}[1]{%
  \chapter*{#1}\addcontentsline{toc}{chapter}{#1}}

%--- Dizinler ------------------------------------------------------------
\renewcommand{\contentsname}{İÇİNDEKİLER}
\renewcommand{\listfigurename}{ŞEKİLLER DİZİNİ}
\renewcommand{\listtablename}{TABLOLAR DİZİNİ}
\renewcommand{\bibname}{KAYNAKLAR}
\renewcommand{\cfttoctitlefont}{\hfill\large\bfseries}
\renewcommand{\cftaftertoctitle}{\hfill}
\renewcommand{\cftloftitlefont}{\hfill\large\bfseries}
\renewcommand{\cftafterloftitle}{\hfill}
\renewcommand{\cftlottitlefont}{\hfill\large\bfseries}
\renewcommand{\cftafterlottitle}{\hfill}
\setlength{\cftbeforetoctitleskip}{0pt}
\setlength{\cftbeforeloftitleskip}{0pt}
\setlength{\cftbeforelottitleskip}{0pt}
\renewcommand{\cftchapfont}{\bfseries}
\renewcommand{\cftchappagefont}{\bfseries}
\renewcommand{\cftfigpresnum}{Şekil~}
\renewcommand{\cfttabpresnum}{Tablo~}
\setlength{\cftfignumwidth}{5.5em}
\setlength{\cfttabnumwidth}{5.5em}
\setlength{\cftfigindent}{0pt}
\setlength{\cfttabindent}{0pt}
\setlength{\cftbeforefigskip}{5pt}
\setlength{\cftbeforetabskip}{5pt}

%--- Şekil ve tablo yazıları: "Şekil 1.1: ..." ---------------------------
\addto\captionsturkish{%
  \renewcommand{\figurename}{Şekil}%
  \renewcommand{\tablename}{Tablo}%
  \renewcommand{\contentsname}{İÇİNDEKİLER}%
  \renewcommand{\listfigurename}{ŞEKİLLER DİZİNİ}%
  \renewcommand{\listtablename}{TABLOLAR DİZİNİ}%
  \renewcommand{\bibname}{KAYNAKLAR}}
\captionsetup{labelsep=colon,font={small,singlespacing},justification=centering,skip=6pt}
\captionsetup[table]{position=top}
\renewcommand{\thefigure}{\thechapter.\arabic{figure}}
\renewcommand{\thetable}{\thechapter.\arabic{table}}
\floatname{algorithm}{Algoritma}

%--- Kod gösterimi (şablondaki gibi satır numaralı, renkli) --------------
\definecolor{kodgri}{gray}{0.96}
\definecolor{kodkirmizi}{RGB}{176,32,40}
\definecolor{kodmavi}{RGB}{28,84,160}
\definecolor{kodyesil}{RGB}{40,120,60}
\lstset{
  basicstyle=\ttfamily\footnotesize\linespread{1.0}\selectfont,
  keywordstyle=\color{kodmavi}\bfseries,
  stringstyle=\color{kodkirmizi},
  commentstyle=\color{kodyesil}\itshape,
  numbers=left, numberstyle=\tiny\color{gray}, numbersep=8pt,
  backgroundcolor=\color{kodgri}, frame=single, rulecolor=\color{gray!40},
  breaklines=true, columns=fullflexible, keepspaces=true, showstringspaces=false,
  xleftmargin=1.6em, framexleftmargin=1.4em, aboveskip=8pt, belowskip=8pt,
  captionpos=t, tabsize=4,
  literate={ç}{{\c{c}}}1 {Ç}{{\c{C}}}1 {ğ}{{\u{g}}}1 {Ğ}{{\u{G}}}1
           {ı}{{\i}}1 {İ}{{\.{I}}}1 {ö}{{\"o}}1 {Ö}{{\"O}}1
           {ş}{{\c{s}}}1 {Ş}{{\c{S}}}1 {ü}{{\"u}}1 {Ü}{{\"U}}1
           {â}{{\^a}}1 {î}{{\^i}}1 {—}{{---}}1 {→}{{$\rightarrow$}}1
}
\renewcommand{\lstlistingname}{Kod}
\renewcommand{\lstlistlistingname}{KODLAR DİZİNİ}

%--- Kapak (Tasarım Çalışması: jüri imza sayfası yoktur) -----------------
\newcommand{\kapaksayfasi}{%
  \begin{titlepage}
  \thispagestyle{empty}
  \begin{center}
    {\bfseries T.C.\\[2pt] BİLECİK ŞEYH EDEBALİ ÜNİVERSİTESİ\\[2pt]
     MÜHENDİSLİK FAKÜLTESİ\\[2pt] BİLGİSAYAR MÜHENDİSLİĞİ BÖLÜMÜ\par}
    \vspace{1.2cm}
    \includegraphics[width=3.6cm]{sekiller/logomuz.png}\par
    \vspace{1.6cm}
    {\setstretch{1.5}\bfseries\large \@baslik\par}
    \vspace{0.6cm}
    {\bfseries \@raportur\par}
    \vspace{1.6cm}
    {\bfseries \@ogrenci\\[2pt] \@ogrencino\par}
    \vfill
    {\bfseries DANIŞMAN\\[2pt] \@danisman\par}
    \vspace{1.4cm}
    {\bfseries \@ders\par}
    \vspace{1.4cm}
    {\bfseries BİLECİK \@yil\par}
  \end{center}
  \end{titlepage}}

%--- Bildirim ------------------------------------------------------------
\newcommand{\bildirimsayfasi}{%
  \chapter*{BİLDİRİM}
  Bu çalışmada bütün bilgilerin etik davranış ve akademik kurallar çerçevesinde elde edildiğini
  ve yazım kurallarına uygun olarak hazırlanan bu çalışmada bana ait olmayan her türlü ifade ve
  bilginin kaynağına eksiksiz atıf yapıldığını bildiririm.
  \vspace{1.2cm}
  \begin{center}\bfseries DECLARATION\end{center}
  I hereby declare that all information in this document has been obtained and presented in
  accordance with academic rules and ethical conduct. I also declare that, as required by these
  rules and conduct, I have fully cited and referenced all materials and results that are not
  original to this work.
  \imzablogu}

\newcommand{\imzablogu}{%
  \par\vspace{1.6cm}
  \hfill\begin{tabular}{c}\bfseries İmza\\ \bfseries \@ogrenci\\ \bfseries Tarih: \@tarih\end{tabular}}

\endinput
