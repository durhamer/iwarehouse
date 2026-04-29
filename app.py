import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import math
from PIL import Image
from datetime import datetime

# 1. 系統資料預設值
INVENTORY_STANDARDS = {
    "波霸薯條": {"標準_完整包": 8, "標準_分裝袋": 2, "單位": "包", "進貨單位": "箱", "進貨換算": 6},
    "甜不辣": {"標準_完整包": 2, "標準_分裝袋": 2, "單位": "包", "進貨單位": "麻袋", "進貨換算": 8},
    "魷米花": {"標準_完整包": 2, "標準_分裝袋": 2, "單位": "包", "進貨單位": "包", "進貨換算": 1},
    "地瓜薯條": {"標準_完整包": 2, "標準_分裝袋": 2, "單位": "包", "進貨單位": "箱", "進貨換算": 6},
    "小雞塊": {"標準_完整包": 8, "標準_分裝袋": 0, "單位": "包", "進貨單位": "包", "進貨換算": 1},
    "洋蔥圈": {"標準_完整包": 7, "標準_分裝袋": 0, "單位": "包", "進貨單位": "包", "進貨換算": 1},
    "山藥卷": {"標準_完整包": 1, "標準_分裝袋": 0, "單位": "箱", "進貨單位": "箱", "進貨換算": 1},
    "披薩球": {"標準_完整包": 1, "標準_分裝袋": 0, "單位": "包", "進貨單位": "包", "進貨換算": 1},
    "小芋泥球": {"標準_完整包": 1, "標準_分裝袋": 0, "單位": "包", "進貨單位": "包", "進貨換算": 1},
    "芝麻芋泥球": {"標準_完整包": 1, "標準_分裝袋": 0, "單位": "包", "進貨單位": "包", "進貨換算": 1},
    "花枝丸": {"標準_完整包": 2, "標準_分裝袋": 0, "單位": "包", "進貨單位": "包", "進貨換算": 1},
    "薯餅": {"標準_完整包": 1, "標準_分裝袋": 0, "單位": "包", "進貨單位": "包", "進貨換算": 1},
    "地瓜球": {"標準_完整包": 1, "標準_分裝袋": 0, "單位": "包", "進貨單位": "包", "進貨換算": 1},
    "鱈魚條": {"標準_完整包": 4, "標準_分裝袋": 0, "單位": "包", "進貨單位": "包", "進貨換算": 1},
    "銀絲卷": {"標準_完整包": 5, "標準_分裝袋": 0, "單位": "包", "進貨單位": "包", "進貨換算": 1},
    "玉米布丁酥": {"標準_完整包": 3, "標準_分裝袋": 0, "單位": "包", "進貨單位": "包", "進貨換算": 1},
    "乳酪甜心酥": {"標準_完整包": 1, "標準_分裝袋": 0, "單位": "份", "進貨單位": "份", "進貨換算": 1},
    "蔥仔餅": {"標準_完整包": 2, "標準_分裝袋": 0, "單位": "包", "進貨單位": "包", "進貨換算": 1},
    "大熱狗": {"標準_完整包": 2, "標準_分裝袋": 0, "單位": "包", "進貨單位": "包", "進貨換算": 1},
    "蘋果派": {"標準_完整包": 10, "標準_分裝袋": 0, "單位": "個", "進貨單位": "個", "進貨換算": 1},
    "香腸": {"標準_完整包": 2, "標準_分裝袋": 0, "單位": "包", "進貨單位": "包", "進貨換算": 1},
    "湯圓": {"標準_完整包": 3, "標準_分裝袋": 0, "單位": "包", "進貨單位": "包", "進貨換算": 1}
}

