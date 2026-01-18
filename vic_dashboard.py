import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. 頁面基礎設定 ---
st.set_page_config(page_title="Charles 戰情室 V9.1", page_icon="⚡", layout="wide")

# ==========================================
# 核心功能：親切的說明模組 (已修正導航路徑)
# ==========================================
def render_user_guide():
    with st.expander("📖 Charles 指揮官手冊 (第一次使用請點我展開)", expanded=True):
        st.markdown("""
        ### 歡迎來到 Charles 專屬可轉債戰情室！ 👋
        
        #### 1️⃣ 第一步：如何取得正確的資料？ (重要！)
        由於 iShares 官網會阻擋直接連結，請依照以下戰術路徑操作：
        
        1. **進入首頁：** 點擊前往 [https://www.ishares.com/us](https://www.ishares.com/us) (請確保留在 **US 美國站**，不要切換到台灣站)。
        2. **執行搜索：** 點擊右上角的 **🔍 (搜尋放大鏡)**。
        3. **鎖定目標：** 輸入代號 **`ICVT`**，點擊搜尋結果中的 **"iShares Convertible Bond ETF"**。
        4. **下載情資：** * 進入頁面後，向下滑動找到 **"Holdings"** (持倉) 區塊。
            * 點擊表格右上角的 **"Download"** (下載)。
            * 選擇 **"CSV"** 格式。
        5. **上傳：** 將下載好的檔案拖進下方的上傳區。

        ---

        #### 2️⃣ 第二步：參數設定怎麼選？ (左側控制台)
        
        **關於「💀 死亡名單」的設定：**
        
        * **🔘 勾選「無視票面利率 (只看價格)」 (建議勾選)**
            * **戰術意義：** 只要債券價格崩盤 (<$95) 就視為危險，不管它利息給多少。這樣能抓到像 **Fisker (FSR)** 這種高息但快違約的地雷。
            
        * **⬜ 不勾選 (進階篩選)**
            * **戰術意義：** 只抓「低息 ($0-2%) 且價格崩盤」的殭屍公司。
        
        ---
        
        #### 3️⃣ 第三步：如何解讀結果？
        * **💀 死亡名單 (紅色)：** 債券價格 < $95 (或您設定的值)。代表市場認為這家公司**還錢有困難**。
        * **🚀 火箭名單 (綠色)：** 債券價格 > $130。代表股價大漲，債務將轉為股票，公司**無償債壓力**。
        """)

# --- 2. 側邊欄：控制中心 ---
with st.sidebar:
    st.header("🎛️ Charles 戰術控制台")
    
    st.info("💡 請先閱讀右方的「新手手冊」")
    
    # 參數設定
    st.subheader("💀 死亡名單標準")
    danger_price = st.slider("債券價格低於多少算危險？", 50.0, 100.0, 95.0, 1.0)
    ignore_coupon = st.checkbox("無視票面利率 (只看價格)", value=True, help="勾選後，只要價格低於設定值就會顯示。")
    
    st.subheader("🚀 火箭名單標準")
    rocket_price = st.slider("債券價格高於多少算火箭？", 100.0, 200.0, 130.0, 5.0)

    st.markdown("---")
    debug_mode = st.checkbox("🐞 開啟除錯模式 (如果沒反應請勾此)", value=False)

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
    # 嘗試多種編碼
    for enc in ['utf-8', 'cp1252', 'latin1']:
        try:
            text_data = bytes_data.decode(enc, errors='ignore')
            break
        except: continue
            
    if not text_data: return None, "無法解碼檔案，請確認格式。"

    lines = text_data.splitlines()
    header_idx = -1
    # 智慧搜尋標題列
    for i, line in enumerate(lines[:50]):
        if "Name" in line and "Market Value" in line:
            header_idx = i
            break
            
    if header_idx == -1: return None, "找不到標題列 (需包含 Name 和 Market Value)"

    try:
        clean_content = "\n".join(lines[header_idx:])
        df = pd.read_csv(io.StringIO(clean_content), quotechar='"')
        return df, None
    except Exception as e:
        return None, str(e)

