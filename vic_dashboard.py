import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 頁面設定 ---
st.set_page_config(page_title="VIC 戰情室 V6.0", page_icon="⚡", layout="wide")

# --- 側邊欄：戰術參數設定 ---
with st.sidebar:
    st.header("🎛️ 戰術參數設定 (Tactical Control)")
    
    st.markdown("### 💀 死亡名單設定")
    # 滑桿：調整死亡價格門檻 (預設 90)
    danger_price_limit = st.slider(
        "債券價格低於多少算危險？(Price Threshold)", 
        min_value=10.0, max_value=100.0, value=90.0, step=1.0
    )
    
    # 核取方塊：是否無視利率
    ignore_coupon = st.checkbox("無視票面利率 (只看價格)", value=False)
    
    if not ignore_coupon:
        # 滑桿：調整利率門檻 (預設 2.0%)
        danger_coupon_limit = st.slider(
            "票面利率低於多少算危險？(Coupon Threshold)", 
            min_value=0.0, max_value=5.0, value=2.0, step=0.1
        )
    else:
        danger_coupon_limit = 999.0 # 設一個超大值代表不啟用

    st.markdown("---")
    
    st.markdown("### 🚀 火箭名單設定")
    # 滑桿：調整火箭價格門檻 (預設 130)
    rocket_price_limit = st.slider(
        "債券價格高於多少算火箭？(Rocket Threshold)", 
        min_value=100.0, max_value=300.0, value=130.0, step=5.0
    )
    
    st.info("💡 提示：滑動參數後，右側表格會即時更新。")

# --- 主頁面 ---
st.title("⚡ VIC 可轉債狙擊戰情室 (V6.0 指揮官版)")
st.markdown(f"""
**目前戰術配置：**
* 💀 **死亡標準：** 價格 < ${danger_price_limit} {'(且 利率 < ' + str(danger_coupon_limit) + '%)' if not ignore_coupon else '(無視利率)'}
* 🚀 **火箭標準：** 價格 > ${rocket_price_limit}
""")

# --- 檔案上傳區 ---
uploaded_file = st.file_uploader("📂 請上傳 iShares 的 CSV 檔案", type=['csv'])

# --- 核心處理函數 (沿用 V5.0 的超強清洗邏輯) ---
def robust_load_data(file):
    bytes_data = file.getvalue()
    text_data = None
    encodings = ['utf-8', 'cp1252', 'latin1']
    
    for enc in encodings:
        try:
            text_data = bytes_data.decode(enc, errors='replace')
            break
        except Exception:
            continue
            
    if text_data is None: return None

    lines = text_data.splitlines()
    header_line_index = -1
    for i, line in enumerate(lines[:50]):
        if "Name" in line and "Sector" in line and "Market Value" in line:
            header_line_index = i
            break
            
    if header_line_index == -1: return None

    clean_csv_data = "\n".join(lines[header_line_index:])
    try:
        df = pd.read_csv(io.StringIO(clean_csv_data), quotechar='"')
        return df
    except: return None

# --- 主程式 ---
if uploaded_file is not None:
    df = robust_load_data(uploaded_file)
    
    if df is not None:
        try:
            df.columns = df.columns.str.strip()
            
            # 數據清洗
            cols_to_clean = ['Market Value', 'Par Value', 'Coupon (%)']
            for col in cols_to_clean:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(',', '').str.replace('"', '').str.replace('$', '')
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 日期與價格計算
            if 'Maturity' in df.columns:
                df['Maturity'] = pd.to_datetime(df['Maturity'], errors='coerce')
                df = df.dropna(subset=['Maturity']) 
                df['Bond_Price'] = (df['Market Value'] / df['Par Value']) * 100
                
                # 時間鎖定 2026-2027
                target_start = datetime(2026, 1, 1)
                target_end = datetime(2027, 12, 31)
                mask = (df['Maturity'] >= target_start) & (df['Maturity'] <= target_end)
                df_final = df[mask].copy()
                
                if len(df_final) > 0:
                    # -------------------------------------------------------
                    # 關鍵：使用 Sidebar 的變數來篩選
                    # -------------------------------------------------------
                    
                    # 死亡名單邏輯
                    if ignore_coupon:
                        danger_mask = (df_final['Bond_Price'] < danger_price_limit)
                    else:
                        danger_mask = (df_final['Bond_Price'] < danger_price_limit) & (df_final['Coupon (%)'] < danger_coupon_limit)
                        
                    danger = df_final[danger_mask].sort_values('Bond_Price') # 按價格由低到高排
                    
                    # 火箭名單邏輯
                    rocket = df_final[df_final['Bond_Price'] > rocket_price_limit].sort_values('Bond_Price', ascending=False)
                    
                    # --- 顯示結果 ---
                    
                    # 頂部儀表板
                    col_m1, col_m2, col_m3 = st.columns(3)
                    col_m1.metric("2026-27 到期總數", f"{len(df_final)} 檔")
                    col_m2.metric("💀 死亡名單數", f"{len(danger)} 檔", delta_color="inverse")
                    col_m3.metric("🚀 火箭名單數", f"{len(rocket)} 檔")
                    
                    st.markdown("---")

                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader(f"💀 死亡名單")
                        if not danger.empty:
                            st.dataframe(
                                danger[['Name', 'Maturity', 'Bond_Price', 'Coupon (%)']].style.format({
                                    'Maturity': '{:%Y-%m-%d}',
                                    'Bond_Price': '{:.1f}',
                                    'Coupon (%)': '{:.2f}%'
                                }).background_gradient(subset=['Bond_Price'], cmap='Reds_r'),
                                use_container_width=True
                            )
                        else:
                            st.success("在此標準下，無高風險標的。試著調高價格門檻？")

                    with col2:
                        st.subheader(f"🚀 火箭名單")
                        if not rocket.empty:
                            st.dataframe(
                                rocket[['Name', 'Maturity', 'Bond_Price', 'Coupon (%)']].style.format({
                                    'Maturity': '{:%Y-%m-%d}',
                                    'Bond_Price': '{:.1f}',
                                    'Coupon (%)': '{:.2f}%'
                                }).background_gradient(subset=['Bond_Price'], cmap='Greens'),
                                use_container_width=True
                            )
                        else:
                            st.info("在此標準下，無強勢標的。")
                else:
                    st.warning("檔案中沒有 2026-2027 到期的資料。")
            else:
                st.error("找不到 Maturity 欄位。")
                    
        except Exception as e:
            st.error(f"❌ 數據運算錯誤: {e}")
