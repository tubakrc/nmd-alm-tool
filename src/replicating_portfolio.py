"""
Replicating Portfolio - davranışsal vade dağılımı oluşturma.

Core mevduat kısmı, "laddered portfolio" (merdiven portföy) mantığıyla
belirli vade dilimlerine bölünür. Bu, core kısmın aslında uzun vadeli ve
istikrarlı bir fonlama kaynağı olarak davrandığını varsayar.

Volatile kısım ise tamamen kısa vadeli (overnight/1 ay) kabul edilir,
çünkü herhangi bir an çekilebilir.

Vade dilimleri ve ağırlıkları, EBA/Basel IRRBB rehberlerindeki tipik
NMD replicating portfolio örneklerine benzer şekilde seçilmiştir
(pass_through düşükse -> daha uzun vadeye kaydırılır, yüksekse -> daha kısa).
"""

import pandas as pd

# Vade dilimleri (ay cinsinden üst sınır) ve temsil eden orta nokta (yıl)
TENOR_BUCKETS = [
    ("1 Ay", 1, 1 / 24),
    ("3 Ay", 3, 2 / 12),
    ("6 Ay", 6, 4.5 / 12),
    ("1 Yıl", 12, 0.75),
    ("2 Yıl", 24, 1.5),
    ("3 Yıl", 36, 2.5),
    ("5 Yıl", 60, 4.0),
]


def _weights_for_pass_through(beta: float) -> list:
    """
    Pass-through katsayısına göre core kısmın vade dilimlerine dağılım ağırlıklarını üretir.

    Düşük beta (yapışkan/sticky) -> ağırlık uzun vadeye kayar (5 yıl bucket'ı büyür)
    Yüksek beta (faize duyarlı)  -> ağırlık kısa vadeye kayar (1-3 ay bucket'ı büyür)

    Bu basit bir sezgisel (heuristic) kuraldır; gerçek bankalarda bu ağırlıklar
    geçmiş veri optimizasyonu (örn. NII volatilitesini minimize eden ağırlıklar)
    ile kalibre edilir.
    """
    # beta 0 (çok yapışkan) -> uzun vadeye yüklü dağılım
    # beta 1 (çok duyarlı)  -> kısa vadeye yüklü dağılım
    beta = max(0.0, min(1.0, beta))

    short_weight_base = 0.10 + 0.5 * beta   # 1 ay-6 ay toplamı
    long_weight_base = 1.0 - short_weight_base

    # 7 bucket'a dağıt: ilk 3'ü kısa, son 4'ü orta-uzun
    short_buckets = [0.5, 0.3, 0.2]  # 1ay, 3ay, 6ay arasında dağılım oranı
    long_buckets = [0.30, 0.25, 0.20, 0.25]  # 1y, 2y, 3y, 5y arasında dağılım oranı

    weights = [w * short_weight_base for w in short_buckets] + [
        w * long_weight_base for w in long_buckets
    ]
    return weights


def build_replicating_portfolio(core_level: float, volatile_level: float, beta: float) -> pd.DataFrame:
    """
    Core + volatile bakiyeyi vade dilimlerine dağıtarak replicating portfolio oluşturur.

    Parameters
    ----------
    core_level : float
        Core (kalıcı) mevduat tutarı.
    volatile_level : float
        Volatile (oynak) mevduat tutarı.
    beta : float
        Pass-through katsayısı (core'un vade dağılımını etkiler).

    Returns
    -------
    pd.DataFrame: columns = [tenor_label, months, year_midpoint, amount, weight_pct]
    """
    weights = _weights_for_pass_through(beta)
    rows = []
    for (label, months, year_mid), w in zip(TENOR_BUCKETS, weights):
        amount = core_level * w
        rows.append({"tenor_label": label, "months": months, "year_midpoint": year_mid, "amount": amount})

    df = pd.DataFrame(rows)

    # Volatile kısmı 1 ay dilimine ekle (overnight/kısa vadeli kabul)
    df.loc[df["tenor_label"] == "1 Ay", "amount"] += volatile_level

    total = df["amount"].sum()
    df["weight_pct"] = df["amount"] / total * 100
    return df


def build_contractual_portfolio(total_balance: float) -> pd.DataFrame:
    """
    Karşılaştırma amaçlı: sözleşmesel (naif) yaklaşım.
    Tüm bakiye overnight/1 ay olarak kabul edilir.
    """
    rows = [{"tenor_label": label, "months": months, "year_midpoint": year_mid, "amount": 0.0}
            for label, months, year_mid in TENOR_BUCKETS]
    df = pd.DataFrame(rows)
    df.loc[df["tenor_label"] == "1 Ay", "amount"] = total_balance
    df["weight_pct"] = df["amount"] / total_balance * 100
    return df


def weighted_average_maturity(portfolio_df: pd.DataFrame) -> float:
    """Replicating portfolio için ağırlıklı ortalama vadeyi (yıl) hesaplar."""
    total = portfolio_df["amount"].sum()
    if total == 0:
        return 0.0
    return (portfolio_df["amount"] * portfolio_df["year_midpoint"]).sum() / total


if __name__ == "__main__":
    # Örnek: retail_demand core=80.3M, volatile=15.8M, beta=0.155
    rp = build_replicating_portfolio(core_level=80_326_416, volatile_level=15_772_453, beta=0.155)
    print("--- Replicating Portfolio (Retail) ---")
    print(rp[["tenor_label", "amount", "weight_pct"]].to_string(index=False))
    print(f"\nAğırlıklı Ortalama Vade: {weighted_average_maturity(rp):.2f} yıl")

    cp = build_contractual_portfolio(total_balance=96_098_869)
    print("\n--- Sözleşmesel (Naif) Portfolio (Retail) ---")
    print(cp[["tenor_label", "amount", "weight_pct"]].to_string(index=False))
    print(f"\nAğırlıklı Ortalama Vade: {weighted_average_maturity(cp):.2f} yıl")
