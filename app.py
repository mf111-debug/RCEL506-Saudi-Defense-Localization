import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from io import StringIO
import warnings
warnings.filterwarnings('ignore')

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Defense Import Dependency Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS — dark professional theme ──────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Inter:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0D0D0D;
    color: #FFFFFF;
}

.stApp { background-color: #0D0D0D; }

h1, h2, h3 {
    font-family: 'Rajdhani', sans-serif !important;
    letter-spacing: 1px;
}

.metric-card {
    background: #1C1C1C;
    border: 1px solid #2A2A2A;
    border-left: 4px solid #C8F542;
    border-radius: 6px;
    padding: 16px 20px;
    margin: 6px 0;
}

.metric-value {
    font-family: 'Rajdhani', sans-serif;
    font-size: 2.2rem;
    font-weight: 700;
    line-height: 1.1;
}

.metric-label {
    font-size: 0.78rem;
    color: #9E9E9E;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 4px;
}

.country-tag {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    margin: 2px;
}

.header-bar {
    background: linear-gradient(90deg, #1A1A1A 0%, #0D0D0D 100%);
    border-bottom: 2px solid #C8F542;
    padding: 20px 0 16px 0;
    margin-bottom: 24px;
}

.sidebar-section {
    background: #1C1C1C;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
}

.stSelectbox > div > div {
    background-color: #1C1C1C !important;
    border-color: #333 !important;
}

div[data-testid="stSidebarContent"] {
    background-color: #111111;
}
</style>
""", unsafe_allow_html=True)


# ── Country configuration ─────────────────────────────────────────────────────
COUNTRY_CONFIG = {
    "Saudi Arabia": {
        "file_prefix": "TradeData_",
        "sipri_row": 11,
        "color": "#C8F542",
        "partner_filter": None,  # already filtered
    },
    "Türkiye": {
        "file_prefix": "TradeData_T&K_",
        "sipri_row": 12,
        "color": "#E05252",
        "partner_filter": "Türkiye",
    },
    "Rep. of Korea": {
        "file_prefix": "TradeData_T&K_",
        "sipri_row": 9,
        "color": "#4A9FD5",
        "partner_filter": "Rep. of Korea",
    }
}

COUNTRY_DISPLAY = {
    "Saudi Arabia": "Saudi Arabia 🇸🇦",
    "Türkiye": "Türkiye 🇹🇷",
    "Rep. of Korea": "South Korea 🇰🇷",
}


# ── Data loading functions ────────────────────────────────────────────────────
@st.cache_data
def load_arms_data(country_name, start_year=2010, end_year=2024):
    config = COUNTRY_CONFIG[country_name]
    all_years = []

    for year in range(start_year, end_year + 1):
        fname = f"{config['file_prefix']}{year}.csv"
        try:
            with open(fname, 'rb') as f:
                raw = f.read()
            text = raw.decode('utf-8', errors='replace')
            df = pd.read_csv(StringIO(text))
            df['value'] = pd.to_numeric(df['fobvalue'], errors='coerce')

            # Filter by partner country if needed (T&K files have both countries)
            if config['partner_filter']:
                df['partnerDesc'] = df['partnerDesc'].astype(str)
                df = df[df['partnerDesc'].str.contains(config['partner_filter'], na=False)]

            monthly = df.groupby('refMonth')['value'].sum().reset_index()
            monthly.columns = ['YearMonth', 'Arms_Imports_USD']
            all_years.append(monthly)
        except FileNotFoundError:
            continue

    if not all_years:
        return None

    arms = pd.concat(all_years, ignore_index=True)
    arms['Date'] = pd.to_datetime(arms['YearMonth'].astype(str), format='%Y%m')
    arms = arms[['Date', 'Arms_Imports_USD']].sort_values('Date').reset_index(drop=True)
    arms['Arms_Imports_USD_M'] = arms['Arms_Imports_USD'] / 1_000_000
    return arms


@st.cache_data
def load_sipri_data(country_name, start_year=2010, end_year=2024):
    config = COUNTRY_CONFIG[country_name]
    try:
        sipri_raw = pd.read_excel(
            'sipri_milex_raw.xlsx',
            sheet_name='Constant (2024) US$',
            header=None
        )
        years_row = sipri_raw.iloc[5].tolist()
        country_row = sipri_raw.iloc[config['sipri_row']].tolist()

        milex_annual = []
        for i in range(len(years_row)):
            if isinstance(years_row[i], (int, float)) and start_year <= years_row[i] <= end_year:
                milex_annual.append({
                    'Year': int(years_row[i]),
                    'Annual_Milex_USD_M': float(country_row[i])
                })

        milex_df = pd.DataFrame(milex_annual)
        monthly_rows = []
        for _, row in milex_df.iterrows():
            for month in range(1, 13):
                monthly_rows.append({
                    'Date': pd.Timestamp(year=int(row['Year']), month=month, day=1),
                    'Milex_Monthly_USD_M': row['Annual_Milex_USD_M'] / 12
                })
        return pd.DataFrame(monthly_rows)
    except Exception as e:
        st.error(f"Error loading SIPRI data: {e}")
        return None


@st.cache_data
def build_dependency_df(country_name, start_year, end_year):
    arms = load_arms_data(country_name, start_year, end_year)
    milex = load_sipri_data(country_name, start_year, end_year)
    if arms is None or milex is None:
        return None
    df = pd.merge(arms, milex, on='Date')
    df['Import_Dependency_Pct'] = (df['Arms_Imports_USD_M'] / df['Milex_Monthly_USD_M']) * 100
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month
    return df


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛡️ Defense Dashboard")
    st.markdown("---")

    st.markdown("### Country Selection")
    selected_countries = st.multiselect(
        "Select countries to analyze",
        options=list(COUNTRY_CONFIG.keys()),
        default=["Saudi Arabia"],
        format_func=lambda x: COUNTRY_DISPLAY[x]
    )

    st.markdown("### Date Range")
    start_year = st.slider("Start Year", 2010, 2023, 2010)
    end_year = st.slider("End Year", 2011, 2024, 2024)

    st.markdown("### Chart Options")
    show_rolling = st.checkbox("Show 12-Month Rolling Average", value=True)
    show_vision2030 = st.checkbox("Show Vision 2030 Launch (2016)", value=True)
    show_peak = st.checkbox("Annotate Yemen Conflict Peak", value=True)

    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.75rem; color:#666;'>
    <b>Data Sources</b><br>
    • UN Comtrade (HS Ch. 93)<br>
    • SIPRI Military Expenditure DB<br><br>
    <b>Methodology</b><br>
    Import Dependency % =<br>
    Arms Imports / Military Spending × 100
    </div>
    """, unsafe_allow_html=True)


# ── Main content ──────────────────────────────────────────────────────────────
st.markdown("""
<div class='header-bar'>
<h1 style='margin:0; font-size:2.2rem; color:#FFFFFF;'>
🛡️ Defense Import Dependency Dashboard
</h1>
<p style='margin:4px 0 0 0; color:#9E9E9E; font-size:0.9rem;'>
Chapter 93 Arms Imports as % of Military Expenditure — Monthly Analysis
</p>
</div>
""", unsafe_allow_html=True)

if not selected_countries:
    st.warning("Please select at least one country from the sidebar.")
    st.stop()

# ── Load data for selected countries ─────────────────────────────────────────
country_data = {}
for country in selected_countries:
    df = build_dependency_df(country, start_year, end_year)
    if df is not None and len(df) > 0:
        country_data[country] = df
    else:
        st.warning(f"Could not load data for {country}. Check that data files are present.")

if not country_data:
    st.error("No data loaded. Please check your data files.")
    st.stop()

# ── Key metrics row ───────────────────────────────────────────────────────────
st.markdown("### Key Statistics")
metric_cols = st.columns(len(country_data))

for col, (country, df) in zip(metric_cols, country_data.items()):
    config = COUNTRY_CONFIG[country]
    current = df['Import_Dependency_Pct'].iloc[-1]
    peak = df['Import_Dependency_Pct'].max()
    peak_date = df.loc[df['Import_Dependency_Pct'].idxmax(), 'Date'].strftime('%b %Y')
    mean_val = df['Import_Dependency_Pct'].mean()
    reduction = ((peak - current) / peak * 100) if peak > 0 else 0

    with col:
        st.markdown(f"""
        <div style='background:#1C1C1C; border-left: 4px solid {config["color"]}; 
             border-radius:6px; padding:16px; margin-bottom:8px;'>
        <div style='font-size:1rem; font-weight:700; color:{config["color"]}; 
             font-family:Rajdhani,sans-serif; letter-spacing:1px;'>
        {COUNTRY_DISPLAY[country]}
        </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Current (%)", f"{current:.2f}%")
            st.metric("Average (%)", f"{mean_val:.2f}%")
        with c2:
            st.metric("Peak (%)", f"{peak:.2f}%")
            st.metric("Reduction", f"{reduction:.1f}%")


# ── Main trend chart ──────────────────────────────────────────────────────────
st.markdown("### Import Dependency Trend")

fig, ax = plt.subplots(figsize=(14, 6))
fig.patch.set_facecolor('#0D0D0D')
ax.set_facecolor('#141414')

for country, df in country_data.items():
    config = COUNTRY_CONFIG[country]
    color = config['color']

    ax.plot(df['Date'], df['Import_Dependency_Pct'],
            color=color, linewidth=1.0, alpha=0.4)

    if show_rolling:
        rolling = df['Import_Dependency_Pct'].rolling(window=12).mean()
        ax.plot(df['Date'], rolling,
                color=color, linewidth=2.5,
                label=f"{COUNTRY_DISPLAY[country]} (12M avg)")
    else:
        ax.plot(df['Date'], df['Import_Dependency_Pct'],
                color=color, linewidth=1.8,
                label=COUNTRY_DISPLAY[country])

if show_vision2030:
    ax.axvline(pd.Timestamp('2016-04-01'), color='#888888',
               linestyle='--', linewidth=1.5, alpha=0.7, label='Vision 2030 Launch')

if show_peak and 'Saudi Arabia' in country_data:
    sa_df = country_data['Saudi Arabia']
    peak_idx = sa_df['Import_Dependency_Pct'].idxmax()
    peak_date = sa_df.loc[peak_idx, 'Date']
    peak_val = sa_df.loc[peak_idx, 'Import_Dependency_Pct']
    ax.annotate('Peak: May 2015\nYemen Conflict',
                xy=(peak_date, peak_val),
                xytext=(pd.Timestamp('2013-01-01'), peak_val * 0.85),
                arrowprops=dict(arrowstyle='->', color='#CCCCCC'),
                fontsize=9, color='#FFFF99',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#333300', alpha=0.8))

ax.set_title("Arms Import Dependency — Monthly Data",
             fontsize=14, fontweight='bold', color='#FFFFFF', pad=12)
ax.set_xlabel("Date", fontsize=11, color='#9E9E9E')
ax.set_ylabel("Import Dependency (%)", fontsize=11, color='#9E9E9E')
ax.tick_params(colors='#9E9E9E')
ax.spines['bottom'].set_color('#333333')
ax.spines['left'].set_color('#333333')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.legend(fontsize=10, facecolor='#1C1C1C', edgecolor='#333333',
          labelcolor='#FFFFFF', loc='upper right')
ax.grid(True, color='#1F1F1F', linewidth=0.8)

plt.tight_layout()
st.pyplot(fig)
plt.close()


# ── Annual comparison bar chart ───────────────────────────────────────────────
st.markdown("### Annual Average Comparison")

fig2, ax2 = plt.subplots(figsize=(14, 5))
fig2.patch.set_facecolor('#0D0D0D')
ax2.set_facecolor('#141414')

years_range = list(range(start_year, end_year + 1))
n_countries = len(country_data)
width = 0.8 / n_countries
offsets = np.linspace(-(n_countries - 1) / 2, (n_countries - 1) / 2, n_countries) * width

for idx, (country, df) in enumerate(country_data.items()):
    config = COUNTRY_CONFIG[country]
    annual_avg = df.groupby('Year')['Import_Dependency_Pct'].mean()
    x_pos = [y + offsets[idx] for y in years_range if y in annual_avg.index]
    y_vals = [annual_avg[y] for y in years_range if y in annual_avg.index]
    ax2.bar(x_pos, y_vals, width=width * 0.9,
            color=config['color'], alpha=0.8,
            label=COUNTRY_DISPLAY[country])

ax2.set_title("Annual Average Import Dependency by Country",
              fontsize=13, fontweight='bold', color='#FFFFFF', pad=10)
ax2.set_xlabel("Year", fontsize=11, color='#9E9E9E')
ax2.set_ylabel("Import Dependency (%)", fontsize=11, color='#9E9E9E')
ax2.tick_params(colors='#9E9E9E')
ax2.set_xticks(years_range)
ax2.set_xticklabels(years_range, rotation=45)
ax2.spines['bottom'].set_color('#333333')
ax2.spines['left'].set_color('#333333')
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.legend(fontsize=10, facecolor='#1C1C1C', edgecolor='#333333', labelcolor='#FFFFFF')
ax2.grid(True, axis='y', color='#1F1F1F', linewidth=0.8)

plt.tight_layout()
st.pyplot(fig2)
plt.close()


# ── Raw data table ────────────────────────────────────────────────────────────
with st.expander("📊 View Raw Monthly Data"):
    for country, df in country_data.items():
        config = COUNTRY_CONFIG[country]
        st.markdown(f"**{COUNTRY_DISPLAY[country]}**")
        display_df = df[['Date', 'Arms_Imports_USD_M', 'Milex_Monthly_USD_M', 'Import_Dependency_Pct']].copy()
        display_df.columns = ['Date', 'Arms Imports (USD M)', 'Military Spending (USD M)', 'Import Dependency (%)']
        display_df['Import Dependency (%)'] = display_df['Import Dependency (%)'].round(3)
        display_df['Arms Imports (USD M)'] = display_df['Arms Imports (USD M)'].round(2)
        display_df['Military Spending (USD M)'] = display_df['Military Spending (USD M)'].round(2)
        st.dataframe(display_df, use_container_width=True)


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align:center; color:#555; font-size:0.8rem; padding:16px 0;'>
RCEL 506 — Applied Statistics and Data Science for Engineering Leaders<br>
Rice University | Mohammed Farran | April 2026<br>
Data: UN Comtrade (HS Chapter 93) + SIPRI Military Expenditure Database
</div>
""", unsafe_allow_html=True)
