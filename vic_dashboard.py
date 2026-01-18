import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. 頁面基礎設定 ---
st.set_page_config(
    page_title="Charles 戰情室 V16.0", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🎨 核心美化模組 (Light Mode)
# ==========================================
def inject_custom_css():
    st.markdown("""
        <style>
        .stApp {
            background-color: #FFFFFF;
            color: #1F2937; 
            font-family: 'Segoe UI', 'Roboto', Helvetica, Arial, sans-serif;
        }
        h1 {
            background: linear-gradient(to right, #003366, #0052cc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800 !important;
            font-size: 2.5rem !important;
            margin-bottom: 0px;
            padding-top: 10px;
        }
        [data-testid="stSidebar"] {
            background-color: #F8F9FA;
            border-right: 1px solid #E5E7EB;
        }
        .sidebar-text {
            color: #4B5563;
            font-size: 0.9rem;
            margin-bottom: 20px;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            height: 45px;
            background-color: #F3F4F6;
            border-radius: 4px; 
            color: #4B5563;
            font-size: 1rem;
            font-weight: 600;
            border: 1px solid #E5E7EB;
        }
        .stTabs [aria-selected="true"] {
            background-color: #0052cc !important; 
            color: white !important;
            border: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.8rem;
            color: #003366;
            font-weight: 700;
        }
        thead tr th {
            background-color: #F3F4F6 !important;
            color: #111827 !important;
        }
        thead tr th:first-child {display:none}
        tbody th {display:none}
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ==========================================
# 📖 說明模組
# ==========================================
def render_user_guide():
    with st.expander("📘 指揮官操作手冊 (點我展開)", expanded=False):
        st.markdown("""
        #### 1️⃣ 數據源
        * 請至 [iShares US](https://www.ishares.com/us) 搜尋 `ICVT` 下載 CSV。
        
        #### 2️⃣ 戰術看板解讀
        * **排序：** 依 **「到期日 (近 -> 遠)」** 排列。
        * **💀 死亡名單：** 價格 < $95 (還款壓力大)。
        * **🚀 火箭名單：** 價格 > $130 (轉股獲利)。
        """)

# --- 2. 側邊欄 ---
with st.sidebar:
    st.markdown("### 🎛️ 戰術控制台")
    st.markdown('<p class="sidebar-text">調整參數以過濾戰情名單。</p>', unsafe_allow_html=True)
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
        # 放寬條件：只要有 Market Value 就算找到
        if "Market Value" in line and ("Name" in line or "Issuer" in line):
            header_idx = i
            break
    if header_idx == -1: return None, "找不到標題列 (需包含 Name/Issuer 和 Market Value)"
    
    try:
        clean_content = "\n".join(lines[header_idx:])
        df = pd.read_csv(io.StringIO(clean_content), quotechar='"')
        return df, None
    except Exception as e: return None, str(e)

# --- 4. 主程式邏輯 ---
st.title("Charles Convertible Sniper")
st.caption("VIC System V16.0 // Stable Core")

render_user_guide()

st.markdown("### 📂 Upload Mission Data")
uploaded_file = st.file_uploader("請上傳 iShares CSV 檔案", type=['csv'], label_visibility="collapsed")

if uploaded_file is not None:
    df, error_msg = robust_parser(uploaded_file)
    
    if error_msg:
        st.error(f"❌ 檔案讀取失敗: {error_msg}")
    else:
        if debug_mode:
            st.warning("🐞 Raw Data Preview")
            st.dataframe(df.head())

        try:
            # 1. 欄位標準化
            df.columns = df.columns.str.strip()
            
            # 2. 智慧尋找關鍵欄位
            col_name = find_column(df, ['Name', 'Issuer Name', 'Security Name'])
            col_market = find_column(df, ['Market Value', 'Market Value ($)', 'Mkt Val'])
            col_par = find_column(df, ['Par Value', 'Par', 'Principal Amount'])
            col_maturity = find_column(df, ['Maturity', 'Maturity Date', 'Mat Date', 'Due Date'])
            col_coupon = find_column(df, ['Coupon (%)', 'Coupon', 'Cpn'])

            # 3. 檢查
            missing_cols = []
            if not col_name: missing_cols.append("公司名稱 (Name)")
            if not col_market: missing_cols.append("市值 (Market Value)")
            if not col_par: missing_cols.append("票面 (Par Value)")
            if not col_maturity: missing_cols.append("到期日 (Maturity)")

            if missing_cols:
                st.error(f"❌ 檔案缺少關鍵欄位，無法分析: {', '.join(missing_cols)}")
            else:
                # 4. 清洗
                df['Name_Clean'] = df[col_name]
                df['Market_Clean'] = df[col_market].apply(clean_currency)
                df['Par_Clean'] = df[col_par].apply(clean_currency)
                
                # 確保 Maturity_Dt 正確生成
                df['Maturity_Dt'] = pd.to_datetime(df[col_maturity], errors='coerce')
                
                # 若有 Coupon 則清洗
                if col_coupon:
                    df['Coupon_Clean'] = df[col_coupon].apply(clean_currency)
                else:
                    df['Coupon_Clean'] = 0.0

                # 5. 計算
                df_valid = df.dropna(subset=['Market_Clean', 'Par_Clean', 'Maturity_Dt']).copy()
                df_valid['Bond_Price'] = (df_valid['Market_Clean'] / df_valid['Par_Clean']) * 100
                
                df_valid['Ticker_Search'] = "https://www.google.com/search?q=" + df_valid['Name_Clean'].str.replace(' ', '+') + "+stock+ticker"
                
                # 鎖定 2026-2027
                mask_date = (df_valid['Maturity_Dt'] >= datetime(2026, 1, 1)) & \
                            (df_valid['Maturity_Dt'] <= datetime(2027, 12, 31))
                df_time = df_valid[mask_date].copy()
                
                if len(df_time) > 0:
                    # 篩選
                    if ignore_coupon:
                        danger = df_time[df_time['Bond_Price'] < danger_price]
                    else:
                        danger = df_time[(df_time['Bond_Price'] < danger_price) & (df_time['Coupon_Clean'] < 2.0)]
                    
                    rocket = df_time[df_time['Bond_Price'] > rocket_price]

                    # 排序：到期日由近到遠
                    danger = danger.sort_values(by='Maturity_Dt', ascending=True)
                    rocket = rocket.sort_values(by='Maturity_Dt', ascending=True)
                    df_all = df_time.sort_values(by='Maturity_Dt', ascending=True)
                    
                    # --- 顯示 ---
                    st.markdown("---")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("📊 掃描總數", f"{len(df_time)}", "2026-27 到期")
                    c2.metric("💀 死亡鎖定", f"{len(danger)}", f"佔比 {len(danger)/len(df_time):.1%}", delta_color="inverse")
                    c3.metric("🚀 火箭鎖定", f"{len(rocket)}", f"佔比 {len(rocket)/len(df_time):.1%}")
                    st.markdown("---")

                    tab1, tab2, tab3 = st.tabs(["💀 死亡名單", "🚀 火箭名單", "📋 完整戰報"])
                    
                    # 設定欄位對應
                    # 直接使用已經存在的欄位名：Name_Clean, Maturity_Dt, Coupon_Clean
                    col_cfg = {
                        "Name_Clean": st.column_config.TextColumn("公司名稱", width="large"),
                        "Ticker_Search": st.column_config.LinkColumn("代號", display_text="🔍", width="small"),
                        "Maturity_Dt": st.column_config.DateColumn("到期日", format="YYYY-MM-DD", width="medium"),
                        "Bond_Price": st.column_config.ProgressColumn("價格強度", format="$%.2f", min_value=0, max_value=200, width="medium"),
                        "Coupon_Clean": st.column_config.NumberColumn("利率", format="%.2f%%", width="small")
                    }
                    
                    final_cols = ['Name_Clean', 'Ticker_Search', 'Maturity_Dt', 'Bond_Price', 'Coupon_Clean']

                    with tab1:
                        if not danger.empty:
                            st.dataframe(danger[final_cols], column_config=col_cfg, use_container_width=True, hide_index=True)
                        else: st.info("✅ 無高風險威脅。")

                    with tab2:
                        if not rocket.empty:
                            st.dataframe(rocket[final_cols], column_config=col_cfg, use_container_width=True, hide_index=True)
                        else: st.info("⚠️ 無高動能目標。")
                        
                    with tab3:
                        st.dataframe(df_all[final_cols], column_config=col_cfg, use_container_width=True, hide_index=True)
                else:
                    st.warning("⚠️ 檔案中未發現 2026-2027 到期目標。")
        except Exception as e:
            st.error(f"❌ 系統錯誤: {e}")
            if debug_mode: st.exception(e)
