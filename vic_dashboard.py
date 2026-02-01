import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. 頁面基礎設定 (維持 Wide 佈局) ---
st.set_page_config(
    page_title="Charles 戰情室 V17.1 Dark", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🎨 核心美化模組 (Dark Mode - 彭博戰術風格)
# ==========================================
def inject_custom_css():
    st.markdown("""
        <style>
        /* 全局背景：深空灰 */
        .stApp {
            background-color: #0E1117;
            color: #FAFAFA; 
            font-family: 'SF Mono', 'Roboto Mono', 'Segoe UI', sans-serif; /* 改用等寬字體增加科技感 */
        }
        
        /* 側邊欄：更深的灰 */
        [data-testid="stSidebar"] {
            background-color: #161B22;
            border-right: 1px solid #30363D;
        }
        
        /* 標題 H1：霓虹漸層 */
        h1 {
            background: linear-gradient(to right, #00E5FF, #2979FF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800 !important;
            font-size: 2.2rem !important;
            margin-bottom: 10px;
            padding-top: 10px;
            letter-spacing: 1px;
        }
        
        /* 副標題說明文字 */
        .sidebar-text {
            color: #8B949E;
            font-size: 0.85rem;
        }
        
        /* 關鍵指標 (Metric) 數字：高亮霓虹青 */
        div[data-testid="stMetricValue"] {
            font-size: 2rem;
            color: #00FFD1; /* Neon Cyan */
            font-weight: 700;
            text-shadow: 0 0 10px rgba(0, 255, 209, 0.3);
        }
        div[data-testid="stMetricLabel"] {
            color: #8B949E;
        }
        
        /* 分頁籤 (Tabs) */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            height: 45px;
            background-color: #21262D;
            border-radius: 4px; 
            color: #C9D1D9;
            font-size: 1rem;
            font-weight: 600;
            border: 1px solid #30363D;
        }
        .stTabs [aria-selected="true"] {
            background-color: #1F6FEB !important; 
            color: white !important;
            border: 1px solid #1F6FEB;
            box-shadow: 0 0 8px rgba(31, 111, 235, 0.4);
        }

        /* 表格優化 (強制暗色模式適配) */
        [data-testid="stDataFrame"] {
            border: 1px solid #30363D;
            border-radius: 5px;
        }
        
        /* 提示框顏色微調 */
        .stAlert {
            background-color: #161B22;
            border: 1px solid #30363D;
            color: #C9D1D9;
        }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ==========================================
# 📖 說明模組
# ==========================================
def render_user_guide():
    with st.expander("📘 指揮官操作手冊 (V17.1 暗黑戰術版)", expanded=False):
        st.markdown("""
        #### 1️⃣ 數據源 (官方情報)
        * 請至 [iShares US](https://www.ishares.com/us) 搜尋 `ICVT` 下載 CSV。
        
        #### 2️⃣ 外部情報 (私有庫)
        * **Master Bond Data:** CSV 需包含 `CUSIP` 和 `Issue Date`。
        
        #### 3️⃣ 戰術看板解讀
        * **💀 死亡名單:** 價格低於門檻 (預設 $95)。
        * **🚀 火箭名單:** 價格高於門檻 (預設 $130)。
        """)

# --- 2. 側邊欄 ---
with st.sidebar:
    st.markdown("### 🎛️ 戰術控制台")
    st.markdown('<p class="sidebar-text">參數設定 // Parameter Setup</p>', unsafe_allow_html=True)
    st.divider()
    
    st.markdown("#### 💀 死亡鎖定 (Short)")
    danger_price = st.slider("危險價格門檻", 50.0, 100.0, 95.0, 1.0)
    ignore_coupon = st.checkbox("無視票面利率 (只看價格)", value=True)
    
    st.divider()
    
    st.markdown("#### 🚀 火箭鎖定 (Long)")
    rocket_price = st.slider("火箭價格門檻", 100.0, 200.0, 130.0, 5.0)

    st.divider()
    debug_mode = st.toggle("🐞 除錯模式", value=False)

# --- 3. 核心清洗引擎 ---
def clean_currency(x):
    if isinstance(x, (int, float)): return x
    if pd.isna(x) or str(x).strip() in ['-', '']: return None
    clean_str = str(x).replace('$', '').replace(',', '').replace('"', '').strip()
    try: return float(clean_str)
    except: return None

def find_column(df, candidates):
    for col in df.columns:
        for cand in candidates:
            if cand.lower() == col.strip().lower():
                return col
    return None

def robust_parser(file):
    bytes_data = file.getvalue()
    text_data = None
    for enc in ['utf-8', 'cp1252', 'latin1']:
        try:
            text_data = bytes_data.decode(enc, errors='ignore')
            break
        except: continue
    if not text_data: return None, "無法解碼檔案"
    
    lines = text_data.splitlines()
    header_idx = -1
    for i, line in enumerate(lines[:50]):
        if "Market Value" in line and ("Name" in line or "Issuer" in line):
            header_idx = i
            break
    if header_idx == -1: return None, "找不到標題列"
    
    try:
        clean_content = "\n".join(lines[header_idx:])
        df = pd.read_csv(io.StringIO(clean_content), quotechar='"')
        return df, None
    except Exception as e: return None, str(e)

# --- 4. 主程式邏輯 ---
st.title("Charles Convertible Sniper")
st.caption("VIC System V17.1 // Dark Knight Edition")

render_user_guide()

c_upload1, c_upload2 = st.columns(2)
with c_upload1:
    st.markdown("### 1. 載入官方情報 (ICVT)")
    uploaded_file = st.file_uploader("選擇 ICVT Holdings CSV", type=['csv'], label_visibility="collapsed", key="main_file")

with c_upload2:
    st.markdown("### 2. 載入私有情報 (Issue Date)")
    uploaded_master = st.file_uploader("選擇 Master Bond CSV", type=['csv'], label_visibility="collapsed", key="master_file")

if uploaded_file is not None:
    df, error_msg = robust_parser(uploaded_file)
    
    if error_msg:
        st.error(f"❌ 官方檔案讀取失敗: {error_msg}")
    else:
        try:
            # 1. 欄位處理
            df.columns = df.columns.str.strip()
            col_name = find_column(df, ['Name', 'Issuer Name', 'Security Name'])
            col_market = find_column(df, ['Market Value', 'Market Value ($)', 'Mkt Val'])
            col_par = find_column(df, ['Par Value', 'Par', 'Principal Amount'])
            col_maturity = find_column(df, ['Maturity', 'Maturity Date', 'Mat Date', 'Due Date'])
            col_coupon = find_column(df, ['Coupon (%)', 'Coupon', 'Cpn'])
            col_cusip = find_column(df, ['CUSIP', 'ISIN'])

            missing_cols = []
            if not col_name: missing_cols.append("公司名稱")
            if not col_market: missing_cols.append("市值")
            if not col_par: missing_cols.append("票面")
            if not col_maturity: missing_cols.append("到期日")

            if missing_cols:
                st.error(f"❌ 缺損: {', '.join(missing_cols)}")
            else:
                df['Name_Clean'] = df[col_name]
                df['Market_Clean'] = df[col_market].apply(clean_currency)
                df['Par_Clean'] = df[col_par].apply(clean_currency)
                df['Maturity_Dt'] = pd.to_datetime(df[col_maturity], errors='coerce')
                
                if col_coupon:
                    df['Coupon_Clean'] = df[col_coupon].apply(clean_currency)
                else:
                    df['Coupon_Clean'] = 0.0

                # 2. 情報融合 (Issue Year)
                df['Issue_Year'] = None
                
                if uploaded_master is not None:
                    try:
                        df_master = pd.read_csv(uploaded_master)
                        m_cusip = find_column(df_master, ['CUSIP', 'ID', 'ISIN'])
                        m_issue = find_column(df_master, ['Issue Date', 'Issue', 'Dated Date', 'Start Date'])
                        
                        if m_cusip and m_issue and col_cusip:
                            df_master[m_cusip] = df_master[m_cusip].astype(str).str.strip()
                            df_master['Issue_Date_Clean'] = pd.to_datetime(df_master[m_issue], errors='coerce')
                            df[col_cusip] = df[col_cusip].astype(str).str.strip()
                            
                            df_merged = df.merge(df_master[[m_cusip, 'Issue_Date_Clean']], left_on=col_cusip, right_on=m_cusip, how='left')
                            df['Issue_Year'] = df_merged['Issue_Date_Clean'].dt.year
                            st.success(f"✅ 情報融合成功: {df_merged['Issue_Date_Clean'].notna().sum()} 筆")
                    except:
                        st.warning("⚠️ 私有檔案讀取異常")

                # 3. 核心計算
                df_valid = df.dropna(subset=['Market_Clean', 'Par_Clean', 'Maturity_Dt']).copy()
                df_valid['Bond_Price'] = (df_valid['Market_Clean'] / df_valid['Par_Clean']) * 100
                df_valid['Ticker_Search'] = "https://www.google.com/search?q=" + df_valid['Name_Clean'].str.replace(' ', '+') + "+stock+ticker"
                
                mask_date = (df_valid['Maturity_Dt'] >= datetime(2026, 1, 1)) & \
                            (df_valid['Maturity_Dt'] <= datetime(2027, 12, 31))
                df_time = df_valid[mask_date].copy()
                
                if len(df_time) > 0:
                    if ignore_coupon:
                        danger = df_time[df_time['Bond_Price'] < danger_price]
                    else:
                        danger = df_time[(df_time['Bond_Price'] < danger_price) & (df_time['Coupon_Clean'] < 2.0)]
                    
                    rocket = df_time[df_time['Bond_Price'] > rocket_price]
                    
                    # 排序
                    danger = danger.sort_values(by='Maturity_Dt', ascending=True)
                    rocket = rocket.sort_values(by='Maturity_Dt', ascending=True)
                    df_all = df_time.sort_values(by='Maturity_Dt', ascending=True)
                    
                    # --- 4. 儀表板顯示 ---
                    st.markdown("---")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("📊 戰術雷達", f"{len(df_time)}", "2026-27 Targets")
                    c2.metric("💀 死亡名單", f"{len(danger)}", f"Rate: {len(danger)/len(df_time):.1%}", delta_color="off")
                    c3.metric("🚀 火箭名單", f"{len(rocket)}", f"Rate: {len(rocket)/len(df_time):.1%}", delta_color="normal")
                    st.markdown("---")

                    tab1, tab2, tab3 = st.tabs(["💀 DEATH LIST", "🚀 ROCKET LIST", "📋 FULL REPORT"])
                    
                    col_cfg = {
                        "Name_Clean": st.column_config.TextColumn("Company", width="large"),
                        "Ticker_Search": st.column_config.LinkColumn("Info", display_text="🔍", width="small"),
                        "Maturity_Dt": st.column_config.DateColumn("Maturity", format="YYYY-MM-DD", width="medium"),
                        "Issue_Year": st.column_config.NumberColumn("Issue Yr", format="%d", width="small"),
                        "Bond_Price": st.column_config.ProgressColumn("Price Strength", format="$%.2f", min_value=0, max_value=200, width="medium"),
                        "Coupon_Clean": st.column_config.NumberColumn("Cpn %", format="%.2f%%", width="small"),
                        "Par_Clean": st.column_config.NumberColumn("Par Value ($)", format="$%d", width="medium"),
                        "Market_Clean": st.column_config.NumberColumn("Mkt Value ($)", format="$%d", width="medium")
                    }
                    
                    final_cols = ['Name_Clean', 'Ticker_Search', 'Maturity_Dt', 'Issue_Year', 'Coupon_Clean', 'Bond_Price', 'Par_Clean']

                    with tab1:
                        if not danger.empty:
                            st.dataframe(danger[final_cols], column_config=col_cfg, use_container_width=True, hide_index=True)
                        else: st.info("✅ NO THREATS DETECTED.")

                    with tab2:
                        if not rocket.empty:
                            st.dataframe(rocket[final_cols], column_config=col_cfg, use_container_width=True, hide_index=True)
                        else: st.info("⚠️ NO TARGETS.")
                        
                    with tab3:
                        st.dataframe(df_all[final_cols], column_config=col_cfg, use_container_width=True, hide_index=True)
                else:
                    st.warning("⚠️ NO DATA FOUND FOR 2026-2027.")
        except Exception as e:
            st.error(f"❌ SYSTEM ERROR: {e}")
            if debug_mode: st.exception(e)
