import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 頁面設定 ---
st.set_page_config(page_title="VIC 戰情室 V5.0", page_icon="⚡", layout="wide")

st.title("⚡ VIC 可轉債狙擊戰情室 (最終版)")
st.markdown("此版本已針對您的原始檔格式進行修正：自動處理第 10 行檔頭、移除雙引號與逗號。")

# --- 檔案上傳區 ---
uploaded_file = st.file_uploader("📂 請上傳 CSV 檔案", type=['csv'])

# --- 核心處理函數 ---
def robust_load_data(file):
    # 1. 讀取原始 Bytes
    bytes_data = file.getvalue()
    
    # 2. 嘗試解碼 (使用 replace 忽略錯誤字元)
    text_data = None
    encodings = ['utf-8', 'cp1252', 'latin1']
    
    for enc in encodings:
        try:
            text_data = bytes_data.decode(enc, errors='replace')
            break
        except Exception:
            continue
            
    if text_data is None:
        st.error("❌ 嚴重錯誤：檔案無法解碼。")
        return None

    # 3. 逐行搜尋標題 (iShares 原始檔標題在第 10 行左右)
    lines = text_data.splitlines()
    header_line_index = -1
    
    for i, line in enumerate(lines[:50]):
        # 關鍵特徵：同一行必須包含 Name, Sector, Market Value
        if "Name" in line and "Sector" in line and "Market Value" in line:
            header_line_index = i
            break
            
    if header_line_index == -1:
        st.error("❌ 找不到標題列 (Name, Sector)。")
        return None

    # 4. 重組數據
    clean_csv_data = "\n".join(lines[header_line_index:])
    
    # 5. 轉成 DataFrame
    try:
        # 使用 pandas 的 quotechar='"' 來自動處理雙引號
        df = pd.read_csv(io.StringIO(clean_csv_data), quotechar='"')
        return df
    except Exception as e:
        st.error(f"❌ Pandas 解析失敗: {e}")
        return None

# --- 主程式 ---
if uploaded_file is not None:
    st.info("數據清洗中...")
    
    df = robust_load_data(uploaded_file)
    
    if df is not None:
        try:
            # 清理欄位名稱 (有些欄位可能有空白)
            df.columns = df.columns.str.strip()
            
            # ---------------------------------------------------------
            # 關鍵修正：針對您的檔案格式進行強制清洗
            # ---------------------------------------------------------
            # 您的檔案中，數值長這樣："124,729,560.37" (字串帶逗號)
            
            cols_to_clean = ['Market Value', 'Par Value', 'Coupon (%)']
            
            for col in cols_to_clean:
                if col in df.columns:
                    # 1. 轉成字串
                    df[col] = df[col].astype(str)
                    # 2. 移除逗號、雙引號、貨幣符號
                    df[col] = df[col].str.replace(',', '').str.replace('"', '').str.replace('$', '')
                    # 3. 強制轉成數字
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # ---------------------------------------------------------
            
            # 檢查必要欄位
            required = ['Name', 'Maturity', 'Market Value', 'Par Value', 'Coupon (%)']
            if not all(col in df.columns for col in required):
                st.error(f"❌ 缺少必要欄位，您的檔案欄位為: {list(df.columns)}")
            else:
                # 轉換日期
                df['Maturity'] = pd.to_datetime(df['Maturity'], errors='coerce')
                df = df.dropna(subset=['Maturity']) 
                
                # 計算價格
                df['Bond_Price'] = (df['Market Value'] / df['Par Value']) * 100
                
                # 鎖定 2026-2027
                target_start = datetime(2026, 1, 1)
                target_end = datetime(2027, 12, 31)
                mask = (df['Maturity'] >= target_start) & (df['Maturity'] <= target_end)
                df_final = df[mask].copy()
                
                if len(df_final) > 0:
                    # 分類
                    danger = df_final[(df_final['Bond_Price'] < 85) & (df_final['Coupon (%)'] < 1.0)].sort_values('Maturity')
                    rocket = df_final[df_final['Bond_Price'] > 130].sort_values('Bond_Price', ascending=False)
                    
                    st.success(f"✅ 解析成功！鎖定 {len(df_final)} 筆關鍵資料。")
                    
                    # 顯示
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.header(f"💀 死亡名單 ({len(danger)})")
                        st.caption("特徵：價格 < 85 + 利率 < 1% (還款壓力大)")
                        st.dataframe(
                            danger[['Name', 'Maturity', 'Bond_Price', 'Coupon (%)']].style.format({
                                'Maturity': '{:%Y-%m-%d}',
                                'Bond_Price': '{:.1f}',
                                'Coupon (%)': '{:.2f}%'
                            }), 
                            use_container_width=True
                        )

                    with col2:
                        st.header(f"🚀 火箭名單 ({len(rocket)})")
                        st.caption("特徵：價格 > 130 (轉股獲利)")
                        st.dataframe(
                            rocket[['Name', 'Maturity', 'Bond_Price', 'Coupon (%)']].style.format({
                                'Maturity': '{:%Y-%m-%d}',
                                'Bond_Price': '{:.1f}',
                                'Coupon (%)': '{:.2f}%'
                            }),
                            use_container_width=True
                        )
                else:
                    st.warning("⚠️ 檔案中沒有 2026-2027 到期的資料。")
                    
        except Exception as e:
            st.error(f"❌ 數據運算錯誤: {e}")