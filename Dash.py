import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import main as M
import breadth as B

st.set_page_config(page_title="Breadth · Correlation · Concentration", layout="wide", initial_sidebar_state="expanded")

# theme
base = dict(template="plotly_dark", margin=dict(l=35, r=20, t=32, b=25),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=10), hovermode="x unified")


# colors
accent, warm, green, red, grey = "#4C8BF5", "#E8833A", "#3FB950", "#E5534B", "#8B949E"

### Sidebar ###
st.sidebar.title("Controls")
start = st.sidebar.date_input("Start date", pd.Timestamp("2015-01-01")).isoformat()
ma_len = st.sidebar.slider("Breadth MA (days)", 50, 200, 200, 50)
corr_window = st.sidebar.slider("Correlation window (days)", 21, 126, 63, 21)
vol_window = st.sidebar.slider("Forward vol window (days)", 10, 42, 21, 1)
sectors = [s for s in M.sector_etfs]

### Data ###
# live equities have short ttl so index levels refresh often
@st.cache_data(ttl="15m", show_spinner="Pulling prices from Yahoo…")
def get_prices(tickers, start):
    return M.load_prices(tickers, start=start)

# today's SPY/QQQ with short ttl to show live
@st.cache_data(ttl="2m", show_spinner=False)
def get_intraday(tickers, period, interval):
    return M.daily_prices(tickers, period=period, interval=interval)

# 503-name breadth pull has long ttl because it doesn't need live updates
@st.cache_data(ttl="12h", show_spinner="Pulling S&P 500 members…")
def get_breadth(start, ma):
    tickers = B.sp500_tickers()
    px = B.load_all_prices(tickers, start=start, ma=ma)
    return px, B.pct_above_ma(px, ma=ma, start=start)

# 2s/10s downloaded from FRED
@st.cache_data
def get_2s10s():
    return pd.read_csv("data_2s10s.csv", index_col=0, parse_dates=True)


# Get data
prices = get_prices(tuple(sectors + M.benchmarks), start)
uni_px, br = get_breadth(start, ma_len)
rets = M.daily_returns(prices[sectors])
corr = M.rolling_avg_pairwise_corr(rets, corr_window)
conc = M.concentration_ratio(prices)
sig = M.signal_frame(br, prices, "SPY", vol_window)
spx = 100 * prices["SPY"] / prices["SPY"].dropna().iloc[0]
yields = get_2s10s()
spread = yields["spread"]

st.title("Market Breadth, Correlation & Concentration")
st.caption("How does breadth move with cross-sector correlation and volatility?")

tabs = st.tabs(["Overview", "Breadth", "Correlation", "Signal", "Methodology"])

### Overview ###
with tabs[0]:
    br_clean, corr_clean = br.dropna(), corr.dropna()
    b_now = br_clean.iloc[-1]

    c = st.columns(4)
    c[0].metric(f"% S&P 500 > {ma_len}d MA", f"{b_now * 100:,.0f}%",
                f"{(b_now - br_clean.iloc[-253]) * 100:+.0f}pp vs 1y" if br_clean.shape[0] > 253 else None)
    c[1].metric("Avg pairwise corr", f"{corr_clean.iloc[-1]:.2f}")
    c[2].metric("RSP/SPY (rebased)", f"{conc.dropna().iloc[-1]:.1f}",
                f"{conc.dropna().iloc[-1] - conc.dropna().iloc[-253]:+.1f} vs 1y" if conc.dropna().shape[0] > 253 else None)
    c[3].metric("2s/10s spread", f"{spread.iloc[-1]:+.2f}%")

    st.write("")
    st.markdown(f"#### Today: {b_now * 100:.0f}% of the S&P is above its {ma_len}-day average")

    # breadth graph side by side with the 2s/10s
    left_1, right_1 = st.columns(2)

    with left_1:
        br_s = br.rolling(21).mean().dropna()
        lo, hi = br.min() * 100, br.max() * 100
        sp = go.Figure()
        sp.add_hrect(y0=lo, y1=hi, line_width=0, fillcolor=grey, opacity=0.08)
        sp.add_trace(go.Scatter(x=br_s.index, y=br_s * 100,
                                line=dict(color=accent, width=2), showlegend=False))
        sp.add_hline(y=50, line=dict(color=grey, width=1, dash="dash"), opacity=0.4)
        sp.add_trace(go.Scatter(x=[br_clean.index[-1]], y=[b_now * 100], mode="markers+text",
                                marker=dict(color=warm, size=10),
                                text=[f" {b_now * 100:.0f}%"], textposition="middle right",
                                textfont=dict(color=warm, size=13), showlegend=False))
        sp.update_layout(title="Breadth since 2015", yaxis_title="% above 200d MA",
                         yaxis_range=[0, 100], height=260, **base)
        st.plotly_chart(sp, use_container_width=True)

    with right_1:
        fyld = go.Figure()
        fyld.add_trace(go.Scatter(x=yields.index, y=yields["DGS2"], name="2yr",
                                  line=dict(color=accent, width=2)))
        fyld.add_trace(go.Scatter(x=yields.index, y=yields["DGS10"], name="10yr",
                                  line=dict(color=warm, width=2)))
        fyld.update_layout(title="2yr and 10yr Treasury yields", yaxis_title="Yield (%)",
                           height=260, legend=dict(x=0.02, y=0.98), **base)
        st.plotly_chart(fyld, use_container_width=True)


    # spy/qqq side by side with the 2/10s spread
    left_2, right_2 = st.columns(2)

    with left_2:
        intr = get_intraday(("SPY", "QQQ"), "1d", "5m")
        if intr.empty or intr.shape[0] < 2:
            st.info("Intraday data unavailable right now")
        else:
            fn = go.Figure()
            fn.add_trace(go.Scatter(x=intr.index, y=intr["SPY"], name="SPY",
                                    line=dict(color=accent, width=2)))
            fn.add_trace(go.Scatter(x=intr.index, y=intr["QQQ"], name="QQQ",
                                    line=dict(color=warm, width=2)))
            fn.update_layout(title="Today's SPY and QQQ", yaxis_title="Price ($)",
                             height=260, legend=dict(x=1.02, y=1, xanchor="left"), **base)
            st.plotly_chart(fn, use_container_width=True)

    with right_2:
        fy = go.Figure()
        fy.add_trace(go.Scatter(x=spread.index, y=spread, name="10y − 2y",
                                line=dict(color=green, width=2)))
        fy.add_hline(y=0, line=dict(color=grey, width=1, dash="dash"))
        fy.update_layout(title="Yield curve (10y − 2y)", yaxis_title="Spread (%)",
                         height=260, **base)
        st.plotly_chart(fy, use_container_width=True)


