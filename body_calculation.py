import streamlit as st
import pandas as pd
from datetime import date
import os
import calendar
import altair as alt

# ==================================================
# Configuration
# ==================================================
st.set_page_config(page_title="Health Dashboard", layout="wide")

# ==================================================
# Files
# ==================================================
FOOD_FILE = "food_log.csv"

# ==================================================
# Food Database (example)
# ==================================================
food_db = {
    "Egg": 78,
    "Toast": 75,
    "Oatmeal": 150,
    "Chicken Breast (100g)": 165,
    "Rice (1 cup)": 206,
    "Salad": 50,
    "Apple": 95,
    "Banana": 105,
    "Pasta (1 cup)": 200,
    "Milk (1 cup)": 122,
    "Yogurt (100g)": 59
}

# ==================================================
# Helper Functions
# ==================================================
def load_food_data():
    if os.path.exists(FOOD_FILE):
        return pd.read_csv(FOOD_FILE)
    return pd.DataFrame(columns=["date", "meal", "food", "calories_in", "exercise", "calories_out"])

def save_food_data(entries):
    df = load_food_data()
    df = pd.concat([df, pd.DataFrame(entries)], ignore_index=True)
    df.to_csv(FOOD_FILE, index=False)

# -------------------
# Body Measurement
# -------------------
def calculate_bmi(weight, height_cm):
    return weight / ((height_cm / 100) ** 2)

def bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal weight"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obese"

def calculate_bmr(weight, height_cm, age, gender):
    if gender == "Male":
        return 88.36 + (13.4 * weight) + (4.8 * height_cm) - (5.7 * age)
    else:
        return 447.6 + (9.2 * weight) + (3.1 * height_cm) - (4.3 * age)

def target_weight(height_cm):
    h_m = height_cm / 100
    return 18.5 * (h_m ** 2), 24.9 * (h_m ** 2)

def daily_calories(weight, height_cm, age, gender, activity_level=1.2):
    return calculate_bmr(weight, height_cm, age, gender) * activity_level

def health_recommendation(bmi, weight, height_cm, age, gender):
    min_w, max_w = target_weight(height_cm)
    calories = daily_calories(weight, height_cm, age, gender)
    if bmi < 18.5:
        return f"😋 Underweight! Gain ~{round(min_w - weight,1)} kg. Calories/day: {int(calories)} kcal"
    elif bmi < 25:
        return f"🎉 Healthy weight! Maintain. Calories/day: {int(calories)} kcal"
    elif bmi < 30:
        return f"⚖️ Overweight! Lose ~{round(weight - max_w,1)} kg. Calories/day: {int(calories)-500} kcal"
    else:
        return f"🚨 Obese! Lose ~{round(weight - max_w,1)} kg. Calories/day: {int(calories)-500} kcal"

# ==================================================
# Main Tabs
# ==================================================
body_tab, food_tab, monthly_tab, run_tab = st.tabs([
    "🧍 Body Measurement",
    "🍎 Food & Exercise",
    "📅 Monthly Calendar",
    "🏃 Run Performance"
])

# ==================================================
# BODY MEASUREMENT TAB
# ==================================================
with body_tab:
    st.title("🧍 Health Dashboard")
    st.caption("Modern UI inspired by Garmin & Strava")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Age", min_value=10, max_value=100)
        height = st.number_input("Height (cm)", min_value=100, max_value=250)
    with col2:
        gender = st.selectbox("Gender", ["Male", "Female"])
        weight = st.number_input("Weight (kg)", min_value=30, max_value=300)

    if st.button("Analyze Health", use_container_width=True):
        bmi = calculate_bmi(weight, height)
        bmr = calculate_bmr(weight, height, age, gender)
        category = bmi_category(bmi)
        recommendation = health_recommendation(bmi, weight, height, age, gender)

        # -----------------------------
        # Metrics Cards
        # -----------------------------
        c1, c2, c3 = st.columns(3)
        metrics = [("BMI", f"{bmi:.2f}", category),
                   ("BMR (kcal/day)", f"{bmr:.0f}", ""),
                   ("Weight Category", category, "")]

        for col, (title, value, extra) in zip([c1, c2, c3], metrics):
            col.markdown(f'''
                <div style="background:#ffffff;padding:20px;border-radius:15px;box-shadow:0 4px 12px rgba(0,0,0,0.1);text-align:center;">
                    <div style="font-size:16px;color:#000;margin-bottom:4px;">{title}</div>
                    <div style="font-size:28px;font-weight:700;color:#000;margin-bottom:4px;">{value}</div>
                    <div style="font-size:14px;color:#555;">{extra}</div>
                </div>
            ''', unsafe_allow_html=True)

        st.markdown(f'''
            <div style="background-color:#f0f9ff;padding:15px;border-radius:15px;font-weight:700;color:#000;">
                {recommendation}
            </div>
        ''', unsafe_allow_html=True)

