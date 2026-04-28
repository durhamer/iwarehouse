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
    try:
        genai.configure(api_key=api_key)
        # 更新為 2.0 版本，這是 2026 年的主流穩定版本
        # 改為 'gemini-2.5-flash'
        model_name = 'gemini-2.5-flash' 
        model = genai.GenerativeModel(model_name)
        
        standard_names = list(INVENTORY_STANDARDS.keys())
        
        prompt = f"""
        你是一個資深的餐廳庫存管理助手。請精準解析這張白板庫存照片。
        
        【任務細節】
        1. 按照白板上「由上而下」的品項順序進行解析。
        2. 讀取表格中每個品項對應的三個數據：
           - 臥式冰箱
           - 二門+四門
           - 分裝
        
        【規則】
        - **順序至關重要**：請務必按照照片中品項出現的先後順序排列 JSON 列表。
        - 若格子為空、有斜線或無法辨識，請填入 0。
        - 必須將辨識出的名稱「自動對齊」至下方的標準品項清單。
        - 修正常見的縮寫或錯字（如：pizza -> 披薩，香腸 -> 花雕雞香腸）。
        
        【標準品項清單】
        {standard_names}
        
        【輸出格式】
        僅回傳純 JSON 列表格式，不含 Markdown 標籤：
        [
          {{
            "品項": "品項名稱",
            "臥式冰箱": 0,
            "二門+四門": 0,
            "分裝": 0
          }}
        ]
        """
        
        # 2.0 版本的安全性與產生設定
        response = model.generate_content(
            [prompt, image],
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.1, # 降低隨機性，確保對齊精準
            }
        )
        
        if not response or not response.text:
            st.error("API 回傳內容為空。")
            return []
            
        # 清理回傳內容
        content = response.text.strip()
        if content.startswith("```"):
            content = content.replace('```json', '').replace('```', '').strip()
            
        return json.loads(content)
        
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            st.error(f"模型 {model_name} 尚未在您的區域開放或名稱不正確，建議嘗試 'gemini-2.5-flash'、'gemini-2.0-flash' 或 'gemini-1.5-flash'。")
        else:
            st.error(f"AI 辨識異常: {error_msg}")
        return []

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
                # 取得 AI 辨識出的品項名稱列表 (僅保留在標準清單中的)
                ai_item_names = []
                for res in ai_results:
                    name = res.get('品項')
                    if name in st.session_state.df['品項'].values and name not in ai_item_names:
                        ai_item_names.append(name)
                
                # 建立一個暫存的資料字典以便更新
                ai_data_map = {res['品項']: res for res in ai_results if res.get('品項') in st.session_state.df['品項'].values}
                
                # 重新排序：AI 辨識出的品項在前 (按照照片順序)，其餘在後
                all_items = st.session_state.df['品項'].tolist()
                remaining_items = [item for item in all_items if item not in ai_item_names]
                new_order = ai_item_names + remaining_items
                
                # 重建 DataFrame 順序並套用新數值
                new_df = st.session_state.df.set_index('品項').reindex(new_order).reset_index()
                
                for item, values in ai_data_map.items():
                    idx = new_df[new_df['品項'] == item].index[0]
                    new_df.at[idx, '臥式冰箱'] = float(values.get('臥式冰箱', 0))
                    new_df.at[idx, '二門+四門'] = float(values.get('二門+四門', 0))
                    new_df.at[idx, '分裝'] = float(values.get('分裝', 0))
                
                st.session_state.df = new_df
                st.success("辨識完成！已根據照片順序重新排列品項，請在下方表格確認。")

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