### Breadth Tab ###
with tabs[1]:
    # 200 day breadth plus 50 day line to compare the possible definitions
    br200 = br.rolling(21).mean()
    br50 = B.pct_above_ma(uni_px, ma=50, start=start).rolling(21).mean()

    f = make_subplots(specs=[[{"secondary_y": True}]])
    f.add_trace(go.Scatter(x=br200.index, y=br200 * 100, name=f"% > {ma_len}d MA (21d avg)",
                           line=dict(color=accent, width=2.5)), secondary_y=False)
    f.add_trace(go.Scatter(x=br50.index, y=br50 * 100, name="% > 50d MA (21d avg)",
                           line=dict(color=green, width=1.6)), secondary_y=False)
    f.add_trace(go.Scatter(x=spx.index, y=spx, name="S&P 500 (rebased)",
                           line=dict(color=warm, width=1.3, dash="dot")), secondary_y=True)
    f.add_hline(y=50, line=dict(color=grey, width=1, dash="dash"),
                opacity=0.35, secondary_y=False)
    f.update_yaxes(tickvals=[0, 25, 50, 75, 100],
                   ticktext=["0", "25", "50 (half)", "75", "100"], secondary_y=False)
    f.update_yaxes(title="% above MA", range=[0, 100], secondary_y=False)
    f.update_yaxes(title="S&P 500 (rebased)", secondary_y=True, showgrid=False)
    f.update_layout(title="Market breadth vs the S&P 500", height=340, **base)
    st.plotly_chart(f, use_container_width=True)


    # insight into how top heavy the market is
    fc2 = go.Figure()
    fc2.add_trace(go.Scatter(x=conc.index, y=conc, name="RSP / SPY",
                             line=dict(color=green, width=2)))
    fc2.add_hline(y=100, line=dict(color=grey, width=1, dash="dash"))
    fc2.update_layout(title="Equal-weight vs cap-weight (rebased to 100)",
                      yaxis_title="RSP / SPY", height=300, **base)
    st.plotly_chart(fc2, use_container_width=True)



### Correlation Tab ###
with tabs[2]:
    f = make_subplots(specs=[[{"secondary_y": True}]])
    f.add_trace(go.Scatter(x=corr.index, y=corr, name="Mean pairwise corr",
                           line=dict(color=accent, width=2)), secondary_y=False)
    f.add_trace(go.Scatter(x=spx.index, y=spx, name="S&P 500 (rebased)",
                           line=dict(color=warm, width=1.3, dash="dot")), secondary_y=True)
    f.update_yaxes(title="Mean pairwise correlation", secondary_y=False)
    f.update_yaxes(title="S&P 500 (rebased)", secondary_y=True, showgrid=False)
    f.update_layout(title="Mean pairwise correlation vs the S&P 500", height=300, **base)
    st.plotly_chart(f, use_container_width=True)


    bc = pd.DataFrame({"breadth": br, "corr": corr}).dropna()
    rc = M.ols(bc["breadth"], bc["corr"])
    xs_c = np.linspace(bc["breadth"].min(), bc["breadth"].max(), 50)
    fc = go.Figure()
    fc.add_trace(go.Scatter(x=bc["breadth"] * 100, y=bc["corr"], mode="markers",
                            name="daily obs", marker=dict(size=4, color=warm, opacity=0.30)))
    fc.add_trace(go.Scatter(x=xs_c * 100, y=rc["intercept"] + rc["slope"] * xs_c, name="OLS fit",
                            line=dict(color=accent, width=3)))
    fc.update_layout(title=f"Breadth vs mean pairwise correlation   "
                           f"(slope {rc['slope']*0.1:+.3f} corr / 10% breadth · "
                           f"R²={rc['r2']:.2f} · n={rc['n']:,})",
                     xaxis_title=f"% S&P 500 > {ma_len}d MA",
                     yaxis_title="Mean pairwise correlation", height=300, **base)
    st.plotly_chart(fc, use_container_width=True)



