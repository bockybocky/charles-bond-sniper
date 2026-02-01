import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re

# --- 1. 頁面基礎設定 ---
st.set_page_config(
    page_title="Charles 戰情室 V17.3 Smart", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🎨 核心美化模組 (Dark Mode)
# ==========================================
def inject_custom_css():
    st.markdown("""
        <style>
        .stApp { background-color: #0E1117; color: #FAFAFA; font-family: 'Microsoft JhengHei', sans-serif; }
        [data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #30363D; }
        h1 { background: linear-gradient(to right, #00E5FF, #2979FF); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800 !important; font-size: 2.2rem !important; }
        div[data-testid="stMetricValue"] { font-size: 2rem; color: #00FFD1; font-weight: 700; text-shadow: 0 0 10px rgba(0, 255, 209, 0.3); }
        div[data-testid="stMetricLabel"] { color: #8B949E; }
        .stTabs [data-baseweb="tab"] { background-color: #21262D; color: #C9D1D9; border: 1px solid #30363D; }
        .stTabs [aria-selected="true"] { background-color: #1F6FEB !important; color: white !important; border: 1px solid #1F6FEB; }
        [data-testid="stDataFrame"] { border: 1px solid #30363D; }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ==========================================
# 🧠 智能偵測引擎 (Smart Detection Engine)
# ==========================================
def detect_columns(df):
    """
    不依賴欄位名稱，直接分析內容來猜測哪一欄是 CUSIP，哪一欄是 Issue Date
    """
    col_cusip = None
    col_issue = None
    
    # 1. 偵測 CUSIP (特徵：9碼，英數混合)
    # 我們計算每一欄符合 CUSIP 格式的比例
    max_cusip_match = 0
    for col in df.columns:
        # 轉成字串並去除空白
        sample = df[col].astype(str).str.strip()
        # 計算符合 9 碼且包含數字的比例
        matches = sample.str.match(r'^[A-Z0-9]{9}$', case=False).sum()
        ratio = matches / len(df)
        
        if ratio > 0.5 and ratio > max_cusip_match: # 假設超過 50% 的列符合格式
            max_cusip_match = ratio
            col_cusip = col

    # 2. 偵測 Issue Date (特徵：日期格式)
    max_date_match = 0
    for col in df.columns:
        if col == col_cusip: continue # 跳過已認定為 CUSIP 的欄位
        
        # 嘗試轉換日期
        try:
            sample = pd.to_datetime(df[col], errors='coerce')
            valid_dates = sample.notna().sum()
            ratio = valid_dates / len(df)
            
            if ratio > 0.5 and ratio > max_date_match:
                max_date_match = ratio
                col_issue = col
        except:
            continue
            
    return col_cusip, col_issue

def load_master_data_smart(file):
    """
    智能讀取 Master File，處理無 Header 或亂 Header 的情況
    """
    try:
        # 先嘗試用預設讀取 (假設有 Header)
        file.seek(0)
        df = pd.read_csv(file)
        
        # 檢查是否讀取失敗 (例如第一行就被當成 Header 吃掉了數據)
        # 如果欄位名稱看起來像 CUSIP (如 "958102AT2")，代表它是無 Header 檔
        is_headless = False
        for col in df.columns:
            if re.match(r'^[A-Z0-9]{9}$', str(col), re.IGNORECASE):
                is_headless = True
                break
        
        if is_headless:
            file.seek(0)
            df = pd.read_csv(file, header=None) # 重新讀取，不設 Header
            
        # 啟動智能偵測
        c_cusip, c_issue = detect_columns(df)
        
        if c_cusip is not None and c_issue is not None:
            # 標準化輸出
            df_clean = pd.DataFrame()
            df_clean['CUSIP'] = df[c_cusip].astype(str).str.strip()
            df_clean['Issue_Date_Clean'] = pd.to_datetime(df[c_issue], errors='coerce')
            return df_clean, f"✅ 智能偵測成功 (CUSIP欄: {c_cusip}, 日期欄: {c_issue})"
        else:
            return None, "❌ 無法自動識別 CUSIP 或日期欄位，請檢查檔案格式。"
            
    except Exception as e:
        return None, f"讀取錯誤: {str(e)}"

# --- 核心工具 ---
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

# --- 主程式 ---
st.title("Charles 戰情室 V17.3 Smart")
st.caption("VIC System // 智能發行日對接")

with st.expander("📘 操作手冊 (V17.3)", expanded=False):
    st.markdown("""
    * **左側上傳：** iShares 官方 `ICVT_holdings.csv`
    * **右側上傳：** 您的 `convertible_notes_issue_dates.csv` (支援無標題格式)
    * **系統功能：** 自動抓取 CUSIP 與日期，計算發行年份。
    """)

# 側邊欄
with st.sidebar:
    st.markdown("### 🎛️ 戰術控制台")
    st.markdown("#### 💀 死亡鎖定")
    danger_price = st.slider("危險價格門檻", 50.0, 100.0, 95.0, 1.0)
    ignore_coupon = st.checkbox("無視票面利率", value=True)
    st.divider()
    st.markdown("#### 🚀 火箭鎖定")
    rocket_price = st.slider("火箭價格門檻", 100.0, 200.0, 130.0, 5.0)

# 上傳區
c1, c2 = st.columns(2)
with c1:
    uploaded_file = st.file_uploader("1. 上傳 ICVT 官方檔", type=['csv'], label_visibility="visible", key="main")
with c2:
    uploaded_master = st.file_uploader("2. 上傳發行日檔 (Master)", type=['csv'], label_visibility="visible", key="master")

# 邏輯處理
if uploaded_file is not None:
    df, error_msg = robust_parser(uploaded_file)
    
    if error_msg:
        st.error(f"❌ 官方檔案錯誤: {error_msg}")
    else:
        try:
            # 1. 基礎清洗
            df.columns = df.columns.str.strip()
            col_name = find_column(df, ['Name', 'Issuer Name'])
            col_market = find_column(df, ['Market Value', 'Market Value ($)'])
            col_par = find_column(df, ['Par Value', 'Par'])
            col_maturity = find_column(df, ['Maturity', 'Maturity Date'])
            col_coupon = find_column(df, ['Coupon (%)', 'Coupon'])
            col_cusip = find_column(df, ['CUSIP', 'ISIN'])

            if not (col_name and col_market and col_par and col_maturity):
                st.error("❌ 官方檔案缺少關鍵欄位")
            else:
                df['Name_Clean'] = df[col_name]
                df['Market_Clean'] = df[col_market].apply(clean_currency)
                df['Par_Clean'] = df[col_par].apply(clean_currency)
                df['Maturity_Dt'] = pd.to_datetime(df[col_maturity], errors='coerce')
                df['Coupon_Clean'] = df[col_coupon].apply(clean_currency) if col_coupon else 0.0

                # 2. 智能融合 Master Data
                df['Issue_Year'] = None
                if uploaded_master is not None:
                    df_master_clean, msg = load_master_data_smart(uploaded_master)
                    if df_master_clean is not None:
                        st.success(msg)
                        # Merge
                        if col_cusip:
                            df[col_cusip] = df[col_cusip].astype(str).str.strip()
                            df = df.merge(df_master_clean, left_on=col_cusip, right_on='CUSIP', how='left')
                            df['Issue_Year'] = df['Issue_Date_Clean'].dt.year
                            
                            # 顯示對接狀況
                            matched_count = df['Issue_Year'].notna().sum()
                            st.info(f"🔗 已成功對接 {matched_count} 筆發行年份數據")
                    else:
                        st.warning(msg)

                # 3. 篩選與顯示
                df_valid = df.dropna(subset=['Market_Clean', 'Par_Clean', 'Maturity_Dt']).copy()
                df_valid['Bond_Price'] = (df_valid['Market_Clean'] / df_valid['Par_Clean']) * 100
                df_valid['Ticker_Search'] = "https://www.google.com/search?q=" + df_valid['Name_Clean'].str.replace(' ', '+') + "+stock+ticker"
                
                # 時間過濾 2026-2027
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
                    danger = danger.sort_values(by='Maturity_Dt')
                    rocket = rocket.sort_values(by='Maturity_Dt')
                    df_all = df_time.sort_values(by='Maturity_Dt')

                    # 儀表板
                    st.markdown("---")
                    c1_m, c2_m, c3_m = st.columns(3)
                    c1_m.metric("📊 戰術雷達", f"{len(df_time)}", "2026-27 目標")
                    c2_m.metric("💀 死亡名單", f"{len(danger)}", f"佔比 {len(danger)/len(df_time):.1%}")
                    c3_m.metric("🚀 火箭名單", f"{len(rocket)}", f"佔比 {len(rocket)/len(df_time):.1%}")
                    st.markdown("---")

                    t1, t2, t3 = st.tabs(["💀 死亡名單", "🚀 火箭名單", "📋 完整戰報"])
                    
                    cfg = {
                        "Name_Clean": st.column_config.TextColumn("公司名稱", width="large"),
                        "Ticker_Search": st.column_config.LinkColumn("資訊", display_text="🔍", width="small"),
                        "Maturity_Dt": st.column_config.DateColumn("到期日", format="YYYY-MM-DD"),
                        "Issue_Year": st.column_config.NumberColumn("發行年", format="%d"),
                        "Bond_Price": st.column_config.ProgressColumn("價格強度", format="$%.2f", min_value=0, max_value=200),
                        "Coupon_Clean": st.column_config.NumberColumn("票面利率", format="%.2f%%"),
                        "Par_Clean": st.column_config.NumberColumn("票面總額", format="$%d"),
                        "Market_Clean": st.column_config.NumberColumn("持有市值", format="$%d")
                    }
                    cols = ['Name_Clean', 'Ticker_Search', 'Maturity_Dt', 'Issue_Year', 'Coupon_Clean', 'Bond_Price', 'Par_Clean']

                    with t1: st.dataframe(danger[cols], column_config=cfg, hide_index=True, use_container_width=True)
                    with t2: st.dataframe(rocket[cols], column_config=cfg, hide_index=True, use_container_width=True)
                    with t3: st.dataframe(df_all[cols], column_config=cfg, hide_index=True, use_container_width=True)
                else:
                    st.warning("⚠️ 此區間無目標。")

        except Exception as e:
            st.error(f"❌ 系統錯誤: {e}")
