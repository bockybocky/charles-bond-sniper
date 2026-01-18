import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. 頁面基礎設定 ---
st.set_page_config(
    page_title="Charles 戰情室 V13.0", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🎨 核心美化模組 (Pro CSS)
# ==========================================
def inject_custom_css():
    st.markdown("""
        <style>
        /* 全域字體與背景優化 */
        .stApp {
            background-color: #0E1117;
            color: #FAFAFA;
        }
        
        /* 標題漸層特效 (冰藍白金) */
        h1 {
            background: linear-gradient(to right, #00c6ff, #0072ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700 !important;
            font-size: 2.5rem !important;
            margin-bottom: 0px;
        }
        
        /* 側邊欄美化 */
        [data-testid="stSidebar"] {
            background-color: #161B22;
            border-right: 1px solid #30363D;
        }
        
        /* 移除醜陋的橘色方塊樣式，改用自定義文字 */
        .sidebar-text {
            color: #8B949E;
            font-size: 0.9rem;
            margin-bottom: 20px;
        }
        
        /* 分頁標籤美化 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            height: 45px;
            background-color: #21262D;
            border-radius: 4px;
            color: #C9D1D9;
            font-size: 0.95rem;
            border: 1px solid #30363D;
        }
        .stTabs [aria-selected="true"] {
            background-color: #238636 !important; /* GitHub Green */
            color: white !important;
            border: none;
        }

        /* 調整 metrics 數值顏色 */
        div[data-testid="stMetricValue"] {
            font-size: 1.8rem;
            color: #58A6FF; /* Sky Blue */
        }
        
        /* 隱藏預設的表格索引 */
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
        #### 1️⃣ 數據源 (iShares US)
        * 請至 [iShares US](https://www.ishares.com/us) 搜尋 `ICVT` 下載 CSV。
        
        #### 2️⃣ 戰術看板解讀
        * **排序邏輯：** 所有名單皆依 **「到期日 (近 -> 遠)」** 排列。越上面的，時間壓力越大。
        * **💀 死亡名單：** 價格崩盤 (<$95) 的潛在違約者。
        * **🚀 火箭名單：** 價格飆漲 (>$130) 的強勢股。
        """)

# --- 2. 側邊欄：控制中心 ---
with st.sidebar:
    st.markdown("### 🎛️ 戰術控制台")
    # 使用自定義 CSS 類別取代 st.info
    st.markdown('<p class="sidebar-text">調整參數以過濾右側戰情名單。</p>', unsafe_allow_html=True)
    
    st.divider()
    
    # 參數設定
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
        if "Name" in line and "Market Value" in line:
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
st.caption("VIC System V13.0 // Authorized Access Only")

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
            df.columns = df.columns.str.strip()
            df['Market_Clean'] = df['Market Value'].apply(clean_currency)
            df['Par_Clean'] = df['Par Value'].apply(clean_currency)
            df['Maturity_Dt'] = pd.to_datetime(df['Maturity'], errors='coerce')
            
            df_valid = df.dropna(subset=['Market_Clean', 'Par_Clean', 'Maturity_Dt']).copy()
            df_valid['Bond_Price'] = (df_valid['Market_Clean'] / df_valid['Par_Clean']) * 100
            
            df_valid['Ticker_Search'] = "https://www.google.com/search?q=" + df_valid['Name'].str.replace(' ', '+') + "+stock+ticker"
            
            mask_date = (df_valid['Maturity_Dt'] >= datetime(2026, 1, 1)) & \
                        (df_valid['Maturity_Dt'] <= datetime(2027, 12, 31))
            df_time = df_valid[mask_date].copy()
            
            if len(df_time) > 0:
                # 篩選
                if ignore_coupon:
                    danger = df_time[df_time['Bond_Price'] < danger_price]
                else:
                    df_time['Coupon_Clean'] = df_time['Coupon (%)'].apply(clean_currency)
                    danger = df_time[(df_time['Bond_Price'] < danger_price) & (df_time['Coupon_Clean'] < 2.0)]
                
                rocket = df_time[df_time['Bond_Price'] > rocket_price]

                # ⚠️ 關鍵修正：排序邏輯 (Maturity Ascending)
                # 越近的日期排在越上面
                danger = danger.sort_values(by='Maturity_Dt', ascending=True)
                rocket = rocket.sort_values(by='Maturity_Dt', ascending=True)
                
                # --- KPI 儀表板 ---
                st.markdown("---")
                col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
                
                col_kpi1.metric("📊 掃描總數", f"{len(df_time)}", "2026-27 到期")
                col_kpi2.metric("💀 死亡鎖定", f"{len(danger)}", f"佔比 {len(danger)/len(df_time):.1%}", delta_color="inverse")
                col_kpi3.metric("🚀 火箭鎖定", f"{len(rocket)}", f"佔比 {len(rocket)/len(df_time):.1%}")
                st.markdown("---")

                # --- 戰術分頁 ---
                tab_death, tab_rocket, tab_all = st.tabs(["💀 死亡名單 (Short)", "🚀 火箭名單 (Long)", "📋 完整戰報 (All)"])

                column_cfg = {
                    "Name": st.column_config.TextColumn("公司名稱", width="large"),
                    "Ticker_Search": st.column_config.LinkColumn("代號", display_text="🔍", width="small"),
                    "Maturity": st.column_config.DateColumn("到期日", format="YYYY-MM-DD", width="medium"),
                    "Bond_Price": st.column_config.ProgressColumn(
                        "債券價格強度", 
                        format="$%.2f", 
                        min_value=0, 
                        max_value=200,
                        width="medium"
                    ),
                    "Coupon (%)": st.column_config.NumberColumn("利率", format="%.2f%%", width="small"),
                }
                
                show_cols = ['Name', 'Ticker_Search', 'Maturity', 'Bond_Price', 'Coupon (%)']

                with tab_death:
                    # st.caption(f"篩選條件：價格 < ${danger_price} | 排序：到期日 (近 -> 遠)")
                    if not danger.empty:
                        st.dataframe(
                            danger[show_cols],
                            column_config=column_cfg,
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("✅ 掃描結果：無高風險威脅。")

                with tab_rocket:
                    # st.caption(f"篩選條件：價格 > ${rocket_price} | 排序：到期日 (近 -> 遠)")
                    if not rocket.empty:
                        st.dataframe(
                            rocket[show_cols],
                            column_config=column_cfg,
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("⚠️ 掃描結果：無高動能目標。")
                        
                with tab_all:
                    st.dataframe(
                        df_time[show_cols].sort_values('Maturity_Dt', ascending=True),
                        column_config=column_cfg,
                        use_container_width=True,
                        hide_index=True
                    )
            else:
                st.warning("⚠️ 檔案中未發現 2026-2027 到期目標。")
        except Exception as e:
            st.error(f"❌ 系統錯誤: {e}")
