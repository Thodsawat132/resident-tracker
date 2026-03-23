import streamlit as st
import pandas as pd
from datetime import date
import google.generativeai as genai

# ==========================================
# 1. Initialization: Clinical Targets & Databases
# ==========================================
DAILY_TARGET = 2100

# สร้าง Database ชั่วคราว (Session State)
if 'food_log' not in st.session_state:
    st.session_state.food_log = pd.DataFrame(columns=['Date', 'Meal', 'Kcal', 'Protein (g)', 'Image'])
if 'weight_log' not in st.session_state:
    st.session_state.weight_log = pd.DataFrame(columns=['Date', 'Weight (kg)'])
if 'activity_log' not in st.session_state:
    st.session_state.activity_log = pd.DataFrame(columns=['Date', 'Activity_Type', 'Detail', 'Burned_Kcal'])

# ==========================================
# 2. User Interface (UI)
# ==========================================
st.title("🩺 Resident's Metabolic Tracker")
st.write(f"**Target Caloric Deficit:** {DAILY_TARGET} kcal/day")

# แบ่งหน้าจอเป็น 2 Tabs
tab1, tab2 = st.tabs(["📝 Daily Flowsheet", "📊 Weekly Assessment & AI"])

# ==========================================
# TAB 1: Daily Flowsheet (บันทึกอาหารและกิจกรรม)
# ==========================================
with tab1:
    selected_date = st.date_input("📅 Select Date (Daily Log)", date.today(), key="daily_date")
    
    # --- บันทึกมื้ออาหาร ---
    with st.form("food_entry", clear_on_submit=True):
        st.subheader("🍽️ Add Meal (บันทึกมื้ออาหาร)")
        meal_name = st.text_input("ชื่ออาหาร (เช่น ข้าวมันไก่ ไม่หนัง):")
        kcal = st.number_input("พลังงานโดยประมาณ (kcal):", min_value=0, step=50)
        protein = st.number_input("โปรตีนโดยประมาณ (g):", min_value=0, step=5)
        uploaded_image = st.file_uploader("📸 อัปโหลดรูปภาพอาหาร (ถ้ามี)", type=['png', 'jpg', 'jpeg'])
        
        if st.form_submit_button("Save Meal") and meal_name:
            new_entry = pd.DataFrame([{'Date': pd.to_datetime(selected_date), 'Meal': meal_name, 'Kcal': kcal, 'Protein (g)': protein, 'Image': uploaded_image}])
            st.session_state.food_log = pd.concat([st.session_state.food_log, new_entry], ignore_index=True)
            st.success("บันทึกมื้ออาหารสำเร็จ!")

    # --- บันทึกกิจกรรม (Physical Activity) ---
    with st.form("activity_entry", clear_on_submit=True):
        st.subheader("🏃‍♂️ Add Activity (บันทึกกิจกรรม)")
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            steps = st.number_input("👣 จำนวนก้าวเดิน (ก้าว):", min_value=0, step=500)
        with col_a2:
            ex_type = st.selectbox("🏋️‍♂️ ระดับการออกกำลังกาย:", ["ไม่มี", "เบา (Light)", "ปานกลาง (Moderate)", "หนัก (Vigorous)"])
            ex_duration = st.number_input("ระยะเวลา (นาที):", min_value=0, step=10)

        if st.form_submit_button("Save Activity"):
            step_burn = steps * 0.04
            ex_burn = 0
            if ex_type == "เบา (Light)": ex_burn = ex_duration * 7
            elif ex_type == "ปานกลาง (Moderate)": ex_burn = ex_duration * 10
            elif ex_type == "หนัก (Vigorous)": ex_burn = ex_duration * 13
            
            total_burn = step_burn + ex_burn
            if total_burn > 0:
                act_detail = f"เดิน {steps} ก้าว" if steps > 0 else ""
                if ex_duration > 0: act_detail += f" + {ex_type} {ex_duration} นาที"
                new_act = pd.DataFrame([{'Date': pd.to_datetime(selected_date), 'Activity_Type': 'Mixed', 'Detail': act_detail.strip(" + "), 'Burned_Kcal': total_burn}])
                st.session_state.activity_log = pd.concat([st.session_state.activity_log, new_act], ignore_index=True)
                st.success(f"บันทึกกิจกรรมสำเร็จ! เผาผลาญเพิ่มไปประมาณ {int(total_burn)} kcal")

    # --- Daily Dashboard ---
    st.divider()
    st.subheader(f"📊 Daily Report: {selected_date.strftime('%d %b %Y')}")
    
    daily_food = st.session_state.food_log[pd.to_datetime(st.session_state.food_log['Date']).dt.date == selected_date]
    daily_act = st.session_state.activity_log[pd.to_datetime(st.session_state.activity_log['Date']).dt.date == selected_date]
    
    total_in = daily_food['Kcal'].sum() if not daily_food.empty else 0
    total_pro = daily_food['Protein (g)'].sum() if not daily_food.empty else 0
    total_out = daily_act['Burned_Kcal'].sum() if not daily_act.empty else 0
    
    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    col_d1.metric("🍽️ Intake", f"{int(total_in)} kcal")
    col_d2.metric("🔥 Active Burn", f"{int(total_out)} kcal")
    col_d3.metric("🎯 Net Target", f"{int(total_in)} / {DAILY_TARGET}")
    col_d4.metric("🥩 Protein", f"{int(total_pro)} g")