# ==================================================
# FOOD & EXERCISE TAB
# ==================================================
with food_tab:
    st.title("🍎 Food & Exercise Tracker")
    log_date = st.date_input("Date", value=date.today())

    with st.expander("📋 Food Tracker"):
        meals = ["Breakfast","Lunch","Dinner"]
        meal_entries = []
        for meal in meals:
            st.markdown(f"### {meal}")
            foods_selected = st.multiselect(f"Select foods for {meal}", list(food_db.keys()), key=meal)
            calories_in = sum([food_db[f] for f in foods_selected]) if foods_selected else 0
            st.write(f"Calories: {calories_in} kcal")
            meal_entries.append({
                "date": log_date.strftime("%d/%m/%Y"),
                "meal": meal,
                "food": ", ".join(foods_selected) if foods_selected else "",
                "calories_in": calories_in,
                "exercise": "",
                "calories_out":0
            })

    with st.expander("🏋️ Exercise Logging"):
        exercise_item = st.text_input("Exercise")
        calories_out = st.number_input("Calories Burned", min_value=0, step=1)

        if st.button("Save Today's Entry"):
            for entry in meal_entries:
                entry["exercise"] = exercise_item
            if exercise_item and calories_out>0:
                meal_entries.append({
                    "date": log_date.strftime("%d/%m/%Y"),
                    "meal":"Exercise","food":"","calories_in":0,
                    "exercise":exercise_item,"calories_out":calories_out
                })
            save_food_data(meal_entries)
            st.success("Saved successfully!")

    # -----------------------------
    # Daily Summary Table
    # -----------------------------
    # -----------------------------
# Daily Summary Table
# -----------------------------
    df_food = load_food_data()
    if not df_food.empty:
        df_food["date"] = pd.to_datetime(df_food["date"], dayfirst=True).dt.date
        daily_summary = df_food.groupby("date").agg({
            "calories_in":"sum",
            "calories_out":"sum"
        }).reset_index()
        daily_summary["net_calories"] = daily_summary["calories_in"] - daily_summary["calories_out"]

        # Add index starting from 1
        daily_summary.index = daily_summary.index + 1
        daily_summary.index.name = "No."

        # Create a styled table with black text
        def style_row(row):
            if row.net_calories <= 2000:
                bg_color = "#d4edda"  # green
            elif row.net_calories <= 2500:
                bg_color = "#fff3cd"  # yellow
            else:
                bg_color = "#f8d7da"  # red
            return [f'background-color:{bg_color}; color:black']*len(row)  # black text

        st.markdown("### 📊 Daily Calories Summary (Table View)")
        styled_table = daily_summary.style.apply(style_row, axis=1).format({
            "calories_in": "{:.0f}",
            "calories_out": "{:.0f}",
            "net_calories": "{:.0f}"
        }).set_properties(**{
            "text-align": "center",
            "font-weight": "600",
            "border": "1px solid #ccc"
        })
        st.dataframe(styled_table, use_container_width=True)

        st.markdown("### 📈 Calories Over Time")
        chart = alt.Chart(daily_summary.melt(id_vars=["date"], value_vars=["calories_in","calories_out","net_calories"],
                                            var_name="Type",value_name="Calories")
                          ).mark_line(point=True).encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("Calories:Q", title="Calories"),
            color="Type:N",
            tooltip=["date:T","Type:N","Calories:Q"]
        ).properties(height=400)
        st.altair_chart(chart,use_container_width=True)

# ==================================================
# RUN PERFORMANCE TAB
# ==================================================
with run_tab:
    st.markdown("### 🏃 Run Performance Dashboard")
    st.markdown(
        '<a href="http://localhost:8502/" target="_blank">'
        '<button style="background: linear-gradient(90deg,#ff6a00,#ff9800);color:white;padding:12px 24px;border:none;border-radius:14px;font-weight:700;font-size:16px;">'
        'Open Run Performance</button></a>',
        unsafe_allow_html=True
    )

# ==================================================
# MONTHLY CALENDAR TAB
# ==================================================
with monthly_tab:
    st.title("📅 Monthly Calories Calendar")
    df_food = load_food_data()
    if not df_food.empty:
        df_food["date"] = pd.to_datetime(df_food["date"], dayfirst=True).dt.date
        col1,col2 = st.columns(2)
        with col1:
            selected_year = st.number_input("Year",2000,2100,date.today().year)
        with col2:
            selected_month = st.selectbox("Month",range(1,13),index=date.today().month-1,
                                         format_func=lambda x: date(1900,x,1).strftime('%B'))
        df_month = df_food[(pd.to_datetime(df_food['date']).dt.year==selected_year)&
                           (pd.to_datetime(df_food['date']).dt.month==selected_month)]

        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdatescalendar(selected_year,selected_month)
        html = '<table style="width:100%;border-collapse:collapse;"><tr>' + \
               ''.join(f'<th style="border:1px solid #ccc;padding:8px;text-align:center;">{day}</th>' for day in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]) + '</tr>'
        for week in month_days:
            html += "<tr>"
            for day in week:
                if day.month == selected_month:
                    calories = df_month[df_month['date'] == day]["calories_in"].sum() - df_month[df_month['date'] == day]["calories_out"].sum()
                    # Set background color
                    if calories <= 2000:
                        bg_color = "#d4edda"  # green
                    elif calories <= 2500:
                        bg_color = "#fff3cd"  # yellow
                    else:
                        bg_color = "#f8d7da"  # red
                    text_color = "#000"  # black text
                    html += f'<td style="border:1px solid #ccc; padding:8px; vertical-align:top; background:{bg_color}; color:{text_color}; font-weight:700; text-align:center;">'
                    html += f'{day.day}<br>{int(calories)} kcal</td>'
                else:
                    html += '<td style="border:1px solid #ccc; padding:8px; background-color:#f5f5f5;"></td>'
            html += "</tr>"
        html+="</table>"
        st.markdown(html,unsafe_allow_html=True)
    else:
        st.info("No data available.")
