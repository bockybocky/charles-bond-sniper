import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. 頁面基礎設定 ---
st.set_page_config(page_title="VIC 戰情室 V7.0", page_icon="⚡", layout="wide")
st.title("⚡ VIC 可轉債戰情室 (V7.0 除錯大師)")

# --- 2. 側邊欄：控制中心 ---
with st.sidebar:
    st.header("🎛️ 戰術控制台")
    st.markdown("如果右邊跑不出來，請調整這裡。")
    
    # 除錯模式開關
    debug_mode = st.checkbox("🐞 開啟除錯模式 (顯示原始資料)", value=True)
    
    st.markdown("---")
    # 參數設定
    danger_price = st.number_input("死亡價格門檻 (<)", value=95.0, step=1.0)
    rocket_price = st.number_input("火箭價格門檻 (>)", value=130.0, step=5.0)
    ignore_coupon = st.checkbox("無視票面利率", value=True)

# --- 3. 核心清洗引擎 (不依賴 Pandas 自動判斷) ---
def clean_currency(x):
    """ 強力清洗函數：把 '$1,234.56' 變成 1234.56 """
    if isinstance(x, (int, float)):
        return x
    if pd.isna(x) or x == '-':
        return None
    # 轉成字串 -> 移除 $ , " -> 轉數字
    clean_str = str(x).replace('$', '').replace(',', '').replace('"', '').strip()
    try:
        return float(clean_str)
    except:
        return None

def robust_parser(file):
    # 讀取檔案內容
    bytes_data = file.getvalue()
    
    # 嘗試不同編碼
    text_data = None
    for enc in ['utf-8', 'cp1252', 'latin1']:
        try:
            text_data = bytes_data.decode(enc, errors='ignore') # ignore 是最暴力的解法
            break
        except: continue
            
    if not text_data: return None, "無法解碼檔案"

    # 手動找標題列
    lines = text_data.splitlines()
    header_idx = -1
    for i, line in enumerate(lines[:50]):
        # 只要同一行有 Name 和 Market Value 就算抓到了
        if "Name" in line and "Market Value" in line:
            header_idx = i
            break
            
    if header_idx == -1: return None, "找不到標題列 (Name, Market Value)"

    # 讀取資料
    try:
        clean_content = "\n".join(lines[header_idx:])
        # 使用 quotechar='"' 處理那些討厭的雙引號
        df = pd.read_csv(io.StringIO(clean_content), quotechar='"')
        return df, None
    except Exception as e:
        return None, str(e)

# --- 4. 主程式邏輯 ---
uploaded_file = st.file_uploader("📂 請上傳 iShares CSV 檔案", type=['csv'])

if uploaded_file is not None:
    # 讀取資料
    df, error_msg = robust_parser(uploaded_file)
    
    if error_msg:
        st.error(f"❌ 檔案讀取失敗: {error_msg}")
    else:
        # --- 數據 X光機 (除錯用) ---
        if debug_mode:
            with st.expander("🐞 點此查看：原始資料預覽 (Raw Data)", expanded=True):
                st.write("程式讀到的前 5 筆資料 (請檢查 Market Value 是否有數字)：")
                st.dataframe(df.head())

        # --- 開始清洗 ---
        try:
            # 清洗欄位名稱 (移除前後空白)
            df.columns = df.columns.str.strip()
            
            # 檢查關鍵欄位
            required_cols = ['Name', 'Market Value', 'Par Value', 'Maturity']
            missing = [c for c in required_cols if c not in df.columns]
            
            if missing:
                st.error(f"❌ 缺少欄位: {missing}")
            else:
                # 1. 數值清洗 (最關鍵的一步)
                df['Market_Clean'] = df['Market Value'].apply(clean_currency)
                df['Par_Clean'] = df['Par Value'].apply(clean_currency)
                
                # 2. 日期清洗
                df['Maturity_Dt'] = pd.to_datetime(df['Maturity'], errors='coerce')
                
                # 3. 過濾掉無效資料
                df_valid = df.dropna(subset=['Market_Clean', 'Par_Clean', 'Maturity_Dt']).copy()
                
                # 4. 計算價格
                df_valid['Bond_Price'] = (df_valid['Market_Clean'] / df_valid['Par_Clean']) * 100
                
                # 5. 顯示清洗結果統計
                st.success(f"✅ 成功清洗 {len(df_valid)} 筆資料 (原始 {len(df)} 筆)")
                
                # --- 篩選邏輯 ---
                # 鎖定 2026-2027
                mask_date = (df_valid['Maturity_Dt'] >= datetime(2026, 1, 1)) & \
                            (df_valid['Maturity_Dt'] <= datetime(2027, 12, 31))
                df_time = df_valid[mask_date].copy()
                
                if len(df_time) == 0:
                    st.warning("⚠️ 在 2026-2027 區間內找不到任何債券。")
                else:
                    # 分類
                    # 死亡名單
                    if ignore_coupon:
                        danger = df_time[df_time['Bond_Price'] < danger_price]
                    else:
                        # 確保 Coupon 也是數字
                        df_time['Coupon_Clean'] = df_time['Coupon (%)'].apply(clean_currency)
                        danger = df_time[(df_time['Bond_Price'] < danger_price) & (df_time['Coupon_Clean'] < 2.0)]
                    
                    # 火箭名單
                    rocket = df_time[df_time['Bond_Price'] > rocket_price]
                    
                    # --- 最終展示 ---
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader(f"💀 死亡名單 ({len(danger)})")
                        if not danger.empty:
                            st.dataframe(
                                danger[['Name', 'Maturity', 'Bond_Price', 'Coupon (%)']].style.format({
                                    'Bond_Price': '{:.2f}',
                                    'Maturity': '{:%Y-%m-%d}'
                                }).background_gradient(subset=['Bond_Price'], cmap='Reds_r'),
                                use_container_width=True
                            )
                        else:
                            st.info("無符合條件標的。")

                    with col2:
                        st.subheader(f"🚀 火箭名單 ({len(rocket)})")
                        if not rocket.empty:
                            st.dataframe(
                                rocket[['Name', 'Maturity', 'Bond_Price', 'Coupon (%)']].style.format({
                                    'Bond_Price': '{:.2f}',
                                    'Maturity': '{:%Y-%m-%d}'
                                }).background_gradient(subset=['Bond_Price'], cmap='Greens'),
                                use_container_width=True
                            )
                        else:
                            st.info("無符合條件標的。")
                            
        except Exception as e:
            st.error(f"❌ 運算過程發生錯誤: {e}")
            st.write("錯誤詳情:", e)
