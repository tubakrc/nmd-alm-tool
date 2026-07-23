"""
Pass-through rate tahmini.

Mevduat faizinin politika/piyasa faizindeki değişime ne kadar tepki
verdiğini basit doğrusal regresyon ile tahmin eder:

    Δdeposit_rate_t = α + β · Δpolicy_rate_t + ε_t

β (pass-through katsayısı) yorumu:
- β ≈ 0   -> mevduat faizi piyasadan tamamen bağımsız, çok "yapışkan" (sticky)
- β ≈ 1   -> mevduat faizi piyasayı tam yansıtıyor, hiç yapışkan değil

Düşük β, bankaya ucuz ve davranışsal olarak uzun vadeli sayılabilecek
bir fonlama kaynağı sağladığı için ALM açısından önemlidir.
"""

import pandas as pd
import statsmodels.api as sm


def estimate_pass_through(df: pd.DataFrame) -> dict:
    """
    Tek bir segment için pass-through regresyonu çalıştırır.

    Parameters
    ----------
    df : pd.DataFrame
        'date', 'deposit_rate', 'policy_rate' kolonlarını içeren zaman serisi.

    Returns
    -------
    dict with:
        - beta: float, pass-through katsayısı
        - alpha: float, sabit terim
        - r_squared: float
        - p_value: float, beta'nın anlamlılığı
        - fitted: pd.Series, tahmin edilen Δdeposit_rate (görselleştirme için)
        - actual: pd.Series, gerçek Δdeposit_rate
        - policy_rate_change: pd.Series, gerçek Δpolicy_rate
    """
    data = df.sort_values("date").copy()
    data["d_deposit"] = data["deposit_rate"].diff()
    data["d_policy"] = data["policy_rate"].diff()
    data = data.dropna(subset=["d_deposit", "d_policy"])

    X = sm.add_constant(data["d_policy"])
    y = data["d_deposit"]
    model = sm.OLS(y, X).fit()

    beta = model.params["d_policy"]
    alpha = model.params["const"]
    r_squared = model.rsquared
    p_value = model.pvalues["d_policy"]
    fitted = model.fittedvalues

    return {
        "beta": beta,
        "alpha": alpha,
        "r_squared": r_squared,
        "p_value": p_value,
        "fitted": fitted,
        "actual": y,
        "policy_rate_change": data["d_policy"],
        "dates": data["date"],
    }


def estimate_all_segments(df: pd.DataFrame) -> dict:
    """Tüm segmentler için pass-through tahminini çalıştırır."""
    results = {}
    for segment in df["segment"].unique():
        seg_df = df[df["segment"] == segment]
        results[segment] = estimate_pass_through(seg_df)
    return results


if __name__ == "__main__":
    df = pd.read_csv("/home/claude/nmd-alm-tool/data/synthetic_nmd_data.csv", parse_dates=["date"])
    results = estimate_all_segments(df)
    for segment, res in results.items():
        print(f"\n--- {segment} ---")
        print(f"Pass-through (beta) : {res['beta']:.3f}")
        print(f"R-squared            : {res['r_squared']:.3f}")
        print(f"p-value (beta)       : {res['p_value']:.4f}")
        yorum = "yapışkan/ucuz fonlama" if res["beta"] < 0.4 else "faize duyarlı fonlama"
        print(f"Yorum                : {yorum}")