### Signal Tab ###
with tabs[3]:
    r = M.ols(sig["breadth"], sig["fwd_vol"])
    xs = np.linspace(sig["breadth"].min(), sig["breadth"].max(), 50)
    f = go.Figure()
    f.add_trace(go.Scatter(x=sig["breadth"] * 100, y=sig["fwd_vol"] * 100, mode="markers",
                           name="daily obs", marker=dict(size=4, color=accent, opacity=0.30)))
    f.add_trace(go.Scatter(x=xs * 100, y=(r["intercept"] + r["slope"] * xs) * 100, name="OLS fit",
                           line=dict(color=warm, width=3)))
    f.update_layout(title=f"Breadth vs forward {vol_window}-day vol   "
                          f"(slope {r['slope'] * 10:+.1f} vol-pts / 10% breadth · "
                          f"R²={r['r2']:.2f} · n={r['n']:,})",
                    xaxis_title=f"% S&P 500 > {ma_len}d MA",
                    yaxis_title="Forward realized vol %", height=340, **base)
    st.plotly_chart(f, use_container_width=True)

    sig = sig.copy()
    sig["bucket"] = pd.qcut(sig["breadth"].rank(method="first"), 3,
                            labels=["Narrow", "Mid", "Broad"])

    st.markdown("##### Forward volatility by breadth regime, split by market direction")

    up = sig[sig["mkt_up"]]
    down = sig[~sig["mkt_up"]]

    def bucket_means(frame):
        return frame.groupby("bucket", observed=True)["fwd_vol"].mean() * 100

    g_up, g_down = bucket_means(up), bucket_means(down)
    ymax = max(g_up.max(), g_down.max()) * 1.18

    left, right = st.columns(2)

    with left:
        b1 = go.Figure(go.Bar(x=g_up.index, y=g_up.values, width=0.55,
                              marker_color=[red, warm, green],
                              text=[f"{v:.1f}%" for v in g_up], textposition="outside",
                              textfont=dict(size=13)))
        b1.update_layout(title=f"Index rising (n={len(up):,})",
                         yaxis_title="Forward realized vol %", height=300,
                         yaxis_range=[0, ymax], **base)
        st.plotly_chart(b1, use_container_width=True)

    with right:
        b2 = go.Figure(go.Bar(x=g_down.index, y=g_down.values, width=0.55,
                              marker_color=[red, warm, green],
                              text=[f"{v:.1f}%" for v in g_down], textposition="outside",
                              textfont=dict(size=13)))
        b2.update_layout(title=f"Index flat or falling (n={len(down):,})",
                         yaxis_title="Forward realized vol %", height=300,
                         yaxis_range=[0, ymax], **base)
        st.plotly_chart(b2, use_container_width=True)



### Methodology Tab ###
with tabs[4]:
    st.markdown(f"""
### Hypothesis
When fewer stocks are participating in the index's gains, cross-sector correlation and the
volatility that follows both tend to rise.

### Data
Adjusted daily closes are pulled from Yahoo Finance (`auto_adjust=True`). Breadth is determined
from the current S&P 500 members (fixed list). Correlation and concentration use the 11
SPDR sector ETFs plus **SPY** (cap-weighted), **RSP** (equal-weighted), and **QQQ** (Nasdaq-100).
The 2s/10s spread is from FRED, downloaded as a CSV for reproducibility. Sample
starts `{start}`.

### Definitions
- **Breadth** is the share of S&P 500 stocks trading above their own 200-day moving average, measured as of each day.
- **Avg pairwise correlation** is the mean off-diagonal value of the 63-day return correlation matrix.
- **Forward vol** is annualized realized volatility over the next 21 days (`shift(-21)`).
- **Concentration** is RSP divided by SPY, rebased to 100.

### Known limitations
1. **Overlapping forward-vol windows:** Because the 21-day windows overlap day to day, the residuals are correlated, which makes the R-squared and significance look stronger than they really are.
2. **Survivorship bias:** Breadth uses today's S&P 500 membership applied to the full history, so the older data leans toward companies that survived. That pushes historical breadth a little high. Getting the actual members as of each date would need a paid data source, so I held the list fixed instead for reproducibility.
3. **Correlation sample is shorter:** XLC and XLRE launched after 2015, so the fully-aligned correlation series only starts around 2018. Breadth isn't affected since it's built from single names rather than the sector ETFs.
4. **Realized instead of implied data:** I used realized volatility and correlation, which is what actually happened in the market. A trading desk mostly cares about implied vol and correlation, the market's forward-looking pricing of those same things from the options market. A production version would pull that instead, but it needs options data I didn't have here.
""")