# ==========================================
# TAB 2: Weekly Assessment & AI Assistant
# ==========================================
with tab2:
    st.header("Weekly Clinical Summary")
    
    # --- Body Weight Tracking ---
    st.subheader("⚖️ Body Weight Tracker")
    col_w1, col_w2 = st.columns([2, 1])
    with col_w1:
        weight_date = st.date_input("Date for Weight Log", date.today(), key="weight_date")
    with col_w2:
        current_weight = st.number_input("Weight (kg)", min_value=50.0, max_value=150.0, value=98.0, step=0.1)
        
    if st.button("Record Weight"):
        new_weight = pd.DataFrame([{'Date': pd.to_datetime(weight_date), 'Weight (kg)': current_weight}])
        st.session_state.weight_log = pd.concat([st.session_state.weight_log, new_weight], ignore_index=True)
        st.success("บันทึกน้ำหนักสำเร็จ!")

    # --- AI Clinical Assistant (Gemini) ---
    st.divider()
    st.subheader("🤖 AI Clinical Assistant (Gemini)")
    st.caption("ระบบจะดึงข้อมูลประวัติส่งให้ Gemini วิเคราะห์ Macronutrients Distribution ของสัปดาห์นี้")
    
    if st.button("✨ ให้ Gemini วิเคราะห์และวางแผนสัปดาห์ถัดไป"):
        try:
            api_key = st.secrets["GEMINI_API_KEY"]
            genai.configure(api_key=api_key)
            
            weight_data = st.session_state.weight_log.to_string() if not st.session_state.weight_log.empty else "ไม่มีข้อมูล"
            food_data = st.session_state.food_log[['Date', 'Meal', 'Kcal', 'Protein (g)']].to_string() if not st.session_state.food_log.empty else "ไม่มีข้อมูล"
            act_data = st.session_state.activity_log[['Date', 'Detail', 'Burned_Kcal']].to_string() if not st.session_state.activity_log.empty else "ไม่มีข้อมูล"
            
            prompt = f"""
            คุณคือ AI ผู้ช่วยแพทย์ (Internal Medicine Board) 
            กรุณาวิเคราะห์ข้อมูลสุขภาพรายสัปดาห์ของแพทย์ประจำบ้านชาย อายุ 30 ปี สูง 174 ซม. 
            เป้าหมายคือลดน้ำหนัก (Target Caloric Intake: 2,100 kcal/day)
            
            วิเคราะห์ "Macronutrients Distribution":
            1. ประเมินปริมาณโปรตีนที่ได้รับ (Clinical Target: 130-150 g/day)
            2. ประเมิน Total Caloric Intake เทียบกับ Target
            
            ข้อมูล:
            น้ำหนัก: {weight_data}
            อาหาร: {food_data}
            กิจกรรม: {act_data}
            
            เขียน Clinical Note สั้นๆ สรุปผลลัพธ์ และวาง Action Plan 3 ข้อ เน้น Dietary modification ที่ใช้ได้จริงช่วงอยู่เวรดึก
            """
            
            with st.spinner("🧠 Gemini กำลังประมวลผล Clinical Data..."):
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                st.markdown(response.text)
                
        except KeyError:
            st.error("🚨 ไม่พบ API Key! กรุณาตั้งค่า GEMINI_API_KEY ในหน้า Settings ของ Streamlit Cloud")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")
