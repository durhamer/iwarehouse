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

def load_mappings():
    try:
        with open('mapping_learning.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_mapping(raw_text, corrected_name):
    mappings = load_mappings()
    mappings[raw_text] = corrected_name
    with open('mapping_learning.json', 'w', encoding='utf-8') as f:
        json.dump(mappings, f, ensure_ascii=False, indent=2)

def parse_image_with_gemini(api_key, image):
    try:
        genai.configure(api_key=api_key)
        model_name = 'gemini-2.5-flash' 
        model = genai.GenerativeModel(model_name)
        
        standard_names = list(INVENTORY_STANDARDS.keys())
        learned_mappings = load_mappings()
        
        mapping_hint = ""
        if learned_mappings:
            mapping_hint = "【過往修正學習（優先參考）】\n" + "\n".join([f"- 白板寫「{k}」時，請對齊為「{v}」" for k, v in learned_mappings.items()])

        prompt = f"""
        你是一個資深的餐廳庫存管理助手。請精準解析這張白板庫存照片。
        
        {mapping_hint}

        【任務細節】
        1. 按照白板上「由上而下」的品項順序進行解析。
        2. 讀取表格中每個品項對應的三個數據：臥式冰箱、二門+四門、分裝。
        
        【規則】
        - **順序至關重要**：請務必按照照片中品項出現的先後順序排列。
        - **原始文字**：請紀錄你在白板上實際看到的文字（包含錯字或簡寫）。
        - **自動對齊**：將辨識出的名稱對齊至下方的標準品項清單。
        - 若無法辨識數值，請填入 0。
        
        【標準品項清單】
        {standard_names}
        
        【輸出格式】
        僅回傳純 JSON 列表格式：
        [
          {{
            "原始文字": "白板上的字",
            "品項": "標準清單中的名稱",
            "臥式冰箱": 0,
            "二門+四門": 0,
            "分裝": 0
          }}
        ]
        """
        
        response = model.generate_content(
            [prompt, image],
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.1,
            }
        )
        
        if not response or not response.text:
            return []
            
        content = response.text.strip()
        if content.startswith("```"):
            content = content.replace('```json', '').replace('```', '').strip()
            
        return json.loads(content)
        
    except Exception as e:
        st.error(f"AI 辨識異常: {str(e)}")
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
    df_base['原始文字'] = ""
    st.session_state.df = df_base

# 執行 AI 辨識
if uploaded_file and api_key:
    if st.button("開始 AI 視覺辨識"):
        with st.spinner("AI 正在解析圖片..."):
            img = Image.open(uploaded_file)
            ai_results = parse_image_with_gemini(api_key, img)
            
            if ai_results:
                # 取得 AI 辨識出的品項名稱列表
                ai_item_names = [res['品項'] for res in ai_results if res.get('品項') in INVENTORY_STANDARDS]
                
                # 重新排序
                all_items = list(INVENTORY_STANDARDS.keys())
                remaining_items = [item for item in all_items if item not in ai_item_names]
                new_order = ai_item_names + remaining_items
                
                # 重建 DataFrame
                new_df = pd.DataFrame.from_dict(INVENTORY_STANDARDS, orient='index').reset_index()
                new_df.columns = ['品項', '標準_完整包', '標準_分裝袋', '單位']
                new_df['臥式冰箱'] = 0.0
                new_df['二門+四門'] = 0.0
                new_df['分裝'] = 0.0
                new_df['原始文字'] = ""
                
                new_df = new_df.set_index('品項').reindex(new_order).reset_index()
                
                for res in ai_results:
                    name = res.get('品項')
                    if name in INVENTORY_STANDARDS:
                        idx = new_df[new_df['品項'] == name].index[0]
                        new_df.at[idx, '臥式冰箱'] = float(res.get('臥式冰箱', 0))
                        new_df.at[idx, '二門+四門'] = float(res.get('二門+四門', 0))
                        new_df.at[idx, '分裝'] = float(res.get('分裝', 0))
                        new_df.at[idx, '原始文字'] = res.get('原始文字', "")
                
                st.session_state.df = new_df
                st.success("辨識完成！已根據照片順序重新排列。若品項有誤，可直接在「品項」欄位修正。")

st.subheader("庫存資料編輯")
standard_options = list(INVENTORY_STANDARDS.keys())

edited_df = st.data_editor(
    st.session_state.df,
    column_config={
        "品項": st.column_config.SelectboxColumn("品項 (可修正)", options=standard_options),
        "標準_完整包": st.column_config.NumberColumn("標準_完整包", disabled=True),
        "標準_分裝袋": st.column_config.NumberColumn("標準_分裝袋", disabled=True),
        "單位": st.column_config.TextColumn("單位", disabled=True),
        "臥式冰箱": st.column_config.NumberColumn("臥式冰箱"),
        "二門+四門": st.column_config.NumberColumn("二門+四門"),
        "分裝": st.column_config.NumberColumn("分裝"),
        "原始文字": st.column_config.TextColumn("白板原始字跡", disabled=True),
    },
    hide_index=True,
    use_container_width=True
)

# 當品項變更時，更新對應的標準值
if not edited_df.equals(st.session_state.df):
    for i, row in edited_df.iterrows():
        item_name = row['品項']
        if item_name in INVENTORY_STANDARDS:
            edited_df.at[i, '標準_完整包'] = INVENTORY_STANDARDS[item_name]['標準_完整包']
            edited_df.at[i, '標準_分裝袋'] = INVENTORY_STANDARDS[item_name]['標準_分裝袋']
            edited_df.at[i, '單位'] = INVENTORY_STANDARDS[item_name]['單位']
    st.session_state.df = edited_df

# 學習功能
if st.button("💾 儲存並學習品項修正"):
    learned_count = 0
    for _, row in st.session_state.df.iterrows():
        if row['原始文字'] and row['品項']:
            save_mapping(row['原始文字'], row['品項'])
            learned_count += 1
    st.toast(f"已記錄 {learned_count} 筆對應關係，下次辨識會參考此紀錄！")

# 計算叫貨量
if st.button("🚀 計算叫貨量"):
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