def calculate_order_qty(item_name, current_full, current_bin, current_split):
    """
    計算單一品項的需叫貨量
    規則：
    1. 庫存換算：1袋『分裝』 = 2個『基礎單位』(包/個/份)
    2. 總標準 = 標準_完整包 + (標準_分裝袋 * 2)
    3. 總庫存 = 臥式冰箱 + 二門+四門 + (分裝 * 2)
    4. 需叫貨量 = 總標準 - 總庫存 (若 <= 0 則不叫貨)
    5. 進貨換算：需叫貨量 / 進貨換算，並無條件進位
    """
    spec = INVENTORY_STANDARDS.get(item_name)
    if not spec:
        return None
    
    # 總標準量換算成基礎單位
    total_standard = spec['標準_完整包'] + (spec['標準_分裝袋'] * 2)
    
    # 總現有庫存換算成基礎單位
    total_inventory = current_full + current_bin + (current_split * 2)
    
    needed_base_qty = total_standard - total_inventory
    
    if needed_base_qty <= 0:
        return None
    
    # 計算進貨單位數量
    purchase_unit_qty = math.ceil(needed_base_qty / spec['進貨換算'])
    return f"{purchase_unit_qty}{spec['進貨單位']}"

def format_order_qty(qty, unit):
    # 此舊函數已被 calculate_order_qty 取代
    return None

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
        - **對齊規則**：將辨識出的名稱對齊至下方的標準品項清單。
        - **重要：清單外品項**：如果白板上的品項「完全不屬於」標準清單中的任何一項，請不要硬湊，直接在「品項」欄位填入你看到的原始文字。
        - **原始文字**：無論是否對齊成功，請務必記錄你在白板上實際看到的文字。
        - 若無法辨識數值，請填入 0。
        
        【標準品項清單】
        {standard_names}
        
        【輸出格式】
        僅回傳純 JSON 列表格式：
        [
          {{
            "原始文字": "白板上的字",
            "品項": "對齊後的名稱或原始文字",
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
    # 根據新的 INVENTORY_STANDARDS 結構調整欄位名稱 (包含 index 共 6 欄)
    df_base.columns = ['品項', '標準_完整包', '標準_分裝袋', '單位', '進貨單位', '進貨換算']
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
                
                # 檢查是否有不在清單中的品項 (幽靈品項)
                unrecognized_items = [res['品項'] for res in ai_results if res.get('品項') not in INVENTORY_STANDARDS]
                
                # 重新排序
                all_items = list(INVENTORY_STANDARDS.keys())
                remaining_items = [item for item in all_items if item not in ai_item_names]
                new_order = ai_item_names + remaining_items
                
                # 重建 DataFrame
                new_df = pd.DataFrame.from_dict(INVENTORY_STANDARDS, orient='index').reset_index()
                new_df.columns = ['品項', '標準_完整包', '標準_分裝袋', '單位', '進貨單位', '進貨換算']
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
                st.success("辨識完成！已根據照片順序重新排列。")
                
                # 顯示警告訊息：如果發現不在清單中的品項
                if unrecognized_items:
                    items_str = "、".join(unrecognized_items)
                    st.warning(f"⚠️ **注意：白板上有 {len(unrecognized_items)} 個品項無法對齊標準清單：**\n\n「{items_str}」\n\n這些品項將不會出現在下方的編輯表格中。若這是新產品，請聯繫系統管理員更新標準庫存清單。")

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
            spec = INVENTORY_STANDARDS[item_name]
            edited_df.at[i, '標準_完整包'] = spec['標準_完整包']
            edited_df.at[i, '標準_分裝袋'] = spec['標準_分裝袋']
            edited_df.at[i, '單位'] = spec['單位']
            edited_df.at[i, '進貨單位'] = spec['進貨單位']
            edited_df.at[i, '進貨換算'] = spec['進貨換算']
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
    
    # 產出結果
    order_items = []
    for _, row in df.iterrows():
        qty_str = calculate_order_qty(
            row['品項'], 
            row['臥式冰箱'], 
            row['二門+四門'], 
            row['分裝']
        )
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
