import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import math
from PIL import Image
from datetime import datetime

# 1. 系統資料預設值
INVENTORY_STANDARDS = {
    "波霸薯條": {"標準_完整包": 8, "標準_分裝袋": 2, "單位": "包"},
    "地瓜薯條": {"標準_完整包": 2, "標準_分裝袋": 2, "單位": "包"},
    "甜不辣": {"標準_完整包": 2, "標準_分裝袋": 2, "單位": "包"},
    "魷米花": {"標準_完整包": 4, "標準_分裝袋": 2, "單位": "包"},
    "洋蔥圈": {"標準_完整包": 8, "標準_分裝袋": 0, "單位": "包"},
    "銀絲卷": {"標準_完整包": 5, "標準_分裝袋": 0, "單位": "包"},
    "花枝丸": {"標準_完整包": 2, "標準_分裝袋": 0, "單位": "包"},
    "鱈魚條": {"標準_完整包": 4, "標準_分裝袋": 0, "單位": "包"},
    "山藥卷": {"標準_完整包": 1, "標準_分裝袋": 0, "單位": "包"},
    "芝麻芋香球": {"標準_完整包": 1, "標準_分裝袋": 0, "單位": "包"},
    "地瓜球": {"標準_完整包": 1, "標準_分裝袋": 0, "單位": "包"},
    "披薩球": {"標準_完整包": 1, "標準_分裝袋": 0, "單位": "包"},
    "小芋泥球": {"標準_完整包": 1, "標準_分裝袋": 0, "單位": "包"},
    "薯餅": {"標準_完整包": 1, "標準_分裝袋": 0, "單位": "包"},
    "玉米布丁酥": {"標準_完整包": 3, "標準_分裝袋": 0, "單位": "包"},
    "乳酪甜心酥": {"標準_完整包": 10, "標準_分裝袋": 0, "單位": "份"},
    "蔥仔餅": {"標準_完整包": 2, "標準_分裝袋": 0, "單位": "包"},
    "花雕雞香腸": {"標準_完整包": 2, "標準_分裝袋": 0, "單位": "包"},
    "蘋果派": {"標準_完整包": 10, "標準_分裝袋": 0, "單位": "份"}
}

def format_order_qty(qty, unit):
    if qty <= 0:
        return None
    
    qty = math.ceil(qty)
    
    if unit == "包" and qty >= 6:
        boxes = qty // 6
        bags = qty % 6
        if bags == 0:
            return f"{boxes}箱"
        else:
            return f"{boxes}箱{bags}包"
    else:
        return f"{qty}{unit}"

def parse_image_with_gemini(api_key, image):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    standard_names = list(INVENTORY_STANDARDS.keys())
    
    prompt = f"""
    你是一個餐廳庫存管理助手。請解析這張白板照片中的庫存數據。
    
    請提取以下三個欄位的數字：
    1. '臥式冰箱'
    2. '二門+四門'
    3. '分裝'
    
    如果欄位是空格或沒寫，請視為 0。
    
    關鍵要求：
    請將辨識出的品項名稱自動對齊到以下標準名稱列表中的 Key。
    例如：將 "pizza球" 轉為 "披薩球"，"Apple派" 轉為 "蘋果派"，"香腸" 轉為 "花雕雞香腸"。
    
    標準名稱列表：
    {standard_names}
    
    輸出格式：
    請僅輸出 JSON 格式，不要有任何其他文字說明。格式如下：
    {{
      "品項名稱": {{
        "臥式冰箱": 0,
        "二門+四門": 0,
        "分裝": 0
      }}
    }}
    """
    
    response = model.generate_content([prompt, image])
    try:
        # 清除可能包含的 markdown 標籤
        content = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(content)
    except Exception as e:
        st.error(f"解析 JSON 失敗: {e}")
        st.text(response.text)
        return {}

# UI 設置
st.set_page_config(page_title="餐廳叫貨輔助工具", layout="wide")
st.title("📦 餐廳每週叫貨輔助系統")

# API Key 配置
# 優先嘗試從 Streamlit Secrets 讀取 (適用於部署或本地 .streamlit/secrets.toml)
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    api_key = st.sidebar.text_input("請輸入 Gemini API Key", type="password")
    if not api_key:
        st.info("請在側邊欄輸入 Gemini API Key 或在 Secrets 中設定 GEMINI_API_KEY 以啟用 AI 辨識功能。")
else:
    st.sidebar.success("已從 Secrets 載入 API Key")

# 圖片上傳
uploaded_file = st.file_uploader("上傳白板庫存照片", type=["jpg", "jpeg", "png"])

# 初始化 Session State
if "df" not in st.session_state:
    df_base = pd.DataFrame.from_dict(INVENTORY_STANDARDS, orient='index').reset_index()
    df_base.columns = ['品項', '標準_完整包', '標準_分裝袋', '單位']
    df_base['臥式冰箱'] = 0.0
    df_base['二門+四門'] = 0.0
    df_base['分裝'] = 0.0
    st.session_state.df = df_base

# 執行 AI 辨識
if uploaded_file and api_key:
    if st.button("開始 AI 視覺辨識"):
        with st.spinner("AI 正在解析圖片..."):
            img = Image.open(uploaded_file)
            ai_results = parse_image_with_gemini(api_key, img)
            
            if ai_results:
                # 更新現有 DataFrame
                for item, values in ai_results.items():
                    if item in st.session_state.df['品項'].values:
                        idx = st.session_state.df[st.session_state.df['品項'] == item].index[0]
                        st.session_state.df.at[idx, '臥式冰箱'] = float(values.get('臥式冰箱', 0))
                        st.session_state.df.at[idx, '二門+四門'] = float(values.get('二門+四門', 0))
                        st.session_state.df.at[idx, '分裝'] = float(values.get('分裝', 0))
                st.success("辨識完成！請在下方表格確認與修正數據。")

st.subheader("庫存資料編輯")
edited_df = st.data_editor(
    st.session_state.df,
    column_config={
        "品項": st.column_config.TextColumn("品項", disabled=True),
        "標準_完整包": st.column_config.NumberColumn("標準_完整包"),
        "標準_分裝袋": st.column_config.NumberColumn("標準_分裝袋"),
        "單位": st.column_config.TextColumn("單位", disabled=True),
        "臥式冰箱": st.column_config.NumberColumn("臥式冰箱"),
        "二門+四門": st.column_config.NumberColumn("二門+四門"),
        "分裝": st.column_config.NumberColumn("分裝"),
    },
    hide_index=True,
    use_container_width=True
)

# 儲存編輯後的結果到 session_state
st.session_state.df = edited_df

# 計算叫貨量
if st.button("計算叫貨量"):
    df = st.session_state.df.copy()
    
    # 計算邏輯
    df['總現有庫存'] = df['臥式冰箱'] + df['二門+四門'] + df['分裝']
    df['總標準庫存'] = df['標準_完整包'] + df['標準_分裝袋']
    df['需叫貨數量'] = df['總標準庫存'] - df['總現有庫存']
    
    # 產出結果
    order_items = []
    for _, row in df.iterrows():
        qty_str = format_order_qty(row['需叫貨數量'], row['單位'])
        if qty_str:
            order_items.append(f"{row['品項']}：{qty_str}")
    
    if order_items:
        today = datetime.now().strftime("%-m/%-d")
        result_text = f"{today} 青雲店\n" + "\n".join(order_items)
        
        st.subheader("📋 叫貨清單產出")
        st.code(result_text, language="text")
        st.write("*(點擊右上角按鈕即可複製文字)*")
    else:
        st.write("目前庫存充足，不需要叫貨。")