# --- 4. 主程式邏輯 ---
st.title("⚡ Charles 可轉債狙擊戰情室")

# 呼叫新手引導
render_user_guide()

st.markdown("### 📂 上傳戰略數據")
uploaded_file = st.file_uploader("請將 iShares 下載的 CSV 檔拖曳到這裡", type=['csv'])

if uploaded_file is not None:
    df, error_msg = robust_parser(uploaded_file)
    
    if error_msg:
        st.error(f"❌ 檔案讀取失敗: {error_msg}")
    else:
        if debug_mode:
            st.warning("🐞 除錯模式已開啟：顯示原始資料前 5 筆")
            st.dataframe(df.head())

        try:
            # 標準化欄位名稱
            df.columns = df.columns.str.strip()
            
            # 數據清洗
            df['Market_Clean'] = df['Market Value'].apply(clean_currency)
            df['Par_Clean'] = df['Par Value'].apply(clean_currency)
            df['Maturity_Dt'] = pd.to_datetime(df['Maturity'], errors='coerce')
            
            # 計算價格
            df_valid = df.dropna(subset=['Market_Clean', 'Par_Clean', 'Maturity_Dt']).copy()
            df_valid['Bond_Price'] = (df_valid['Market_Clean'] / df_valid['Par_Clean']) * 100
            
            # 鎖定 2026-2027
            mask_date = (df_valid['Maturity_Dt'] >= datetime(2026, 1, 1)) & \
                        (df_valid['Maturity_Dt'] <= datetime(2027, 12, 31))
            df_time = df_valid[mask_date].copy()
            
            if len(df_time) > 0:
                st.success(f"✅ 分析完成！在 2026-2027 年到期的債券中，共鎖定 {len(df_time)} 檔標的。")
                
                # 篩選名單
                if ignore_coupon:
                    danger = df_time[df_time['Bond_Price'] < danger_price]
                else:
                    df_time['Coupon_Clean'] = df_time['Coupon (%)'].apply(clean_currency)
                    danger = df_time[(df_time['Bond_Price'] < danger_price) & (df_time['Coupon_Clean'] < 2.0)]
                
                rocket = df_time[df_time['Bond_Price'] > rocket_price]
                
                # 顯示結果
                st.markdown("---")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader(f"💀 死亡名單 ({len(danger)})")
                    st.markdown(f"**篩選標準：** 價格 < ${danger_price}")
                    if not danger.empty:
                        st.dataframe(
                            danger[['Name', 'Maturity', 'Bond_Price', 'Coupon (%)']],
                            column_config={
                                "Maturity": st.column_config.DateColumn("到期日", format="YYYY-MM-DD"),
                                "Bond_Price": st.column_config.NumberColumn("債券價格 ($)", format="%.2f"),
                                "Coupon (%)": st.column_config.NumberColumn("利率 (%)", format="%.2f%%"),
                            },
                            use_container_width=True
                        )
                    else:
                        st.info("好消息！目前沒有發現符合此標準的高風險債券。")

                with col2:
                    st.subheader(f"🚀 火箭名單 ({len(rocket)})")
                    st.markdown(f"**篩選標準：** 價格 > ${rocket_price}")
                    if not rocket.empty:
                        st.dataframe(
                            rocket[['Name', 'Maturity', 'Bond_Price', 'Coupon (%)']],
                            column_config={
                                "Maturity": st.column_config.DateColumn("到期日", format="YYYY-MM-DD"),
                                "Bond_Price": st.column_config.NumberColumn("債券價格 ($)", format="%.2f"),
                                "Coupon (%)": st.column_config.NumberColumn("利率 (%)", format="%.2f%%"),
                            },
                            use_container_width=True
                        )
                    else:
                        st.info("目前沒有發現符合此標準的飆漲債券。")
            else:
                st.warning("⚠️ 檔案中沒有發現 2026-2027 年到期的債券，請確認您下載的是 ICVT 持倉檔。")
                
        except Exception as e:
            st.error(f"❌ 運算發生錯誤: {e}")
            if debug_mode: st.exception(e)
