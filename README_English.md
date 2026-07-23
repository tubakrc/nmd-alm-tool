# NMD Behavioral Modeling Tool

> An end-to-end ALM / IRRBB showcase for modeling Non-Maturity Deposits (NMDs) — from raw balance data to EVE sensitivity comparison.

---

## What problem does this solve?

Non-Maturity Deposits have no contractual maturity — a customer can withdraw at any time. In practice, however, a significant portion of these balances (the **core**) stays in the bank for years. If a bank models NMDs at their contractual maturity (i.e., treats everything as overnight), it severely misrepresents its gap, EVE, and NII risk profiles.

This tool extracts behavioral characteristics from deposit data and shows — in concrete numbers — how much the contractual (naïve) approach understates interest rate risk compared to a behavioral model.

---

## Features

| Step | Method |
|------|--------|
| **Core / Volatile split** | Rolling minimum over a configurable window (e.g. 12 months) |
| **Pass-through estimation** | OLS first-difference regression: `Δdeposit_rate = α + β·Δpolicy_rate` |
| **Replicating portfolio** | Laddered maturity bucketing weighted by pass-through coefficient |
| **EVE sensitivity comparison** | Simplified duration proxy under Basel standard parallel shock (±100/200/300bp) |

Two deposit segments are modeled side by side:
- **Retail demand deposits** — low pass-through, high core ratio, longer behavioral maturity
- **Commercial demand deposits** — higher pass-through, more volatile, shorter behavioral maturity

---

## Demo

```
Contractual approach  →  Weighted Average Maturity: 0.04 yrs  →  EVE impact at 200bp: -0.08%
Behavioral model      →  Weighted Average Maturity: 1.47 yrs  →  EVE impact at 200bp: -2.94%
```

The contractual approach underestimates risk by ~35x in this example.

---

## Project Structure

```
nmd-alm-tool/
├── data/
│   └── synthetic_nmd_data.csv      # pre-generated synthetic dataset
├── src/
│   ├── data_generator.py           # synthetic NMD data generator (2 segments)
│   ├── core_volatile.py            # core/volatile split (rolling minimum)
│   ├── pass_through.py             # OLS pass-through regression
│   ├── replicating_portfolio.py    # behavioral maturity bucketing
│   ├── eve_calculator.py           # EVE sensitivity & comparison table
│   └── app.py                      # Streamlit dashboard
├── requirements.txt
└── README.md
```

---

## Installation

```bash
pip install -r requirements.txt
```

> **Anaconda users on Windows:** if you encounter a `pyarrow` DLL error on startup, run:
> ```bash
> conda install -c conda-forge pyarrow --force-reinstall
> ```

---

## Usage

```bash
cd src
streamlit run app.py
```

The dashboard sidebar lets you:
- Switch between **synthetic data** (default) and **your own CSV upload**
- Adjust the rolling window for core/volatile split (6–24 months)
- Choose the interest rate shock size (100 / 200 / 300 bp)

### Bringing your own data

Upload a CSV with the following columns:

| Column | Description |
|--------|-------------|
| `date` | Monthly date |
| `segment` | Deposit segment name |
| `balance` | Deposit balance |
| `deposit_rate` | Deposit interest rate (%) |
| `policy_rate` | Central bank / market rate (%) |

---

## Methodology Notes

**Core / Volatile split**
Rolling minimum approach — the lowest balance observed in a given window is treated as the core (permanently stable) portion. The excess above core in the average balance is classified as volatile. This is one of the methods referenced in EBA/Basel IRRBB guidelines. More advanced alternatives include VaR-based confidence interval methods and Markov chain models.

**Pass-through regression**
Simple OLS on first differences. A more sophisticated approach would use an Error Correction Model (ECM) to separately estimate short-run and long-run pass-through, and to capture the speed of adjustment.

**Replicating portfolio**
Core balances are distributed across maturity buckets using a laddered (equally-spaced rollover) logic, with bucket weights shifting toward longer maturities as the pass-through coefficient decreases. In production, these weights are typically calibrated by minimizing historical NII volatility.

**EVE sensitivity**
The EVE impact is computed using a simplified duration proxy (modified duration ≈ weighted average maturity). This is for illustrative purposes only — a full Basel IRRBB Standardised Outlier Test (SOT) requires proper cash flow discounting, tenor-specific shock curves, and regulatory caps on NMD behavioral maturity (e.g. average maturity ≤ 5 years for retail NMDs under EBA guidelines).

---

## Regulatory Context

This project is grounded in the IRRBB (Interest Rate Risk in the Banking Book) framework:
- **BCBS 368** — Basel Committee's standards for IRRBB (2016)
- **EBA/GL/2018/02** — EBA Guidelines on the management of interest rate risk arising from non-trading book activities
- **CRD IV / CRR II** — EU implementation

NMD behavioral modeling is one of the most judgment-intensive assumptions in IRRBB. Supervisors pay close attention to it precisely because small changes in assumed maturity can produce large swings in reported EVE sensitivity.

---

## License

MIT
