"""
NMD Behavioral Modeling Dashboard
-----------------------------------
Vadesiz mevduatların (NMD) davranışsal modellemesini, core/volatile ayrımını,
pass-through tahminini, replicating portfolio'yu ve EVE duyarlılık karşılaştırmasını
tek sayfada gösteren Streamlit uygulaması.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_generator import generate_nmd_dataset
from core_volatile import split_core_volatile
from pass_through import estimate_pass_through
from replicating_portfolio import (
    build_replicating_portfolio,
    build_contractual_portfolio,
    weighted_average_maturity,
)
from eve_calculator import compare_contractual_vs_behavioral


# ----------------------------- Sayfa Ayarları -----------------------------
st.set_page_config(
    page_title="NMD Davranışsal Modelleme",
    layout="wide",
    initial_sidebar_state="expanded",
)

PRIMARY = "#1B3A5C"      # koyu lacivert
ACCENT = "#C77B3B"       # turuncu/bronz vurgu
NEUTRAL = "#6B7280"      # gri
BG_LIGHT = "#F7F8FA"

st.markdown(
    f"""
    <style>
    .main {{ background-color: {BG_LIGHT}; }}
    h1, h2, h3 {{ color: {PRIMARY}; }}
    .stMetric {{ background-color: white; padding: 12px; border-radius: 6px; border: 1px solid #E5E7EB; }}
    .note-box {{
        background-color: white;
        border-left: 3px solid {ACCENT};
        padding: 10px 16px;
        border-radius: 4px;
        font-size: 0.92rem;
        color: #374151;
        margin-bottom: 1rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

PLOTLY_TEMPLATE = "plotly_white"
SEGMENT_COLORS = {"retail_demand": PRIMARY, "commercial_demand": ACCENT}
SEGMENT_LABELS = {"retail_demand": "Perakende Vadesiz", "commercial_demand": "Ticari Vadesiz"}


def note(text: str):
    st.markdown(f'<div class="note-box">{text}</div>', unsafe_allow_html=True)


# ----------------------------- Başlık -----------------------------
st.title("NMD Davranışsal Modelleme Aracı")
st.caption("Vadesiz mevduatların (Non-Maturity Deposits) faiz oranı riski yönetiminde davranışsal modellenmesi — ALM / IRRBB showcase")

note(
    "Vadesiz mevduatların sözleşmesel vadesi yoktur (anında çekilebilir), ancak müşteriler "
    "pratikte bu paranın büyük kısmını uzun süre bankada tutar. Bu araç, gerçek bakiye verisinden "
    "<b>core/volatile ayrımı</b>, <b>pass-through (faiz duyarlılığı)</b> ve <b>davranışsal vade dağılımı</b> "
    "çıkararak, bu fonlama kaynağının faiz riskine etkisini sözleşmesel (naif) yaklaşımla karşılaştırır."
)

# ----------------------------- Sidebar: Veri Kaynağı -----------------------------
st.sidebar.header("Veri Kaynağı")
data_source = st.sidebar.radio(
    "Veri nereden gelsin?",
    ["Sentetik veri (varsayılan)", "Kendi CSV dosyamı yükle"],
)

if data_source == "Kendi CSV dosyamı yükle":
    st.sidebar.caption("Beklenen kolonlar: date, segment, balance, deposit_rate, policy_rate")
    uploaded = st.sidebar.file_uploader("CSV yükle", type=["csv"])
    if uploaded is not None:
        df = pd.read_csv(uploaded, parse_dates=["date"])
        required_cols = {"date", "segment", "balance", "deposit_rate", "policy_rate"}
        if not required_cols.issubset(df.columns):
            st.sidebar.error(f"CSV şu kolonları içermeli: {required_cols}")
            st.stop()
    else:
        st.info("Soldan bir CSV dosyası yükleyin, ya da sentetik veriye geçin.")
        st.stop()
else:
    n_months = st.sidebar.slider("Veri uzunluğu (ay)", min_value=24, max_value=120, value=60, step=6)
    df = generate_nmd_dataset(n_months=n_months)

st.sidebar.divider()
window = st.sidebar.slider(
    "Core/Volatile rolling pencere (ay)", min_value=6, max_value=24, value=12, step=1
)
shock_bps = st.sidebar.select_slider(
    "EVE Faiz Şoku (baz puan)", options=[100, 200, 300], value=200
)

segments = sorted(df["segment"].unique())

# ----------------------------- 1. Bakiye Zaman Serisi -----------------------------
st.header("1. Mevduat Bakiyesi Zaman Serisi")
note(
    "Ham veri: her segment için aylık bakiye, mevduat faizi ve politika faizi. "
    "Perakende mevduatın daha stabil, ticari mevduatın daha oynak olması beklenir — "
    "bu, sonraki adımlardaki core/volatile ayrımının temelini oluşturur."
)

fig_balance = go.Figure()
for seg in segments:
    seg_df = df[df["segment"] == seg].sort_values("date")
    fig_balance.add_trace(
        go.Scatter(
            x=seg_df["date"], y=seg_df["balance"],
            name=SEGMENT_LABELS.get(seg, seg),
            line=dict(color=SEGMENT_COLORS.get(seg, NEUTRAL), width=2),
        )
    )
fig_balance.update_layout(
    template=PLOTLY_TEMPLATE, height=350,
    margin=dict(l=10, r=10, t=10, b=10),
    yaxis_title="Bakiye", xaxis_title=None,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)
st.plotly_chart(fig_balance, use_container_width=True)

# ----------------------------- 2. Core / Volatile Ayrımı -----------------------------
st.header("2. Core / Volatile Ayrımı")
note(
    "Yöntem: <b>rolling minimum</b>. Belirli bir pencerede (varsayılan 12 ay) bakiyenin "
    "hiç düşmediği taban seviye <b>core</b> (kalıcı) kabul edilir; ortalama bakiyenin "
    "bu tabanın üzerinde kalan kısmı <b>volatile</b> (oynak, kısa vadeli) olarak ayrılır."
)

cv_results = {}
cols = st.columns(len(segments))
for i, seg in enumerate(segments):
    seg_df = df[df["segment"] == seg].sort_values("date").reset_index(drop=True)
    res = split_core_volatile(seg_df, window=window)
    cv_results[seg] = res
    with cols[i]:
        st.subheader(SEGMENT_LABELS.get(seg, seg))
        st.metric("Core Oranı", f"%{res['core_ratio']*100:.1f}")
        m1, m2 = st.columns(2)
        m1.metric("Core Seviye", f"{res['core_level']/1e6:.1f}M")
        m2.metric("Volatile Seviye", f"{res['volatile_level']/1e6:.1f}M")

fig_cv = go.Figure()
for seg in segments:
    seg_df = df[df["segment"] == seg].sort_values("date").reset_index(drop=True)
    res = cv_results[seg]
    fig_cv.add_trace(
        go.Scatter(
            x=seg_df["date"], y=seg_df["balance"], name=f"{SEGMENT_LABELS.get(seg, seg)} - Bakiye",
            line=dict(color=SEGMENT_COLORS.get(seg, NEUTRAL), width=1.5),
        )
    )
    fig_cv.add_trace(
        go.Scatter(
            x=seg_df["date"], y=res["rolling_min_series"],
            name=f"{SEGMENT_LABELS.get(seg, seg)} - Rolling Min",
            line=dict(color=SEGMENT_COLORS.get(seg, NEUTRAL), width=2, dash="dot"),
        )
    )
fig_cv.update_layout(
    template=PLOTLY_TEMPLATE, height=350,
    margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)
st.plotly_chart(fig_cv, use_container_width=True)

# ----------------------------- 3. Pass-Through Regresyonu -----------------------------
st.header("3. Pass-Through (Faiz Duyarlılığı) Tahmini")
note(
    "Regresyon: <code>Δdeposit_rate = α + β·Δpolicy_rate</code>. "
    "β ≈ 0 → mevduat faizi piyasadan bağımsız, <b>yapışkan/ucuz</b> fonlama. "
    "β ≈ 1 → mevduat faizi piyasayı tam yansıtıyor, <b>faize duyarlı</b> fonlama."
)

pt_results = {}
cols2 = st.columns(len(segments))
for i, seg in enumerate(segments):
    seg_df = df[df["segment"] == seg]
    res = estimate_pass_through(seg_df)
    pt_results[seg] = res
    with cols2[i]:
        st.subheader(SEGMENT_LABELS.get(seg, seg))
        st.metric("Pass-Through (β)", f"{res['beta']:.3f}")
        st.metric("R²", f"{res['r_squared']:.3f}")
        yorum = "Yapışkan / ucuz fonlama" if res["beta"] < 0.4 else "Faize duyarlı fonlama"
        st.caption(f"Yorum: **{yorum}**")

fig_pt = go.Figure()
for seg in segments:
    res = pt_results[seg]
    fig_pt.add_trace(
        go.Scatter(
            x=res["policy_rate_change"], y=res["actual"], mode="markers",
            name=f"{SEGMENT_LABELS.get(seg, seg)} - Gerçek",
            marker=dict(color=SEGMENT_COLORS.get(seg, NEUTRAL), size=6, opacity=0.6),
        )
    )
    sorted_idx = res["policy_rate_change"].argsort()
    fig_pt.add_trace(
        go.Scatter(
            x=res["policy_rate_change"].iloc[sorted_idx], y=res["fitted"].iloc[sorted_idx],
            mode="lines", name=f"{SEGMENT_LABELS.get(seg, seg)} - Trend",
            line=dict(color=SEGMENT_COLORS.get(seg, NEUTRAL), width=2),
        )
    )
fig_pt.update_layout(
    template=PLOTLY_TEMPLATE, height=350,
    margin=dict(l=10, r=10, t=10, b=10),
    xaxis_title="Δ Politika Faizi (puan)", yaxis_title="Δ Mevduat Faizi (puan)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)
st.plotly_chart(fig_pt, use_container_width=True)

# ----------------------------- 4. Replicating Portfolio -----------------------------
st.header("4. Davranışsal Vade Dağılımı (Replicating Portfolio)")
note(
    "Core kısım, pass-through katsayısına göre vade dilimlerine dağıtılır (yapışkan core "
    "uzun vadeye, duyarlı core kısa vadeye kayar). Volatile kısım tamamen 1 ay dilimine "
    "yazılır. Sözleşmesel yaklaşım ise tüm bakiyeyi tek bir overnight/1 ay dilimine koyar — "
    "aradaki fark, bu mevduatın gerçek faiz riski profilini gösterir."
)

selected_seg = st.selectbox(
    "Vade dağılımını görmek istediğiniz segment", segments,
    format_func=lambda s: SEGMENT_LABELS.get(s, s),
)

cv = cv_results[selected_seg]
pt = pt_results[selected_seg]
behavioral_portfolio = build_replicating_portfolio(cv["core_level"], cv["volatile_level"], pt["beta"])
contractual_portfolio = build_contractual_portfolio(cv["avg_balance"])

col_left, col_right = st.columns(2)
with col_left:
    st.markdown("**Sözleşmesel (Naif) Dağılım**")
    fig_c = go.Figure(
        go.Bar(
            x=contractual_portfolio["tenor_label"], y=contractual_portfolio["amount"],
            marker_color=NEUTRAL,
        )
    )
    fig_c.update_layout(
        template=PLOTLY_TEMPLATE, height=300,
        margin=dict(l=10, r=10, t=10, b=10), yaxis_title="Tutar",
    )
    st.plotly_chart(fig_c, use_container_width=True)
    st.caption(f"Ağırlıklı Ortalama Vade: **{weighted_average_maturity(contractual_portfolio):.2f} yıl**")

with col_right:
    st.markdown("**Davranışsal Dağılım**")
    fig_b = go.Figure(
        go.Bar(
            x=behavioral_portfolio["tenor_label"], y=behavioral_portfolio["amount"],
            marker_color=SEGMENT_COLORS.get(selected_seg, ACCENT),
        )
    )
    fig_b.update_layout(
        template=PLOTLY_TEMPLATE, height=300,
        margin=dict(l=10, r=10, t=10, b=10), yaxis_title="Tutar",
    )
    st.plotly_chart(fig_b, use_container_width=True)
    st.caption(f"Ağırlıklı Ortalama Vade: **{weighted_average_maturity(behavioral_portfolio):.2f} yıl**")

# ----------------------------- 5. EVE Karşılaştırması -----------------------------
st.header("5. EVE Duyarlılık Karşılaştırması")
note(
    f"Basitleştirilmiş duration yaklaşımı ile, {shock_bps}bp paralel faiz şoku altında "
    "iki yaklaşımın (sözleşmesel vs davranışsal) ekonomik değer (EVE) duyarlılığı karşılaştırılır. "
    "<b>Bu hesaplama öğretici/gösterim amaçlıdır</b>, tam bir Basel IRRBB SOT hesaplaması değildir."
)

comparison = compare_contractual_vs_behavioral(
    core_level=cv["core_level"],
    volatile_level=cv["volatile_level"],
    beta=pt["beta"],
    total_balance=cv["avg_balance"],
    shock_bps=shock_bps,
)

display_comparison = comparison.copy()
display_comparison["Ağırlıklı Ort. Vade (yıl)"] = display_comparison["Ağırlıklı Ort. Vade (yıl)"].round(2)
display_comparison["Duration Proxy"] = display_comparison["Duration Proxy"].round(2)
shock_col = f"{shock_bps}bp Şokta ΔEVE"
pct_col = f"{shock_bps}bp Şokta ΔEVE (%)"
display_comparison[shock_col] = display_comparison[shock_col].apply(lambda x: f"{x:,.0f}")
display_comparison[pct_col] = display_comparison[pct_col].apply(lambda x: f"%{x:.2f}")

st.dataframe(display_comparison, use_container_width=True, hide_index=True)

naive_pct = comparison.iloc[0][pct_col]
behavioral_pct = comparison.iloc[1][pct_col]
ratio = abs(behavioral_pct / naive_pct) if naive_pct != 0 else float("inf")

st.markdown(
    f"""
    <div class="note-box" style="border-left-color: {PRIMARY};">
    <b>Sonuç:</b> Sözleşmesel yaklaşıma göre bu mevduatta {shock_bps}bp şokta risk yalnızca
    <b>%{abs(naive_pct):.2f}</b> görünürken, davranışsal modelde gerçek risk
    <b>%{abs(behavioral_pct):.2f}</b> — yani sözleşmesel yaklaşım gerçek riski
    <b>~{ratio:.0f} kat</b> küçük göstermektedir.
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()
st.caption(
    "Bu araç, ALM/IRRBB context'inde NMD davranışsal modellemesinin metodolojik bir gösterimidir. "
    "Sentetik veri ve basitleştirilmiş duration yaklaşımı kullanılmaktadır."
)
