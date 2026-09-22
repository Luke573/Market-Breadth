**Market Breadth, Correlation and Concentration**

The goal of this project was to create a Streamlit dashboard that tests whether
narrow market breadth leads to higher cross-sector correlation and higher future 
volatility in the S&P 500.

Dashboard: https://market-breadth-cmqffdpng2jmebxzionmwt.streamlit.app/

**Question**

When fewer stocks participate in the index's gains, do correlation and the volatility 
that follows tend to rise?

**Findings**

My findings are based on the default controls: 200-day breadth, 63-day correlation, 
21-day forward volatility, and 2015-01-01 as the start date.

-Breadth and forward volatility are negatively correlated. Dropping 10 points in breadth
leads to about a 2.4 point rise in forward realized volatility on the SPY (R^2 of 0.20)
-The effect is exacerbated when the direction of the market is flat or falling. It is 
important to note that this could be due to a lower sample size than a rising market.
-Breadth and cross-sector correlation are also negatively correlated. Similar to the 
volatility comparison, this correlation is loose with an R^2 of 0.22.
-As of September 2026, ~51% of S&P 500 stocks are above their 200-day average, cross
sector correlation is 0.13, and the equal weight RSP has underperformed the cap-weighted
SPY by ~29% since 2015.

**Data**

-Ticker data is retrieved from the yfinance Python library which is Yahoo Finance.
-Breadth uses a set list of current S&P 500 members.
-Correlation uses the 11 SPDR sector ETFs.
-Concentration is the RSP divided by the SPY, rebased to 100 to show their growth.
-2s/10s Treasury spread is downloaded as a csv from FRED.

**Limitations**

-Forward vol windows overlap from day to day which overstates the R^2 value.
-Using todays members for the full history introduces survivorship bias and likely raises
the historical breadth.
-XLC and XLRE launched in 2018, so the correlation series starts later.
