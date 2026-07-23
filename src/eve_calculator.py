"""
EVE (Economic Value of Equity) duration ve faiz şoku etkisi hesaplama.

Basitleştirilmiş yaklaşım:
- Her vade dilimini sıfır kuponlu bir nakit akışı gibi ele alıyoruz.
- Modified duration ~ vade (yıl) olarak yaklaşıklanıyor (basit gösterim amaçlı;
  gerçek uygulamada iskonto faktörleri ve nakit akışı zamanlaması kullanılır).
- ΔEVE ≈ -Duration × ΔYield × Bakiye  (yükümlülük tarafı için, faiz artışı
  yükümlülüğün bugünkü değerini düşürür -> bu sermaye/EVE için bir KAYIP değil,
  mevduat bir yükümlülük olduğundan faiz artışında yükümlülüğün PV'si düşer,
  bu da EVE'yi (Varlık-Yükümlülük) ARTIRIR. Ancak NMD context'inde asıl risk,
  bu fonlama kaynağının yeniden fiyatlama riskidir; burada gösterim amacıyla
  basitleştirilmiş "duration mismatch" etkisini hesaplıyoruz.)

Not: Bu modül öğretici/gösterim amaçlıdır, tam bir Basel IRRBB SOT
(standardised outlier test) hesaplaması değildir.
"""

import pandas as pd

from replicating_portfolio import (
    build_replicating_portfolio,
    build_contractual_portfolio,
    weighted_average_maturity,
)


def compute_eve_sensitivity(portfolio_df: pd.DataFrame, shock_bps: int = 200) -> dict:
    """
    Verilen replicating/contractual portfolio için basitleştirilmiş EVE duyarlılığı hesaplar.

    Parameters
    ----------
    portfolio_df : pd.DataFrame
        'amount' ve 'year_midpoint' kolonlarını içeren vade dağılımı.
    shock_bps : int
        Faiz şoku (baz puan). Varsayılan 200bp (Basel standart paralel şok).

    Returns
    -------
    dict with: total_balance, wam (weighted average maturity), duration_proxy,
               delta_eve, delta_eve_pct
    """
    total_balance = portfolio_df["amount"].sum()
    wam = weighted_average_maturity(portfolio_df)

    # Basit modified duration yaklaşımı: WAM'in kendisi (sıfır kupon yaklaşıklaması)
    duration_proxy = wam

    shock_decimal = shock_bps / 10000
    delta_eve = -duration_proxy * shock_decimal * total_balance
    delta_eve_pct = (delta_eve / total_balance * 100) if total_balance > 0 else 0

    return {
        "total_balance": total_balance,
        "wam": wam,
        "duration_proxy": duration_proxy,
        "shock_bps": shock_bps,
        "delta_eve": delta_eve,
        "delta_eve_pct": delta_eve_pct,
    }


def compare_contractual_vs_behavioral(
    core_level: float, volatile_level: float, beta: float, total_balance: float, shock_bps: int = 200
) -> pd.DataFrame:
    """
    Sözleşmesel (naif) vs davranışsal (replicating portfolio) yaklaşımı
    EVE duyarlılığı açısından karşılaştırır.

    Returns
    -------
    pd.DataFrame: iki satır (Sözleşmesel, Davranışsal), kolonlar karşılaştırma metrikleri.
    """
    contractual = build_contractual_portfolio(total_balance)
    behavioral = build_replicating_portfolio(core_level, volatile_level, beta)

    c_metrics = compute_eve_sensitivity(contractual, shock_bps)
    b_metrics = compute_eve_sensitivity(behavioral, shock_bps)

    comparison = pd.DataFrame(
        [
            {
                "Yaklaşım": "Sözleşmesel (Naif)",
                "Ağırlıklı Ort. Vade (yıl)": c_metrics["wam"],
                "Duration Proxy": c_metrics["duration_proxy"],
                f"{shock_bps}bp Şokta ΔEVE": c_metrics["delta_eve"],
                f"{shock_bps}bp Şokta ΔEVE (%)": c_metrics["delta_eve_pct"],
            },
            {
                "Yaklaşım": "Davranışsal Model",
                "Ağırlıklı Ort. Vade (yıl)": b_metrics["wam"],
                "Duration Proxy": b_metrics["duration_proxy"],
                f"{shock_bps}bp Şokta ΔEVE": b_metrics["delta_eve"],
                f"{shock_bps}bp Şokta ΔEVE (%)": b_metrics["delta_eve_pct"],
            },
        ]
    )
    return comparison


if __name__ == "__main__":
    comparison = compare_contractual_vs_behavioral(
        core_level=80_326_416,
        volatile_level=15_772_453,
        beta=0.155,
        total_balance=96_098_869,
        shock_bps=200,
    )
    print(comparison.to_string(index=False))
