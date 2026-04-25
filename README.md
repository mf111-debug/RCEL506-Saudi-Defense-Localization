# Saudi Arabia Defense Localization Analysis (2010–2030)
## Can Saudi Arabia Reach 50% Defense Localization by 2030?

**Course:** RCEL 506 — Applied Statistics and Data Science for Engineering Leaders  
**Institution:** Rice University  
**Author:** Mohammed Farran  
**Date:** April 2026

---

## Business Problem

Saudi Arabia's Vision 2030 targets 50% defense sector localization by 2030, up from 4% in 2018. This project builds a data-driven forecasting model to assess whether this target is achievable based on observed trends in arms import dependency from 2010 to 2024.

---

## Solution

A time series forecasting pipeline that tracks Saudi Arabia's monthly arms import dependency ratio — defined as Chapter 93 arms imports divided by total military expenditure — using publicly available international trade and defense spending data.

Three models were built and compared:

| Model | R² | RMSE | Role |
|---|---|---|---|
| Rolling Mean | -0.11 | 1.19% | Naive Baseline |
| Linear Regression | **0.47** | **0.82%** | **Best Model** |
| Prophet | -1.15 | 1.65% | Time Series Forecast |

Linear Regression outperformed all models on the test period (2023–2024). Prophet was used for long-term forecasting to 2030.

---

## Key Finding

Saudi Arabia's arms import dependency peaked at **10.85%** in May 2015 during the Yemen conflict and has since declined to **2.29%** by December 2024 — a **77.4% reduction**. The forecast projects this ratio remaining stable and low through 2030, consistent with GAMI's official localization data showing progress from 4% (2018) to 24.89% (2024).

---

## Data Sources

| Source | Variable | Frequency | Period |
|---|---|---|---|
| UN Comtrade (mirror data) | Arms imports to Saudi Arabia (HS Chapter 93, USD) | Monthly | 2010–2024 |
| SIPRI Military Expenditure Database | Saudi military spending (constant 2024 USD millions) | Annual ÷ 12 | 2010–2024 |

**Note on mirror data:** Saudi Arabia does not self-report arms imports to UN Comtrade. This project uses exports reported by all trading partners to Saudi Arabia as a proxy — a standard methodology in defense trade research.

---

## Repository Structure
