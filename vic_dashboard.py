import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. 頁面基礎設定 ---
st.set_page_config(page_title="Charles 戰情室 V10.0", page_icon="⚡", layout="wide")

# ==========================================
# 核心功能：親切的說明模組
# ==========================================
def render_user_guide():
    with st.expander("📖 Charles 指揮官手冊 (V10.0 新功能：找代號)", expanded=True):
        st.markdown("""
        ### 歡迎來到 Charles 專屬可轉債戰情室！ 👋
        
        #### 🆕 V10.0 更新：美股代號去哪了？
        iShares 的原始檔案**不包含**美股代號 (Ticker)，這很讓人頭痛。
        為了解決這個問題，我在表格最後面增加了一個 **「🔍 找代號」** 的連結。
        * **怎麼用？** 看到感興趣的公司，點擊該欄位的放大鏡，系統會自動幫您 Google 該公司的代號。

        ---
        
        #### 1️⃣ 資料下載路徑 (路徑修正)
        1. **進入首頁：** [https://www.ishares.com/us](https://www.ishares.com/us) (請留在美國站)。
        2. **搜索：** 點右上角搜尋 **`ICVT`** -> 點擊 **"iShares Convertible Bond ETF"**。
        3. **下載：** 找到 **"Holdings"** 區塊 -> 點 **"Download"** -> 選 **"CSV"**。
        4. **上傳：** 拖進下方框框。

        ---
        
        #### 2️⃣ 參數與解讀
        * **💀 死亡名單 (紅色)：** 債券價格 < $95 (且低息)。暗示**還錢有困難**。
        * **🚀 火箭名單 (綠色)：** 債券價格 > $130。暗示股價大漲，**無償債壓力**。
        """)

# --- 2. 側邊欄：控制中心 ---
with st.sidebar:
    st.header("🎛️ Charles 戰術控制台")
    
    st.info("💡 iShares 原檔無代號，已新增「Google 搜尋連結」功能。")
    
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
            
            # 價格計算
            df_valid = df.dropna(subset=['Market_Clean', 'Par_Clean', 'Maturity_Dt']).copy()
            df_valid['Bond_Price'] = (df_valid['Market_Clean'] / df_valid['Par_Clean']) * 100
            
            # 產生搜尋連結 (解決沒有 Ticker 的問題)
            # 邏輯：Google Search "Company Name stock ticker"
            df_valid['Ticker_Search'] = "https://www.google.com/search?q=" + df_valid['Name'].str.replace(' ', '+') + "+stock+ticker"
            
            # 鎖定 2026-2027
            mask_date = (df_valid['Maturity_Dt'] >= datetime(2026, 1, 1)) & \
                        (df_valid['Maturity_Dt'] <= datetime(2027, 12, 31))
            df_time = df_valid[mask_date].copy()
            
            if len(df_time) > 0:
                st.success(f"✅ 分析完成！共鎖定 {len(df_time)} 檔標的。")
                
                # 篩選名單
                if ignore_coupon:
                    danger = df_time[df_time['Bond_Price'] < danger_price]
                else:
                    df_time['Coupon_Clean'] = df_time['Coupon (%)'].apply(clean_currency)
                    danger = df_time[(df_time['Bond_Price'] < danger_price) & (df_time['Coupon_Clean'] < 2.0)]
                
                rocket = df_time[df_time['Bond_Price'] > rocket_price]
                
                # 顯示設定
                column_cfg = {
                    "Name": st.column_config.TextColumn("公司名稱", width="medium"),
                    "Maturity": st.column_config.DateColumn("到期日", format="YYYY-MM-DD"),
                    "Bond_Price": st.column_config.NumberColumn("債券價格 ($)", format="%.2f"),
                    "Coupon (%)": st.column_config.NumberColumn("利率 (%)", format="%.2f%%"),
                    # 關鍵新功能：搜尋連結
                    "Ticker_Search": st.column_config.LinkColumn("美股代號", display_text="🔍 找代號"),
                }
                
                # 顯示結果
                st.markdown("---")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader(f"💀 死亡名單 ({len(danger)})")
                    if not danger.empty:
                        st.dataframe(
                            danger[['Name', 'Ticker_Search', 'Maturity', 'Bond_Price', 'Coupon (%)']],
                            column_config=column_cfg,
                            use_container_width=True
                        )
                    else:
                        st.info("無符合條件標的。")

                with col2:
                    st.subheader(f"🚀 火箭名單 ({len(rocket)})")
                    if not rocket.empty:
                        st.dataframe(
                            rocket[['Name', 'Ticker_Search', 'Maturity', 'Bond_Price', 'Coupon (%)']],
                            column_config=column_cfg,
                            use_container_width=True
                        )
                    else:
                        st.info("無符合條件標的。")
            else:
                st.warning("⚠️ 檔案中沒有發現 2026-2027 年到期的債券。")
                
        except Exception as e:
            st.error(f"❌ 運算發生錯誤: {e}")
