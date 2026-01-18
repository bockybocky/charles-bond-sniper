import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. 頁面基礎設定 (開啟寬螢幕模式) ---
st.set_page_config(page_title="Charles 戰情室 V11.0", page_icon="⚡", layout="wide")

# ==========================================
# 核心功能：親切的說明模組
# ==========================================
def render_user_guide():
    with st.expander("📖 Charles 指揮官手冊 (點我展開/收合)", expanded=False):
        st.markdown("""
        ### 歡迎來到 Charles 專屬可轉債戰情室！ 👋
        
        #### 1️⃣ 資料下載 (iShares 官網)
        1. **進入首頁：** [https://www.ishares.com/us](https://www.ishares.com/us) (請留在美國站)。
        2. **搜索：** 點右上角搜尋 **`ICVT`** -> 點擊 **"iShares Convertible Bond ETF"**。
        3. **下載：** 找到 **"Holdings"** 區塊 -> 點 **"Download"** -> 選 **"CSV"**。
        4. **上傳：** 拖進下方框框。

        #### 2️⃣ 如何看懂這張表？
        此版本已採用 **「全寬度分頁」** 設計，請點擊下方的 **「💀 死亡名單」** 或 **「🚀 火箭名單」** 標籤切換查看。
        
        * **🔍 找代號：** 點擊表格中的「🔍 找代號」連結，系統會自動幫您 Google 美股代號。
        """)

# --- 2. 側邊欄：控制中心 ---
with st.sidebar:
    st.header("🎛️ Charles 戰術控制台")
    
    st.success("✅ 目前模式：寬螢幕優化 (Tab View)")
    
    # 參數設定
    st.subheader("💀 死亡名單標準")
    danger_price = st.slider("債券價格低於多少算危險？", 50.0, 100.0, 95.0, 1.0)
    ignore_coupon = st.checkbox("無視票面利率 (只看價格)", value=True)
    
    st.subheader("🚀 火箭名單標準")
    rocket_price = st.slider("債券價格高於多少算火箭？", 100.0, 200.0, 130.0, 5.0)

    st.markdown("---")
    debug_mode = st.checkbox("🐞 開啟除錯模式", value=False)

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
    except Exception as e:
        return None, str(e)

# --- 4. 主程式邏輯 ---
st.title("⚡ Charles 可轉債狙擊戰情室")

render_user_guide()

st.markdown("### 📂 上傳戰略數據")
uploaded_file = st.file_uploader("請上傳 CSV 檔", type=['csv'])

if uploaded_file is not None:
    df, error_msg = robust_parser(uploaded_file)
    
    if error_msg:
        st.error(f"❌ 檔案讀取失敗: {error_msg}")
    else:
        if debug_mode:
            st.warning("🐞 除錯模式：原始資料預覽")
            st.dataframe(df.head())

        try:
            df.columns = df.columns.str.strip()
            
            # 清洗與計算
            df['Market_Clean'] = df['Market Value'].apply(clean_currency)
            df['Par_Clean'] = df['Par Value'].apply(clean_currency)
            df['Maturity_Dt'] = pd.to_datetime(df['Maturity'], errors='coerce')
            
            df_valid = df.dropna(subset=['Market_Clean', 'Par_Clean', 'Maturity_Dt']).copy()
            df_valid['Bond_Price'] = (df_valid['Market_Clean'] / df_valid['Par_Clean']) * 100
            
            # 產生搜尋連結
            df_valid['Ticker_Search'] = "https://www.google.com/search?q=" + df_valid['Name'].str.replace(' ', '+') + "+stock+ticker"
            
            # 鎖定 2026-2027
            mask_date = (df_valid['Maturity_Dt'] >= datetime(2026, 1, 1)) & \
                        (df_valid['Maturity_Dt'] <= datetime(2027, 12, 31))
            df_time = df_valid[mask_date].copy()
            
            if len(df_time) > 0:
                # 篩選名單
                if ignore_coupon:
                    danger = df_time[df_time['Bond_Price'] < danger_price].sort_values('Bond_Price')
                else:
                    df_time['Coupon_Clean'] = df_time['Coupon (%)'].apply(clean_currency)
                    danger = df_time[(df_time['Bond_Price'] < danger_price) & (df_time['Coupon_Clean'] < 2.0)].sort_values('Bond_Price')
                
                rocket = df_time[df_time['Bond_Price'] > rocket_price].sort_values('Bond_Price', ascending=False)
                
                # --- 新功能：戰情儀表板 (Metrics) ---
                st.markdown("---")
                m1, m2, m3 = st.columns(3)
                m1.metric("📊 2026-27 到期總數", f"{len(df_time)} 檔")
                m2.metric("💀 死亡名單 (潛在空單)", f"{len(danger)} 檔", delta=f"佔比 {len(danger)/len(df_time):.1%}", delta_color="inverse")
                m3.metric("🚀 火箭名單 (多頭確認)", f"{len(rocket)} 檔", delta=f"佔比 {len(rocket)/len(df_time):.1%}")
                st.markdown("---")

                # --- 新功能：全寬分頁切換 (Tabs) ---
                tab_death, tab_rocket, tab_all = st.tabs(["💀 死亡名單 (High Risk)", "🚀 火箭名單 (High Reward)", "📋 完整清單"])
                
                # 設定欄位顯示格式
                column_cfg = {
                    "Name": st.column_config.TextColumn("公司名稱", width="large"), # 加寬名稱欄
                    "Ticker_Search": st.column_config.LinkColumn("代號搜尋", display_text="🔍 找代號", width="small"),
                    "Maturity": st.column_config.DateColumn("到期日", format="YYYY-MM-DD", width="small"),
                    "Bond_Price": st.column_config.NumberColumn("債券價格 ($)", format="%.2f", width="small"),
                    "Coupon (%)": st.column_config.NumberColumn("利率 (%)", format="%.2f%%", width="small"),
                }
                
                # 顯示欄位
                show_cols = ['Name', 'Ticker_Search', 'Maturity', 'Bond_Price', 'Coupon (%)']

                with tab_death:
                    if not danger.empty:
                        st.dataframe(
                            danger[show_cols],
                            column_config=column_cfg,
                            use_container_width=True, # 關鍵：使用全寬度
                            hide_index=True
                        )
                    else:
                        st.info("✅ 目前無高風險標的。")

                with tab_rocket:
                    if not rocket.empty:
                        st.dataframe(
                            rocket[show_cols],
                            column_config=column_cfg,
                            use_container_width=True, # 關鍵：使用全寬度
                            hide_index=True
                        )
                    else:
                        st.info("⚠️ 目前無飆漲標的。")
                        
                with tab_all:
                    st.dataframe(
                        df_time[show_cols].sort_values('Maturity'),
                        column_config=column_cfg,
                        use_container_width=True,
                        hide_index=True
                    )

            else:
                st.warning("⚠️ 檔案中沒有發現 2026-2027 年到期的債券。")
                
        except Exception as e:
            st.error(f"❌ 運算發生錯誤: {e}")
