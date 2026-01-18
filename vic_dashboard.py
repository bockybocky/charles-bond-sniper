import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. 頁面基礎設定 ---
st.set_page_config(page_title="VIC 戰情室 V8.0", page_icon="⚡", layout="wide")
st.title("⚡ Charles 可轉債戰情室 (V8.0 輕量版)")

# --- 2. 側邊欄：控制中心 ---
with st.sidebar:
    st.header("🎛️ 戰術控制台")
    
    # 除錯模式開關
    debug_mode = st.checkbox("🐞 開啟除錯模式", value=True)
    
    st.markdown("---")
    # 參數設定
    danger_price = st.number_input("死亡價格門檻 (<)", value=95.0, step=1.0)
    rocket_price = st.number_input("火箭價格門檻 (>)", value=130.0, step=5.0)
    ignore_coupon = st.checkbox("無視票面利率", value=True)

# --- 3. 核心清洗引擎 ---
def clean_currency(x):
    if isinstance(x, (int, float)):
        return x
    if pd.isna(x) or x == '-':
        return None
    # 移除所有可能的干擾字元
    clean_str = str(x).replace('$', '').replace(',', '').replace('"', '').strip()
    try:
        return float(clean_str)
    except:
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
uploaded_file = st.file_uploader("📂 請上傳 iShares CSV 檔案", type=['csv'])

if uploaded_file is not None:
    df, error_msg = robust_parser(uploaded_file)
    
    if error_msg:
        st.error(f"❌ 檔案讀取失敗: {error_msg}")
    else:
        # 除錯預覽
        if debug_mode:
            with st.expander("🐞 原始資料預覽", expanded=False):
                st.dataframe(df.head())

        try:
            df.columns = df.columns.str.strip()
            
            # 清洗與計算
            df['Market_Clean'] = df['Market Value'].apply(clean_currency)
            df['Par_Clean'] = df['Par Value'].apply(clean_currency)
            df['Maturity_Dt'] = pd.to_datetime(df['Maturity'], errors='coerce')
            
            df_valid = df.dropna(subset=['Market_Clean', 'Par_Clean', 'Maturity_Dt']).copy()
            df_valid['Bond_Price'] = (df_valid['Market_Clean'] / df_valid['Par_Clean']) * 100
            
            # 篩選 2026-2027
            mask_date = (df_valid['Maturity_Dt'] >= datetime(2026, 1, 1)) & \
                        (df_valid['Maturity_Dt'] <= datetime(2027, 12, 31))
            df_time = df_valid[mask_date].copy()
            
            st.success(f"✅ 分析完成！鎖定 {len(df_time)} 筆關鍵資料")

            if len(df_time) > 0:
                # 篩選名單
                if ignore_coupon:
                    danger = df_time[df_time['Bond_Price'] < danger_price]
                else:
                    df_time['Coupon_Clean'] = df_time['Coupon (%)'].apply(clean_currency)
                    danger = df_time[(df_time['Bond_Price'] < danger_price) & (df_time['Coupon_Clean'] < 2.0)]
                
                rocket = df_time[df_time['Bond_Price'] > rocket_price]
                
                # --- 顯示結果 (使用 Streamlit 原生 Column Config，不依賴 matplotlib) ---
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader(f"💀 死亡名單 ({len(danger)})")
                    if not danger.empty:
                        st.dataframe(
                            danger[['Name', 'Maturity', 'Bond_Price', 'Coupon (%)']],
                            column_config={
                                "Maturity": st.column_config.DateColumn("到期日", format="YYYY-MM-DD"),
                                "Bond_Price": st.column_config.NumberColumn("債券價格", format="%.2f"),
                                "Coupon (%)": st.column_config.NumberColumn("利率", format="%.2f%%"),
                            },
                            use_container_width=True
                        )
                    else:
                        st.info("無符合條件標的。")

                with col2:
                    st.subheader(f"🚀 火箭名單 ({len(rocket)})")
                    if not rocket.empty:
                        st.dataframe(
                            rocket[['Name', 'Maturity', 'Bond_Price', 'Coupon (%)']],
                            column_config={
                                "Maturity": st.column_config.DateColumn("到期日", format="YYYY-MM-DD"),
                                "Bond_Price": st.column_config.NumberColumn("債券價格", format="%.2f"),
                                "Coupon (%)": st.column_config.NumberColumn("利率", format="%.2f%%"),
                            },
                            use_container_width=True
                        )
                    else:
                        st.info("無符合條件標的。")
            else:
                st.warning("⚠️ 此時間區間內無資料。")
                
        except Exception as e:
            st.error(f"❌ 運算錯誤: {e}")

