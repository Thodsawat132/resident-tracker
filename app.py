import streamlit as st
import pandas as pd
from datetime import date
import google.generativeai as genai
from PIL import Image
import io

# ==========================================
# 1. Initialization: Databases & Targets
# ==========================================
DAILY_TARGET = 2100

# กำหนดโครงสร้าง Database
if 'food_log' not in st.session_state:
    st.session_state.food_log = pd.DataFrame(columns=['Date', 'Meal', 'Kcal', 'Protein (g)', 'Image'])
if 'weight_log' not in st.session_state:
    st.session_state.weight_log = pd.DataFrame(columns=['Date', 'Weight (kg)'])
if 'activity_log' not in st.session_state:
    st.session_state.activity_log = pd.DataFrame(columns=['Date', 'Activity_Type', 'Detail', 'Burned_Kcal'])

# กำหนดค่าเริ่มต้นสำหรับฟอร์ม (Form State)
if 'temp_kcal' not in st.session_state: st.session_state.temp_kcal = 0
if 'temp_protein' not in st.session_state: st.session_state.temp_protein = 0
if 'temp_meal_name' not in st.session_state: st.session_state.temp_meal_name = ""

# ==========================================
# 2. User Interface (UI)
# ==========================================
st.title("🩺 Resident's Metabolic Tracker v2")
st.write(f"**Target Caloric Deficit:** {DAILY_TARGET} kcal/day")

tab1, tab2 = st.tabs(["📝 Daily Flowsheet", "📊 Weekly AI Assessment"])

# ==========================================
# TAB 1: Daily Flowsheet
# ==========================================
with tab1:
    selected_date = st.date_input("📅 Select Date", date.today(), key="daily_date")
    
    # --- บันทึกมื้ออาหาร (Upgrade: AI Vision) ---
    with st.form("food_entry", clear_on_submit=True):
        st.subheader("🍽️ Add Meal (บันทึกมื้ออาหาร)")
        uploaded_image = st.file_uploader("📸 ถ่ายรูป/อัปโหลดรูปภาพอาหาร", type=['png', 'jpg', 'jpeg'])
        
        # แสดงรูปภาพตัวอย่าง
        if uploaded_image:
            image = Image.open(uploaded_image)
            st.image(image, caption="รูปภาพที่อัปโหลด", use_container_width=True)
            
            # --- ปุ่มสั่ง Gemini Vision (API Call) ---
            if st.form_submit_button("🧠 ให้ AI ประเมินข้อมูลอาหารจากรูป"):
                try:
                    # 1. เรียก API Key และ Config Gemini
                    api_key = st.secrets["GEMINI_API_KEY"]
                    genai.configure(api_key=api_key)
                    model_vision = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # 2. เตรียมภาพ
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format=image.format)
                    img_bytes = img_byte_arr.getvalue()
                    
                    # 3. เขียน Prompt สั่งงาน AI Vision
                    prompt_vision = """
                    คุณคือ AI ผู้ช่วยนักโภชนาการสำหรับแพทย์ประจำบ้าน
                    กรุณามองรูปภาพอาหารนี้ และประเมินค่าดังต่อไปนี้ตามหลักโภชนาการมาตรฐาน:
                    1. ชื่ออาหาร (ให้ชื่อเป็นภาษาไทยที่กระชับ)
                    2. พลังงานโดยประมาณ (Kcal) 
                    3. โปรตีนโดยประมาณ (กรัม)
                    
                    กรุณาตอบเป็นข้อความรูปแบบ JSON เท่านั้น เช่น:
                    {"Meal_Name": "ข้าวมันไก่", "Kcal": 650, "Protein_g": 25}
                    """
                    
                    # 4. เรียกใช้ Gemini Vision
                    with st.spinner("🧠 Gemini กำลังมองรูปและประมวลผลข้อมูลสารอาหาร..."):
                        response = model_vision.generate_content([prompt_vision, {"mime_type": "image/jpeg", "data": img_bytes}])
                        # ประมวลผล JSON output
                        import json
                        import re
                        json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group(0) # ดึงเฉพาะส่วน JSON
                        data = json.loads(json_str)
                        
                        # บันทึกค่าลง Form State ชั่วคราว
                        st.session_state.temp_meal_name = data.get("Meal_Name", "อาหารไม่ระบุชื่อ")
                        st.session_state.temp_kcal = data.get("Kcal", 0)
                        st.session_state.temp_protein = data.get("Protein_g", 0)
                        
                        st.success("✅ ประเมินข้อมูลสำเร็จ! คุณหมอสามารถตรวจสอบและแก้ไขข้อมูลด้านล่างก่อนกดบันทึกจริงได้ครับ")
                        
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ AI: {e}")

        # แสดงผลลัพธ์จาก AI ให้คุณหมอตรวจสอบและแก้ไข (Check & Balance)
        meal_name = st.text_input("ชื่ออาหาร (AI ประเมิน):", value=st.session_state.temp_meal_name)
        kcal = st.number_input("พลังงาน (kcal, AI ประเมิน):", min_value=0, step=50, value=int(st.session_state.temp_kcal))
        protein = st.number_input("โปรตีน (g, AI ประเมิน):", min_value=0, step=5, value=int(st.session_state.temp_protein))
        
        # --- ปุ่มบันทึกจริง ---
        if st.form_submit_button("💾 ยืนยันข้อมูลและบันทึกมื้ออาหาร"):
            if meal_name:
                new_entry = pd.DataFrame([{'Date': pd.to_datetime(selected_date), 'Meal': meal_name, 'Kcal': kcal, 'Protein (g)': protein, 'Image': uploaded_image}])
                st.session_state.food_log = pd.concat([st.session_state.food_log, new_entry], ignore_index=True)
                st.success(f"บันทึก {meal_name} ลง Flowsheet เรียบร้อยแล้วครับ")
                # รีเซ็ต Form State
                st.session_state.temp_kcal = 0
                st.session_state.temp_protein = 0
                st.session_state.temp_meal_name = ""

    # --- ส่วนกิจกรรมและ Daily Dashboard คงเดิม ---
    # ... (ส่วนบันทึกกิจกรรมและ Dashboard ของเดิม) ...

# ==========================================
# TAB 2: Weekly Assessment & AI Assistant คงเดิม
# ==========================================
# ... (ส่วนบันทึกน้ำหนักและ AI Summary ของเดิม) ...
