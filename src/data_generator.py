"""
Sentetik NMD (Non-Maturity Deposit) verisi üretici.

İki segment üretir:
- retail_demand: perakende vadesiz mevduat (stabil, düşük pass-through)
- commercial_demand: ticari vadesiz mevduat (volatil, yüksek pass-through)

Çıktı kolonları: date, segment, balance, deposit_rate, policy_rate
"""

import numpy as np
import pandas as pd


def generate_policy_rate_path(n_months: int, seed: int = 42) -> np.ndarray:
    """Politika faizi yolu üretir: kademeli artış + birkaç sabit dönem."""
    rng = np.random.default_rng(seed)
    rate = 8.0
    path = []
    for i in range(n_months):
        if i % 4 == 0:
            rate += rng.choice([0, 0.5, 1.0, -0.5], p=[0.4, 0.3, 0.2, 0.1])
        rate = max(rate, 2.0)
        path.append(rate)
    return np.array(path)


def generate_segment(
    n_months: int,
    policy_rate: np.ndarray,
    base_balance: float,
    pass_through: float,
    volatility: float,
    seasonality_amp: float,
    seed: int,
) -> pd.DataFrame:
    """
    Tek bir mevduat segmenti için zaman serisi üretir.

    pass_through: mevduat faizinin politika faizine tepki katsayısı (0-1)
    volatility: bakiyedeki rastgele dalgalanma şiddeti (core/volatile ayrımını
                anlamlı kılmak için segment bazlı farklılaştırılır)
    seasonality_amp: yıllık mevsimsellik genliği (örn. yıl sonu bakiye artışı)
    """
    rng = np.random.default_rng(seed)

    # Mevduat faizi: politika faizi DEĞİŞİMİNİN sönümlü/gecikmeli takibi.
    # pass_through parametresi burada doğrudan beta'ya karşılık gelir:
    # politika faizi 1 puan değiştiğinde mevduat faizi pass_through puan değişir,
    # ek olarak küçük bir gürültü ve gecikme etkisi eklenir (gerçekçilik için).
    deposit_rate = np.zeros(n_months)
    deposit_rate[0] = max(policy_rate[0] * pass_through * 0.05, 0.2)
    for t in range(1, n_months):
        policy_change = policy_rate[t] - policy_rate[t - 1]
        rate_noise = rng.normal(0, 0.02)
        deposit_rate[t] = deposit_rate[t - 1] + pass_through * policy_change + rate_noise
        deposit_rate[t] = max(deposit_rate[t], 0.1)

    # Bakiye: trend + mevsimsellik + faiz farkına tepki + gürültü
    balance = np.zeros(n_months)
    balance[0] = base_balance
    trend_growth = 0.003  # aylık hafif organik büyüme
    initial_gap = policy_rate[0] - deposit_rate[0]
    for t in range(1, n_months):
        month_of_year = t % 12
        season = seasonality_amp * np.sin(2 * np.pi * month_of_year / 12)
        # fırsat maliyeti BAŞLANGIÇ seviyesine göre ne kadar değişti -> bakiye o yönde tepki verir
        rate_gap = policy_rate[t] - deposit_rate[t]
        gap_change = rate_gap - initial_gap
        rate_effect = -0.0015 * gap_change
        noise = rng.normal(0, volatility)
        growth = trend_growth + rate_effect + noise
        balance[t] = balance[t - 1] * (1 + growth) + season * base_balance * 0.01
        balance[t] = max(balance[t], base_balance * 0.3)  # taban koruması (gerçekçilik)

    return pd.DataFrame(
        {
            "balance": balance,
            "deposit_rate": deposit_rate,
            "policy_rate": policy_rate,
        }
    )


def generate_nmd_dataset(n_months: int = 60, seed: int = 42) -> pd.DataFrame:
    """
    İki segmentli (perakende + ticari) tam NMD veri setini üretir.

    Returns
    -------
    pd.DataFrame with columns: date, segment, balance, deposit_rate, policy_rate
    """
    end_date = pd.Timestamp.today().normalize().replace(day=1)
    dates = pd.date_range(end=end_date, periods=n_months, freq="MS")
    assert len(dates) == n_months, f"date length mismatch: {len(dates)} != {n_months}"
    policy_rate = generate_policy_rate_path(n_months, seed=seed)

    retail = generate_segment(
        n_months,
        policy_rate,
        base_balance=100_000_000,
        pass_through=0.15,   # düşük pass-through -> yapışkan, ucuz fonlama
        volatility=0.015,    # düşük volatilite -> stabil
        seasonality_amp=0.5,
        seed=seed,
    )
    retail["segment"] = "retail_demand"

    commercial = generate_segment(
        n_months,
        policy_rate,
        base_balance=60_000_000,
        pass_through=0.55,   # yüksek pass-through -> faize duyarlı
        volatility=0.045,    # yüksek volatilite -> daha az stabil
        seasonality_amp=1.5,
        seed=seed + 1,
    )
    commercial["segment"] = "commercial_demand"

    retail["date"] = dates
    commercial["date"] = dates

    df = pd.concat([retail, commercial], ignore_index=True)
    df = df[["date", "segment", "balance", "deposit_rate", "policy_rate"]]
    df["balance"] = df["balance"].round(0)
    df["deposit_rate"] = df["deposit_rate"].round(3)
    df["policy_rate"] = df["policy_rate"].round(3)
    return df


if __name__ == "__main__":
    df = generate_nmd_dataset()
    df.to_csv("/home/claude/nmd-alm-tool/data/synthetic_nmd_data.csv", index=False)
    print(df.head(15))
    print(f"\nToplam satır: {len(df)}")
    print(f"Segmentler: {df['segment'].unique()}")
