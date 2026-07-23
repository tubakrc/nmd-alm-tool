# NMD Davranışsal Modelleme Aracı

Vadesiz mevduatların (Non-Maturity Deposits) faiz oranı riski yönetiminde
**davranışsal modellenmesini** gösteren bir ALM/IRRBB showcase projesi.

## Neden bu proje?

Vadesiz mevduatların sözleşmesel vadesi yoktur — müşteri parasını istediği an
çekebilir. Ancak pratikte bu paranın büyük bir kısmı (core) bankada yıllarca
kalır. Bu projeyi sözleşmesel vadeye göre modellersen (yani "overnight" kabul
edersen), bankanın gap/EVE/NII risk profilini ciddi şekilde yanlış gösterirsin.

Bu araç, sentetik (veya kendi yüklediğiniz) mevduat verisinden:

1. **Core / Volatile ayrımı** (rolling minimum yöntemi)
2. **Pass-through tahmini** (mevduat faizinin politika faizine duyarlılığı, OLS regresyon)
3. **Replicating portfolio** (davranışsal vade dağılımı, laddered portfolio mantığı)
4. **EVE duyarlılık karşılaştırması** (sözleşmesel vs davranışsal yaklaşım, Basel standart şokları)

çıkararak, bu farkın pratikte nasıl bir risk algısı farkı yarattığını gösterir.

## Kurulum

```bash
pip install -r requirements.txt
```

## Çalıştırma

```bash
cd src
streamlit run app.py
```

## Proje Yapısı

```
nmd-alm-tool/
├── data/
│   └── synthetic_nmd_data.csv      # örnek üretilmiş veri
├── src/
│   ├── data_generator.py           # sentetik veri üretici (2 segment)
│   ├── core_volatile.py            # core/volatile ayrımı (rolling min)
│   ├── pass_through.py             # pass-through OLS regresyonu
│   ├── replicating_portfolio.py    # davranışsal vade dağılımı
│   ├── eve_calculator.py           # EVE duyarlılık karşılaştırması
│   └── app.py                      # Streamlit dashboard
├── requirements.txt
└── README.md
```

## Kendi Verinizi Kullanma

Dashboard'da "Kendi CSV dosyamı yükle" seçeneğini seçip şu kolonlara sahip bir
CSV yükleyebilirsiniz:

| Kolon | Açıklama |
|---|---|
| date | Tarih (aylık) |
| segment | Mevduat segmenti adı |
| balance | Bakiye |
| deposit_rate | Mevduat faiz oranı (%) |
| policy_rate | Politika/piyasa faiz oranı (%) |

## Metodolojik Notlar

- **Core/Volatile ayrımı**: EBA/Basel IRRBB rehberlerinde referans verilen
  basit rolling-minimum yaklaşımı kullanılmıştır. Daha gelişmiş alternatifler
  arasında güven aralığı bazlı (VaR) yöntemler ve Markov zinciri modelleri
  bulunur.
- **EVE hesaplaması**: Bu araçtaki EVE duyarlılığı, öğretici/gösterim amaçlı
  basitleştirilmiş bir duration yaklaşımıdır (modified duration ≈ ağırlıklı
  ortalama vade). Tam bir Basel IRRBB Standardised Outlier Test (SOT)
  hesaplaması iskonto faktörleri, nakit akışı zamanlaması ve düzenleyici
  vade üst sınırlarını (NMD için ortalama vade ≤ 5 yıl gibi) içerir.
- **Pass-through regresyonu**: Basit OLS first-difference modeli kullanılmıştır.
  Daha gelişmiş bir yaklaşım, kısa/uzun dönem pass-through'u ayıran bir
  Error Correction Model (ECM) olabilir.
