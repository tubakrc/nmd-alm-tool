"""
Core / Volatile mevduat ayrımı.

Yöntem: Rolling minimum (hareketli minimum) yaklaşımı.
Belirli bir pencere (örn. 12 ay) içindeki en düşük bakiye seviyesi,
mevduatın "her koşulda bankada kalan" kısmı olarak kabul edilir (core).
Bunun üzerindeki kısım volatile (oynak, kısa vadeli kabul edilir) olarak ayrılır.

Bu, EBA/Basel IRRBB rehberlerinde de referans verilen basit ve yaygın bir
yöntemdir (daha gelişmiş alternatifler: güven aralığı bazlı VaR yöntemi,
Markov zinciri tabanlı modeller).
"""

import pandas as pd


def split_core_volatile(df: pd.DataFrame, window: int = 12) -> dict:
    """
    Tek bir segmentin bakiye serisi için core/volatile ayrımı yapar.

    Parameters
    ----------
    df : pd.DataFrame
        'date' ve 'balance' kolonlarını içeren, tek segmente ait zaman serisi.
    window : int
        Rolling minimum penceresi (ay). Varsayılan 12 ay.

    Returns
    -------
    dict with:
        - core_level: float, core (kalıcı) mevduat seviyesi
        - volatile_level: float, en son bakiyedeki volatile kısım
        - core_ratio: float, core / ortalama bakiye (%)
        - rolling_min_series: pd.Series, görselleştirme için
        - latest_balance: float
    """
    balance = df["balance"]
    rolling_min = balance.rolling(window=window, min_periods=1).min()

    # Core seviye: serinin tarihi en düşük (rolling) noktası -> "hiç düşmediği taban".
    # Volatile seviye: ORTALAMA bakiyenin bu tabanın üzerinde kalan kısmı.
    # (Son ay yerine ortalama kullanmak, tek bir düşük ayın hikayeyi
    # bozmasını engeller ve "tipik durumda ne kadarı oynak" sorusuna cevap verir.)
    core_level = rolling_min.min()
    latest_balance = balance.iloc[-1]
    avg_balance = balance.mean()
    volatile_level = max(avg_balance - core_level, 0)
    core_ratio = core_level / avg_balance if avg_balance > 0 else 0

    return {
        "core_level": core_level,
        "volatile_level": volatile_level,
        "core_ratio": core_ratio,
        "rolling_min_series": rolling_min,
        "latest_balance": latest_balance,
        "avg_balance": avg_balance,
    }


def split_all_segments(df: pd.DataFrame, window: int = 12) -> dict:
    """
    Veri setindeki tüm segmentler için core/volatile ayrımını çalıştırır.

    Returns
    -------
    dict: {segment_name: split_core_volatile sonucu}
    """
    results = {}
    for segment in df["segment"].unique():
        seg_df = df[df["segment"] == segment].sort_values("date").reset_index(drop=True)
        results[segment] = split_core_volatile(seg_df, window=window)
    return results


if __name__ == "__main__":
    df = pd.read_csv("/home/claude/nmd-alm-tool/data/synthetic_nmd_data.csv", parse_dates=["date"])
    results = split_all_segments(df)
    for segment, res in results.items():
        print(f"\n--- {segment} ---")
        print(f"Ortalama bakiye   : {res['avg_balance']:,.0f}")
        print(f"Son bakiye        : {res['latest_balance']:,.0f}")
        print(f"Core seviye       : {res['core_level']:,.0f}")
        print(f"Volatile seviye   : {res['volatile_level']:,.0f}")
        print(f"Core oranı        : %{res['core_ratio']*100:.1f}")
