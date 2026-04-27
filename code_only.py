import streamlit as st
import pandas as pd
from datetime import date
import altair as alt
import psycopg2

def get_connection():
    return psycopg2.connect(
        "postgresql://postgres.ibulpdvkvyqwbjdkhsms:fitnessstreamlit@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"
    )

# ==================================================
# PASSWORDS
# ==================================================
PREMIUM_PASSWORD = "premium"

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="Run Performance",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# ==================================================
# SESSION STATE (LOGIN CONTROL)
# ==================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

# ==================================================
# Helpers
# ==================================================
def to_minutes(h, m, s):
    return h * 60 + m + s / 60

def pace_to_minutes(mins, secs):
    return mins + secs / 60

def format_time(minutes_float):
    total_seconds = int(round(minutes_float * 60))

    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60

    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    else:
        return f"{m}:{s:02d}"

def format_pace(pace_float):
    pace_min = int(pace_float)
    pace_sec = int(round((pace_float - pace_min) * 60))
    return f"{pace_min}:{pace_sec:02d}"

def get_distance_label(D2):
    if D2 == 42.195:
        return "Marathon (42.195 km)"
    elif D2 == 21.0975:
        return "Half Marathon (21.1 km)"
    else:
        return f"{int(D2)} km"

def format_pace(p):
    m = int(p)
    s = int(round((p - m) * 60))
    return f"{m}:{s:02d}"

def snap_bpm(x):
    last_digit = int(x) % 10

    if last_digit in [1, 2, 8, 9]:
        # round to nearest 10
        return round(x / 10) * 10

    elif last_digit in [3, 4, 6, 7]:
        # round to nearest 5
        return round(x / 5) * 5

    else:
        # already clean (0 or 5)
        return x

# ==================================================
# New Functions
# ==================================================
def read_runs():
    conn = get_connection()
    query = "SELECT * FROM 'Runs'"
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def save_run(run):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO "Runs" (date, distance_km, time_min, pace_min_per_km)
        VALUES (%s, %s, %s, %s)
    """,
    run["date"],
    run["distance_km"],
    run["time_min"],
    run["pace_min_per_km"])

    conn.commit()
    conn.close()

def load_notes():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT * FROM "Notes"
        WHERE user_id = %s
        ORDER BY date DESC
    """, conn, params=[st.session_state.user_db_id])
    conn.close()
    return df


def save_notes(df):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM "Notes"
        WHERE user_id = %s
    """, (st.session_state.user_db_id,))

    def clean(val):
        if pd.isna(val):
            return None
        return val

    for _, row in df.iterrows():
        cursor.execute("""
    INSERT INTO "Notes" (id, date, title, content, tags, user_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        new_id,
        row["date"],
        row["title"],
        row["content"],
        row.get("tags"),
        st.session_state.user_db_id
    ))

    conn.commit()
    conn.close()

def load_events():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT * FROM "Events"
        WHERE user_id = %s
        ORDER BY date ASC
    """, conn, params=[st.session_state.user_db_id])
    conn.close()
    return df

def save_events(df):
    conn = get_connection()
    cursor = conn.cursor()

    # ONLY delete current user's events (NOT ALL USERS)
    cursor.execute("""
        DELETE FROM "Events"
        WHERE user_id = %s
    """, (st.session_state.user_db_id,))

    # get safe starting id from DB (IMPORTANT)
    cursor.execute('SELECT COALESCE(MAX(id), 0) FROM "Events"')
    base_id = cursor.fetchone()[0]

    for i, row in enumerate(df.itertuples(), start=1):
        cursor.execute("""
            INSERT INTO "Events" (id, name, date, description, user_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            base_id + i,
            row.name,
            row.date,
            row.description,
            st.session_state.user_db_id
        ))

    conn.commit()
    conn.close()

# ==================================================
# Pace / Speed Helpers
# ==================================================
def pace_to_speed(pace_min_per_km):
    return 60 / pace_min_per_km

def speed_to_pace(speed_kmh):
    return 60 / speed_kmh

def time_table_from_pace(pace_min_per_km):
    distances = {
        "5 km": 5,
        "10 km": 10,
        "Half Marathon (21.1 km)": 21.097,
        "Full Marathon (42.2 km)": 42.195
    }

    rows = []
    for name, km in distances.items():
        total_minutes = pace_min_per_km * km
        hours = int(total_minutes // 60)
        minutes = int(total_minutes % 60)
        seconds = int((total_minutes - hours*60 - minutes) * 60)

        if hours > 0:
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            time_str = f"{minutes:02d}:{seconds:02d}"

        rows.append({
            "Distance": name,
            "Time": time_str
        })

    return rows

# ==================================================
# USER AUTH CRUD
# ==================================================

def create_user(name, user_id, password):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO "Users" (name, user_id, password)
        VALUES (%s, %s, %s)
    """, (name, user_id, password))

    conn.commit()
    conn.close()


def get_user(user_id, password):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name
        FROM "Users"
        WHERE user_id = %s AND password = %s
    """, (user_id, password))

    user = cursor.fetchone()
    conn.close()

    return user


def check_user_exists(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM "Users" WHERE user_id = %s
    """, (user_id,))

    user = cursor.fetchone()
    conn.close()

    return user is not None

# ==================================================
# CRUD functions
# ==================================================

# Run CRUD
def create_run(date, distance_km, time_min, pace):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO "Runs" (date, distance_km, time_min, pace_min_per_km, user_id)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        date,
        distance_km,
        time_min,
        pace,
        st.session_state.user_db_id
    ))

    conn.commit()
    conn.close()

def read_runs():

    conn = get_connection()

    df = pd.read_sql("""
        SELECT *
        FROM "Runs"
        WHERE user_id = %s
        ORDER BY date DESC
    """, conn, params=[st.session_state.user_db_id])

    conn.close()
    return df

def update_run(run_id, date, distance_km, time_min, pace):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE "Runs"
        SET date = %s,
            distance_km = %s,
            time_min = %s,
            pace_min_per_km = %s
        WHERE id = %s AND user_id = %s
    """, (
        date,
        distance_km,
        time_min,
        pace,
        run_id,
        st.session_state.user_db_id
    ))

    conn.commit()
    conn.close()

def delete_run(run_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM "Runs"
        WHERE id = %s AND user_id = %s
    """, (
        run_id,
        st.session_state.user_db_id
    ))

    conn.commit()
    conn.close()

# Note CRUD
def create_note(note):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO "Notes" (id, date, title, content, tags, user_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """,
    note["id"],
    note["date"],
    note["title"],
    note["content"],
    note.get("tags", None),
    st.session_state.user_db_id)

    conn.commit()
    conn.close()

def read_notes():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT * FROM "Notes"
        WHERE user_id = %s
        ORDER BY date DESC
    """, conn, params=[st.session_state.user_db_id])
    conn.close()
    return df

def update_note(note_id, title, content, tags=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE "Notes"
        SET title = %s, content = %s, tags = %s
        WHERE id = %s AND user_id = %s
    """,
    (title, content, tags, note_id, st.session_state.user_db_id)
)

    conn.commit()
    conn.close()

def delete_note(note_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM "Notes"
        WHERE id = %s AND user_id = %s
    """,
    (note_id, st.session_state.user_db_id))

    conn.commit()
    conn.close()

# Event CRUD
def create_event(name, date, description):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO "Events" (name, date, description, user_id)
        VALUES (%s, %s, %s, %s)
    """,
    name,
    date,
    description,
    st.session_state.user_db_id)

    conn.commit()
    conn.close()

def read_events():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM 'Events' ORDER BY date ASC", conn)
    conn.close()
    return df

def update_event(event_id, name, date, description):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE "Events"
        SET name = %s, date = %s, description = %s
        WHERE id = %s
    """,
    (name, date, description, event_id))

    conn.commit()
    conn.close()

def delete_event(event_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM 'Events' WHERE id = %s", (event_id,))

    conn.commit()
    conn.close()

# ==================================================
# ULTRA-PREMIUM GARMIN / STRAVA CSS (MOBILE FRIENDLY)
# ==================================================
st.markdown("""
<style>
/* ---------- Global ---------- */
.block-container {
    max-width: 100%;
    padding: 1rem 1.2rem; /* smaller padding for mobile */
}

body {
    background: radial-gradient(circle at top, #111 0%, #0b0b0b 60%);
    color: #eaeaea;
    font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont;
}

/* ---------- Headings ---------- */
h1, h2, h3 {
    font-weight: 800;
    letter-spacing: -0.5px;
}

/* ---------- Hero ---------- */
.hero {
    background: linear-gradient(135deg, #ff6a00, #ff9800);
    padding: 24px;
    border-radius: 20px;
    box-shadow: 0 10px 40px #00000080;
    margin-bottom: 20px;
    text-align: center;
}
.hero h2 {
    color: white;
    font-size: 28px;
}
.hero p {
    color: white;
    opacity: 0.95;
    font-size: 14px;
}

/* ---------- Cards ---------- */
.card {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(14px);
    padding: 16px;
    border-radius: 16px;
    box-shadow: 0 10px 30px #00000060;
    transition: transform 0.2s ease;
    text-align: center;
}
.card:hover {
    transform: translateY(-2px);
}

/* ---------- Metrics ---------- */
.metric-value {
    font-size: 28px;
    font-weight: 800;
    color: #ff8c00;
}
.metric-label {
    font-size: 12px;
    opacity: 0.75;
}

/* ---------- Buttons ---------- */
.stButton>button {
    background: linear-gradient(90deg, #ff6a00, #ff9800);
    color: white;
    border-radius: 14px;
    height: 44px;
    font-weight: 700;
    border: none;
    font-size: 14px;
    box-shadow: 0 8px 20px #00000080;
}
.stButton>button:hover {
    transform: scale(1.03);
}

/* ---------- Inputs ---------- */
input, .stNumberInput input {
    background: rgba(255,255,255,0.06);
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.15);
    color: white;
}

/* ---------- Tabs ---------- */
div[role="tablist"] button {
    background: rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 14px;
}
div[role="tablist"] button[aria-selected="true"] {
    background: linear-gradient(90deg, #ff6a00, #ff9800);
    color: white;
}

/* ---------- Calendar ---------- */
div.stMarkdown div.card {
    font-size: 12px;
    padding: 8px;
}

/* ---------- Mobile ---------- */
@media (max-width: 768px) {
    .block-container {
        padding: 0.8rem;
    }
    .metric-value {
        font-size: 20px;
    }
    .metric-label {
        font-size: 10px;
    }
    .hero h2 {
        font-size: 24px;
    }
    .hero p {
        font-size: 12px;
    }
    input, .stNumberInput input {
        font-size: 12px;
    }
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# HERO
# ==================================================
st.markdown("""
<div class="hero">
    <h2>🏃 All in One Running System</h2>
    <p>Garmin-level insights. Strava-grade aesthetics.</p>
</div>
""", unsafe_allow_html=True)

# ==================================================
# 🔐 LOGIN / SIGNUP SYSTEM
# ==================================================

if not st.session_state.logged_in:

    st.title("🔐 Fitness System Login")

    menu = st.radio("Choose Option", ["Login", "Sign Up"])

    # ================= LOGIN =================
    if menu == "Login":

        user_id_input = st.text_input("User ID")
        password_input = st.text_input("Password", type="password")

        if st.button("Login"):

            user = get_user(user_id_input, password_input)

            if user:
                st.session_state.logged_in = True
                st.session_state.user_db_id = user[0]   # 👈 THIS IS THE KEY
                st.session_state.username = user[1]

                st.success("Login successful")
                st.rerun()
            else:
                st.error("Invalid user ID or password")

    # ================= SIGN UP =================
    else:

        name = st.text_input("Name")
        new_user_id = st.text_input("Create User ID")
        new_password = st.text_input("Create Password", type="password")

        if st.button("Sign Up"):

            if name == "" or new_user_id == "" or new_password == "":
                st.warning("Please fill all fields")
            elif check_user_exists(new_user_id):
                st.error("User ID already exists ❌")
            else:
                create_user(name, new_user_id, new_password)
                st.success("Account created ✔️ Please login now")

if st.session_state.logged_in:
    # ==================================================
    # MAIN TABS
    # ==================================================
    tools, log, race_predictor, dash, event, calendar, notes = st.tabs([
        "⚡ Tools",
        "📝 Log Run",
        "🏃 Race Predictor",
        "📊 Performance",
        "🏁 Event Countdown",
        "📅 Calendar",
        "📝 Notes",
    ])

    # ==================================================
    # TOOLS
    # ==================================================
    with tools:
        pace_converter, speed_converter, hr_cb_calculator, VO_calculator, BMI_calculator, pace_spm_bpm_converter = st.tabs([
            "🧮 Pace Converter",
            "🚀 Speed Converter",
            "❤️‍🔥 Heart & Calorie Calculator",
            "📈 VO2 Max Calculator",
            "⚖️ BMI Calculator",
            "⏱️ Pace/SPM/BPM Converter"
        ])

        # ==================================================
        # PACE CONVERTER
        # ==================================================
        with pace_converter:
            pace, dist, time = st.tabs([
                "Pace",
                "Distance",
                "Time"
            ])

            # ---------------- Pace ----------------
            with pace:
                st.markdown("### Pace Calculator")
                d = st.number_input(
                    "Distance (km)", 0.1, step=0.1, value=5.0, key="p_d"
                )

                c1, c2, c3 = st.columns(3)
                h = c1.number_input("Hours", 0, key="p_h")
                m = c2.number_input("Minutes", 0, key="p_m")
                s = c3.number_input("Seconds", 0, 59, key="p_s")

                if st.button("Calculate Pace", key="p_btn"):
                    st.success(
                        f"{format_pace(to_minutes(h, m, s) / d)} min/km"
                    )

            # ---------------- Distance ----------------
            with dist:
                st.markdown("### Distance Calculator")

                st.markdown("**Pace (min/km)**")
                p1, p2 = st.columns(2)
                p_min = p1.number_input("Minutes", 0, key="d_p_min")
                p_sec = p2.number_input("Seconds", 0, 59, key="d_p_sec")

                c1, c2, c3 = st.columns(3)
                h = c1.number_input("Hours", 0, key="d_h")
                m = c2.number_input("Minutes", 0, key="d_m")
                s = c3.number_input("Seconds", 0, 59, key="d_s")

                if st.button("Calculate Distance", key="d_btn"):
                    pace = pace_to_minutes(p_min, p_sec)
                    t = to_minutes(h, m, s)

                    if pace > 0:
                        st.success(f"{t / pace:.2f} km")
                    else:
                        st.error("Pace cannot be 0")
                        
            # ---------------- Time ----------------
            with time:
                st.markdown("### Time Calculator")

                d = st.number_input("Distance (km)", 0.1, step=0.1, value=5.0, key="t_d")

                st.markdown("**Pace (min/km)**")
                p1, p2 = st.columns(2)
                p_min = p1.number_input("Minutes", 0, key="t_p_min")
                p_sec = p2.number_input("Seconds", 0, 59, key="t_p_sec")

                if st.button("Calculate Time", key="t_btn"):
                    pace = pace_to_minutes(p_min, p_sec)
                    t = d * pace

                    m = int(t)
                    s = int(round((t - m) * 60))
                    h = m // 60
                    m = m % 60

                    st.success(f"{h} hours, {m} minutes, {s} seconds")

        # ==================================================
        # SPEED CONVERTER (placeholder – safe)
        # ==================================================
        with speed_converter:
            pace_tab, speed_tab = st.tabs([
                "🏃 Pace → Speed",
                "🚀 Speed → Pace"
            ])

        # ---------------- Pace -> Speed ----------------
        with pace_tab:
            st.markdown("### 🏃 Pace → Speed (km/h)")

            c1, c2 = st.columns(2)
            pace_min = c1.number_input(
                "Minutes", 0, step=1, value=6, key="ps_min"
            )
            pace_sec = c2.number_input(
                "Seconds", 0, 59, step=1, value=0, key="ps_sec"
            )

            if st.button("Convert to Speed", key="ps_btn"):
                pace = pace_min + pace_sec / 60
                if pace > 0:
                    speed = 60 / pace
                    st.success(f"🚀 **{speed:.2f} km/h**")

                    st.markdown("#### ⏱ Estimated Finish Times")
                    table = time_table_from_pace(pace)
                    df_table = pd.DataFrame(table)
                    st.dataframe(df_table, use_container_width=True, hide_index=True)

                else:
                    st.warning("Pace must be greater than 0")

        # ---------------- Speed -> Pace ----------------
        with speed_tab:
            st.markdown("### 🚀 Speed → Pace (min/km)")

            speed = st.number_input(
                "Speed (km/h)", 0.1, step=0.1, value=10.0, key="sp_speed"
            )

            if st.button("Convert to Pace", key="sp_btn"):
                if speed > 0:
                    pace = 60 / speed
                    st.success(f"🏃 **{format_pace(pace)} min/km**")

                    st.markdown("#### ⏱ Estimated Finish Times")
                    table = time_table_from_pace(pace)
                    st.table(table)

                else:
                    st.warning("Speed must be greater than 0")

        # ==================================================
        # ❤️‍🔥 HEART & CALORIE CALCULATOR
        # ==================================================
        with hr_cb_calculator:
            heart_rate, calorie_burn = st.tabs([
                "❤️ Heart Rate Zones Calculator",
                "🔥 Calorie Burn Calculator"
            ])
            with heart_rate:
                st.markdown("### ❤️ Heart Rate Zones Calculator")

                age = st.number_input("Enter your age, minimum is 20", min_value=0, step=1, value=20)

                if age <= 19:
                    st.warning("Please enter an age greater than 19 for accurate heart rate zones.")
                else:
                    # ---------------- FORMULA ----------------
                    formula = st.selectbox(
                        "Select Formula",
                        ["Standard (220 - age)", "Tanaka (208 - 0.7 × age)"]
                    )

                    # ---------------- MAX HR ----------------
                    if formula == "Standard (220 - age)":
                        max_hr = 220 - age
                    else:
                        max_hr = int(208 - (0.7 * age))

                    st.success(f"🔥 Max Heart Rate: {max_hr} BPM")

                    # ---------------- ZONES ----------------
                    zones = [
                        ("Maximum (VO2 Max Zone)", "90–100%", "Sprint / Peak"),
                        ("Hard (Anaerobic Zone)", "80–90%", "Performance"),
                        ("Moderate (Aerobic Zone)", "70–80%", "Endurance"),
                        ("Light (Fat Burn Zone)", "60–70%", "Fat Burn"),
                        ("Very Light (Warm Up Zone)", "50–60%", "Recovery / Warm-up"),
                    ]

                    table_data = []

                    for name, percent, purpose in zones:
                        low, high = percent.replace("%", "").split("–")
                        low, high = int(low), int(high)

                        low_bpm = int(max_hr * low / 100)
                        high_bpm = int(max_hr * high / 100)

                        table_data.append({
                            "Zone": name,
                            "Intensity (%)": percent,
                            "Heart Rate (BPM)": f"{low_bpm} - {high_bpm}",
                            "Purpose": purpose
                        })

                    df_zones = pd.DataFrame(table_data)

                    st.markdown("### 📊 Heart Rate Zones Table")
                    st.table(df_zones)

                    st.markdown("""
                    💡 **Training Tips:**
                    - 🔵 Lower zones → recovery & fat burn  
                    - 🟢 Moderate → endurance  
                    - 🔴 High zones → intervals & performance  
                    """)

                # ==================================================
                # 🔥 ADVANCED CALORIE ESTIMATOR (NO BPM REQUIRED)
                # ==================================================
                with calorie_burn:
                    st.markdown("### 🔥 Calorie Burn Calculator")

                    weight = st.number_input("Enter your weight (kg)", min_value=1.0, step=0.1)

                    # ---------------- INPUT RUN DATA ----------------
                    c1, c2, c3 = st.columns(3)
                    h = c1.number_input("Hours", 0)
                    m = c2.number_input("Minutes", 0)
                    s = c3.number_input("Seconds", 0, 59)
                    distance = st.number_input("Distance (km)", min_value=0.1, step=0.1)

                    # ---------------- CALCULATE TIME ----------------
                    time_hours = h + m / 60 + s / 3600
                    time_minutes = time_hours * 60

                    if st.button("Calculate Calories (Smart Mode)"):

                        if weight > 0 and time_hours > 0 and distance > 0:

                            # ---------------- PACE ----------------
                            pace = time_minutes / distance  # min/km

                            # ---------------- ESTIMATED INTENSITY (NO BPM) ----------------
                            if pace <= 5:
                                zone = "Maximum (VO2 Max Zone)"
                                met = 12.0
                            elif pace <= 6:
                                zone = "Hard (Anaerobic Zone)"
                                met = 10.0
                            elif pace <= 7.5:
                                zone = "Moderate (Aerobic Zone)"
                                met = 8.3
                            elif pace <= 9:
                                zone = "Light (Fat Burn Zone)"
                                met = 6.0
                            else:
                                zone = "Very Light (Warm Up Zone)"
                                met = 3.5

                            # ---------------- CALORIES ----------------
                            calories = met * weight * time_hours

                            # ---------------- OUTPUT ----------------
                            st.info(f"📊 Estimated Effort Zone: {zone}")
                            st.info(f"🏃 Pace: {pace:.2f} min/km")

                            st.success(f"🔥 Estimated Calories Burned: {calories:.0f} kcal")

                        else:
                            st.error("Please enter valid values")

        # ==================================================
        # 📈 VO2 MAX CALCULATOR (12-MIN COOPER TEST)
        # ==================================================
        with VO_calculator:
            st.markdown("### 📈 VO2 Max Calculator")

            st.info("Enter the distance you ran in 12 minutes to estimate your VO2 Max.")

            # ---------------- Input ----------------
            distance_km = st.number_input(
                "Distance covered in 12 minutes (km)", 
                min_value=0.1, 
                step=0.1, 
                value=2.5, 
                key="vo_distance"
            )

            if st.button("Calculate VO2 Max", key="vo_btn"):
                if distance_km > 0:
                    distance_m = distance_km * 1000  # convert to meters
                    vo2_max = (distance_m - 504.9) / 44.7

                    st.success(f"📈 Estimated VO2 Max: **{vo2_max:.1f} ml/kg/min**")

                    # -------- Interpretation --------
                    if vo2_max >= 60:
                        level = "🟢 Excellent"
                    elif vo2_max >= 50:
                        level = "🟡 Good"
                    elif vo2_max >= 40:
                        level = "🟠 Average"
                    else:
                        level = "🔴 Below Average"

                    st.markdown(f"💡 **Fitness Level:** {level}")

                else:
                    st.warning("Please enter a valid distance.")

        # ==================================================
        # ⚖️ BMI CALCULATOR (CONTROLLED FLOW)
        # ==================================================
        with BMI_calculator:
            st.markdown("### ⚖️ BMI Calculator")

            weight = st.number_input("Weight (kg)", min_value=0.1, step=0.1, value=70.0, key="b_weight")
            height = st.number_input("Height (cm)", min_value=0.1, step=0.1, value=170.0, key="b_height")

            if st.button("Calculate BMI", key="b_btn"):
                if weight > 0 and height > 0:
                    height_m = height / 100  # convert to meters
                    bmi = weight / (height_m ** 2)

                    # -------- Interpretation + Color --------
                    if bmi < 18.5:
                        category = "Underweight"
                        color = "red"
                    elif bmi < 25:
                        category = "Normal weight"
                        color = "green"
                    elif bmi < 30:
                        category = "Overweight"
                        color = "orange"
                    else:
                        category = "Obese"
                        color = "red"   # change to "orange" if you prefer

                    # -------- Styled Output --------
                    st.markdown(
                        f"""
                        <div style="padding:15px;border-radius:10px;background-color:#f9f9f9;">
                            <h2 style="color:{color};margin:0;">⚖️ BMI: {bmi:.1f}</h2>
                            <p style="color:{color};font-size:18px;margin:5px 0;">
                                <b>Category: {category}</b>
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                else:
                    st.warning("Please enter valid weight and height.")

        # ==================================================
        # ⏱️ PACE → SPM → MUSIC BPM CONVERTER (PREMIUM LOCK)
        # ==================================================
        if "is_premium" not in st.session_state:
            st.session_state.is_premium = False

        # ==================================================
        # ⏱️ PACE → SPM → BPM CONVERTER
        # ==================================================
        with pace_spm_bpm_converter:

            st.markdown("### ⏱️ Pace → SPM → BPM Converter")

            # ==================================================
            # 🔐 PREMIUM LOGIN
            # ==================================================
            if not st.session_state.get("is_premium", False):

                st.markdown("""
                <div style="
                    padding:15px;
                    border-radius:10px;
                    background-color:#1E1E1E;
                    color:#ffffff;
                    line-height:1.8;
                ">
                Premium Feature:
                ⏱️ Pace → SPM → BPM Converter<br>
                🔒 Unlock to access full analytics<br>
                🎧 Spotify integration included<br>
                📊 Personalized running insights<br>
                ⚡ Real-time pace conversion
                </div>
                """, unsafe_allow_html=True)
                
                password = st.text_input("Enter Password to unlock Premium", type="password")

                if password == "":
                    st.info("🔒 Premium Feature Locked")

                elif password == PREMIUM_PASSWORD:
                    st.session_state.is_premium = True
                    st.success("🎉 Premium Unlocked!")
                    st.rerun()

                elif password != "":
                    st.error("❌ Wrong Password")
                    st.info("🔒 Premium Feature Locked")

            # ==================================================
            # 🎯 PREMIUM CONTENT (ONLY SHOW IF UNLOCKED)
            # ==================================================
            if st.session_state.is_premium:
                
                # ==================================================
                # Estimate
                # ==================================================

                # ---------------- EXPANDER ----------------
                with st.expander("🔎 How this estimate converter works", expanded=True):
                    st.markdown("""
                    ### 1️⃣ Speed from pace  
                    Speed (km/h) = 60 / Pace (min/km)

                    ### 2️⃣ Stride estimation  
                    Stride length = 0.65 × Height (m)

                    ### 3️⃣ Cadence (SPM)  
                    SPM = 1000 / (Pace × Stride length)

                    ### 4️⃣ Music sync model  
                    BPM = SPM (1:1 rhythm matching)
                    """)

                # ---------------- INPUTS ----------------
                c1, c2, c3 = st.columns(3)

                with c1:
                    pace_min = st.number_input(
                        "Pace (Minutes)",
                        min_value=0,
                        step=1,
                        key="psp_pace_min"
                    )

                with c2:
                    pace_sec = st.number_input(
                        "Pace (Seconds)",
                        min_value=0,
                        max_value=59,
                        step=1,
                        key="psp_pace_sec"
                    )

                with c3:
                    height_cm = st.number_input(
                    "Height (cm)",
                    min_value=0,
                    step=1,
                    key="psp_height"
                )

                # ---------------- CONVERT ----------------
                if st.button("Convert", key="psp_btn"):

                    # Convert inputs
                    pace = pace_min + (pace_sec / 60)
                    height_m = height_cm / 100 if height_cm > 0 else 0

                    if pace > 0 and height_m > 0:

                        # 1️⃣ Speed
                        speed_kmh = 60 / pace

                        # 2️⃣ Stride
                        stride_length = 0.65 * height_m

                        # 3️⃣ Cadence (SPM)
                        spm = 1000 / (pace * stride_length)

                        # 4️⃣ Music BPM
                        bpm = spm

                        # BPM range for music
                        low_bpm = snap_bpm(bpm - 5)
                        high_bpm = snap_bpm(bpm + 5)

                        # ---------------- OUTPUT ----------------
                        st.success(f"""
                        🚀 **Results**

                        - 🏃 Average Pace: {pace_min}:{pace_sec:02d} min/km  
                        - ⚡ Average Speed: {speed_kmh:.2f} km/h  
                        - 📏 Estimate Stride Length: {stride_length:.2f} m  
                        - 👣 Estimate Cadence (SPM): {spm:.0f} steps/min  
                        - 🎵 Estimate BPM: {bpm:.0f} BPM  
                        """)

                        st.info(f"""
                        🎧 Recommended Music Range:

                        **{low_bpm:.0f} BPM → {high_bpm:.0f} BPM**
                        """)

                        # ---------------- MUSIC LINKS ----------------
                        st.markdown("### 🎧 Premium Music Access")

                        c1, c2 = st.columns(2)

                        with c1:
                            st.link_button(
                                f"🎵 {low_bpm:.0f} BPM MIX",
                                f"https://open.spotify.com/search/{int(low_bpm)}%20BPM%20Mix"
                            )

                        with c2:
                            st.link_button(
                                f"🎵 {high_bpm:.0f} BPM MIX",
                                f"https://open.spotify.com/search/{int(high_bpm)}%20BPM%20Mix"
                            )

                    else:
                        st.warning("Please enter valid pace and height.")
            
    # ==================================================
    # LOG RUN
    # ==================================================
    with log:
        st.markdown("### Log Activity")
        d = st.date_input("Date", value=date.today(), key="l_date")
        km = st.number_input("Distance (km)", 0.1, step=0.1, key="l_km")
        c1, c2, c3 = st.columns(3)
        h = c1.number_input("Hours", 0, key="l_h")
        m = c2.number_input("Minutes", 0, key="l_m")
        s = c3.number_input("Seconds", 0, 59, key="l_s")

        if st.button("Save Activity", key="l_btn"):

            t = to_minutes(h, m, s)

            create_run(
                d,
                km,
                round(t, 2),
                round(t / km, 2)
            )

            st.success("Activity saved")

        # ==================================================
        # 🏃 RACE PREDICTOR
        # ==================================================
        with race_predictor:

            st.title("🏃 Race Predictor")
            st.caption("Predict your race performance based on a known result")

            # =====================
            # ⏱️ TIME INPUT
            # =====================
            st.subheader("⏱️ Enter Your Performance")

            t1_col1, t1_col2, t1_col3 = st.columns(3)
            hour_input = t1_col1.number_input("Hours", min_value=0, step=1)
            min_input = t1_col2.number_input("Minutes", min_value=0, step=1)
            sec_input = t1_col3.number_input("Seconds", min_value=0, max_value=59, step=1)

            # =====================
            # 📏 DISTANCE INPUT
            # =====================
            st.subheader("📏 Select Distance")

            d_col1, d_col2 = st.columns(2)

            distance_option = d_col1.selectbox(
                "Distance Type",
                ["5 km", "10 km", "Half Marathon", "Marathon", "Custom"]
            )

            if distance_option == "Custom":
                D1 = d_col2.number_input("Custom Distance (km)", min_value=0.1, value=5.0)
            elif distance_option == "5 km":
                D1 = 5.0
            elif distance_option == "10 km":
                D1 = 10.0
            elif distance_option == "Half Marathon":
                D1 = 21.0975
            else:
                D1 = 42.195

            # Convert to minutes
            T1 = (hour_input * 60) + min_input + (sec_input / 60)

            st.divider()

            # =====================
            # 📊 DISTANCE LIST
            # =====================
            distances = sorted(
                [d for d in range(1, 43) if d not in (21, 42)] + [21.0975, 42.195]
            )

            # =====================
            # 📈 CALCULATION
            # =====================
            if T1 > 0:

                data = []

                for D2 in distances:

                    # Fix: same distance → same time
                    if abs(D2 - D1) <= 0.1:
                        T2 = T1
                    else:
                        T2 = T1 * (D2 / D1) ** 1.06

                    pace = T2 / D2

                    data.append([
                        get_distance_label(D2),
                        format_time(T2),
                        format_pace(pace)
                    ])

                df = pd.DataFrame(data, columns=[
                    "Distance",
                    "Finish Time",
                    "Pace (/km)"
                ])

                # =====================
                # 📋 OUTPUT TABLE
                # =====================
                st.subheader("📊 Predicted Results")

                df_display = df.reset_index(drop=True)

                st.dataframe(df_display, use_container_width=True, hide_index=True)

            else:
                st.info("Enter your time to see predictions")

    # ==================================================
    # DASHBOARD
    # ==================================================
    with dash:
        df = read_runs()
        if df.empty:
            st.info("No activities yet.")
        else:
            df["date"] = pd.to_datetime(df["date"], dayfirst=True)

            # ------------------ Dashboard Cards ------------------
            c1, c2, c3, c4 = st.columns(4)
            for col, val, label in [
                (c1, len(df), "Runs"),
                (c2, f"{df.distance_km.sum():.1f}", "Total Km"),
                (c3, format_pace(df.pace_min_per_km.min()), "Best Pace"),
                (c4, format_pace(df.pace_min_per_km.mean()), "Avg Pace")
            ]:
                col.markdown(
                    f"<div class='card'><div class='metric-value'>{val}</div><div class='metric-label'>{label}</div></div>",
                    unsafe_allow_html=True
                )

            # ------------------ Add gap before chart tabs ------------------
            st.markdown("<br><br>", unsafe_allow_html=True)  # Two line breaks for spacing

            # ------------------ Chart Tabs ------------------
            perf_tab, pace_tab = st.tabs(["Performance Trend", "Pace Trend"])

            # Prepare formatted Pace column for tooltips
            df["Pace"] = df["pace_min_per_km"].apply(format_pace)

            with perf_tab:
                st.markdown("### Distance over Time")
                chart_perf = alt.Chart(df).mark_line(point=True, color="#ff9800").encode(
                    x="date:T",
                    y="distance_km:Q",
                    tooltip=["date:T", "distance_km", "Pace"]
                ).properties(height=420, width="container")
                st.altair_chart(chart_perf, width='stretch')

            with pace_tab:
                st.markdown("### Pace over Time")
                chart_pace = alt.Chart(df).mark_line(point=True, color="#ff6a00").encode(
                    x="date:T",
                    y="pace_min_per_km:Q",
                    tooltip=["date:T", "Pace", "distance_km"]
                ).properties(height=420, width="container")
                st.altair_chart(chart_pace, width='stretch')

            # ------------------ Monthly Runs Table ------------------
            st.markdown("<br>", unsafe_allow_html=True)  # Optional: small gap above table
            st.markdown("### 📋 Monthly Runs Data")

            from calendar import month_name
            current_month = date.today().month
            current_year = date.today().year
            month_df = df[(df["date"].dt.month == current_month) & (df["date"].dt.year == current_year)]

            if month_df.empty:
                st.info("No runs logged this month.")
            else:
                # Format Date, Time, and Pace
                month_df_display = month_df.copy()
                month_df_display["Date"] = month_df_display["date"].dt.strftime("%d/%m/%Y")
                month_df_display["Time"] = month_df_display["time_min"].apply(lambda t: f"{int(t//60)}h {int(t%60)}m")
                month_df_display["Pace"] = month_df_display["pace_min_per_km"].apply(format_pace)
                
                # Select and rename columns
                month_df_display = month_df_display[["Date", "distance_km", "Time", "Pace"]]
                month_df_display = month_df_display.rename(columns={"distance_km": "Distance (km)"})

                # Reset index starting from 1
                month_df_display.index = range(1, len(month_df_display)+1)
                month_df_display.index.name = "No."

                st.dataframe(month_df_display, width='stretch')

    #=================================================
    # EVENT COUNTDOWN
    # =================================================
    with event:

        st.markdown("### 🏁 Running Event Countdown")

        df_events = load_events()

        # ---------------- Add Event ----------------
        st.markdown("#### ➕ Add Event")

        name = st.text_input("Event Name")
        event_date = st.date_input("Event Date")
        desc = st.text_area("Description")

        if st.button("Save Event"):

            new_id = 1 if df_events.empty else df_events["id"].max() + 1

            new_event = {
                "id": new_id,
                "name": name,
                "date": event_date.strftime("%Y-%m-%d"),
                "description": desc
            }

            df_events = pd.concat([df_events, pd.DataFrame([new_event])], ignore_index=True)
            save_events(df_events)

            st.success("Event Added!")
            st.rerun()

        st.markdown("---")

        # ---------------- Show Events ----------------
        st.markdown("### 📅 Upcoming Events")

        if df_events.empty:
            st.info("No events added yet.")

        else:

            today = date.today()

            for i, row in df_events.iterrows():

                event_date = pd.to_datetime(row["date"]).date()
                days_left = (event_date - today).days

                if days_left > 0:
                    countdown = f"{days_left} days left"
                elif days_left == 0:
                    countdown = "🎉 TODAY!"
                else:
                    countdown = f"{abs(days_left)} days ago"

                st.markdown(
                    f"""
                    <div class="card">
                        <h4>{row['name']}</h4>
                        <p><b>Date:</b> {event_date}</p>
                        <p>{row['description']}</p>
                        <p style="color:#ff9800;font-weight:bold;">⏳ {countdown}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                col1, col2 = st.columns(2)

                # -------- Edit --------
                with col1:
                    if st.button(f"Edit"):

                        st.session_state["edit_event"] = row["id"]

                # -------- Delete --------
                with col2:
                    if st.button(f"Delete"):

                        df_events = df_events[df_events["id"] != row["id"]]
                        save_events(df_events)

                        st.warning("Event Deleted")
                        st.rerun()

            # ---------------- Edit Mode ----------------
            if "edit_event" in st.session_state:

                edit_id = st.session_state["edit_event"]
                edit_row = df_events[df_events["id"] == edit_id].iloc[0]

                st.markdown("---")
                st.markdown("### ✏️ Edit Event")

                new_name = st.text_input("Event Name", value=edit_row["name"], key="edit_name")

                new_date = st.date_input(
                    "Event Date",
                    value=pd.to_datetime(edit_row["date"]).date(),
                    key="edit_date"
                )

                new_desc = st.text_area(
                    "Description",
                    value=edit_row["description"],
                    key="edit_desc"
                )

                if st.button("Update Event"):

                    df_events.loc[df_events["id"] == edit_id, "name"] = new_name
                    df_events.loc[df_events["id"] == edit_id, "date"] = new_date.strftime("%Y-%m-%d")
                    df_events.loc[df_events["id"] == edit_id, "description"] = new_desc

                    save_events(df_events)

                    del st.session_state["edit_event"]

                    st.success("Event Updated!")
                    st.rerun()

    # ==================================================
    # CALENDAR VIEW - Proper Table + Monthly Summary
    # ==================================================
    with calendar:
        st.markdown("### 📅 Monthly Training Calendar")
        df = read_runs()
        
        if df.empty:
            st.info("No activities logged yet.")
        else:
            df["date"] = pd.to_datetime(df["date"], dayfirst=True)
            from calendar import month_name, monthrange
            
            # Month / Year selector
            c1, c2 = st.columns([1, 1])
            with c1:
                year = st.selectbox("Year", sorted(df["date"].dt.year.unique(), reverse=True), index=0, key="cal_year")
            with c2:
                month = st.selectbox("Month", list(month_name)[1:], index=date.today().month-1, key="cal_month")
            month_num = list(month_name).index(month)
            
            # Filter runs for selected month
            month_df = df[(df["date"].dt.year == year) & (df["date"].dt.month == month_num)]

            # ------------------ Monthly Summary ------------------
            total_km = month_df["distance_km"].sum()
            avg_km = month_df["distance_km"].mean() if not month_df.empty else 0
            avg_pace = month_df["pace_min_per_km"].mean() if not month_df.empty else 0

            st.markdown(f"""
            <div class="card" style="display:flex;justify-content:space-around;margin-bottom:15px;">
                <div><b>Total KM:</b> {total_km:.1f}</div>
                <div><b>Avg KM / Run:</b> {avg_km:.2f}</div>
                <div><b>Avg Pace:</b> {format_pace(avg_pace) if not month_df.empty else '-'}</div>
            </div>
            """, unsafe_allow_html=True)

            # ------------------ Table Calendar ------------------
            first_weekday, days_in_month = monthrange(year, month_num)
            weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

            # Start HTML table
            table_html = "<table style='width:100%;border-collapse:collapse;'>"
            
            # Weekday header
            table_html += "<tr>"
            for wd in weekdays:
                table_html += f"<th style='padding:5px;text-align:center;border-bottom:1px solid #555;'>{wd}</th>"
            table_html += "</tr>"

            # Fill in days
            day_counter = 1 - ((first_weekday - 0) % 7)  # Align Monday as 0
            while day_counter <= days_in_month:
                table_html += "<tr>"
                for i in range(7):
                    if day_counter < 1 or day_counter > days_in_month:
                        # Empty cell
                        table_html += "<td style='padding:10px;border:1px solid #333;background:rgba(255,255,255,0.05);opacity:0.1;'></td>"
                    else:
                        d = pd.Timestamp(year=year, month=month_num, day=day_counter)
                        day_runs = month_df[month_df["date"] == d]
                        if not day_runs.empty:
                            km = day_runs["distance_km"].sum()
                            pace = format_pace(day_runs["pace_min_per_km"].mean())
                            table_html += f"<td style='padding:10px;border:1px solid #333;background:rgba(255,255,255,0.05);text-align:center;'><b>{day_counter}</b><br>{km:.1f} km<br>{pace} min/km</td>"
                        else:
                            table_html += f"<td style='padding:10px;border:1px solid #333;background:rgba(255,255,255,0.05);opacity:0.35;text-align:center;'><b>{day_counter}</b><br>—</td>"
                    day_counter += 1
                table_html += "</tr>"
            table_html += "</table>"

            st.markdown(table_html, unsafe_allow_html=True)

    # ==================================================
    # BODY MEASUREMENT TAB - LINK TO 8501
    # ==================================================
    # with body_measure:   # NEW TAB ADDED
    #     st.markdown("### 🧍 Go to Advanced Body Measurement System")
    #     st.markdown(
    #         """
    #         Click the button below to open your **Advanced Body Measurement** app.
    #         """)
        
    #     # Styled button consistent with your theme
    #     st.markdown(
    #         '<a href="http://localhost:8501/" target="_blank">'
    #         '<button style="background: linear-gradient(90deg, #ff6a00, #ff9800);'
    #         'color:white;padding:12px 24px;border:none;border-radius:14px;font-weight:700;'
    #         'font-size:16px;box-shadow: 0 8px 20px #00000080;">'
    #         'Open Advanced Body Measurement</button></a>',
    #         unsafe_allow_html=True
    #     )

    # ==================================================
    # NOTES TAB - Add / Edit / Delete / Search Notes
    # ==================================================
    with notes:
        st.markdown("### 📝 Training Notes")
        st.markdown("Keep track of thoughts, injuries, goals, or reflections.")

        notes_df = load_notes()

        # ------------------ Add New Note ------------------
        with st.expander("➕ Add New Note", expanded=True):
            with st.form("add_note_form", clear_on_submit=True):
                note_title = st.text_input("Title")
                note_content = st.text_area("Note", height=120)

                submitted = st.form_submit_button("Save Note")

            if submitted:
                if note_title.strip() == "" or note_content.strip() == "":
                    st.warning("Title and note cannot be empty.")
                else:
                    conn = get_connection()
                    cursor = conn.cursor()

                    # ✅ get next valid ID from SQL (not dataframe)
                    cursor.execute('SELECT COALESCE(MAX(id), 0) + 1 FROM "Notes"')
                    new_id = cursor.fetchone()[0]
                    cursor.execute("""
                        INSERT INTO Notes (id, date, title, content, tags, user_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    new_id,
                    date.today().strftime("%Y-%m-%d"),
                    note_title,
                    note_content,
                    None,
                    st.session_state.user_db_id
                    )

                    conn.commit()
                    conn.close()

                    st.success("Note saved ✔️")
                    st.rerun()

        st.divider()

        # ------------------ Search Notes ------------------
        search_query = st.text_input(
            "🔍 Search notes",
            placeholder="Search by title or content"
        )

        filtered_df = notes_df
        if search_query.strip():
            filtered_df = notes_df[
                notes_df["title"].str.contains(search_query, case=False, na=False) |
                notes_df["content"].str.contains(search_query, case=False, na=False)
            ]

        # ------------------ Existing Notes ------------------
        if filtered_df.empty:
            st.info("No notes found.")
        else:
            for idx, row in filtered_df.iterrows():
                with st.expander(f"📌 {row['title']}  •  {row['date']}"):
                    edited_title = st.text_input(
                        "Edit Title",
                        value=row["title"],
                        key=f"title_{row['id']}"
                    )
                    edited_content = st.text_area(
                        "Edit Note",
                        value=row["content"],
                        height=120,
                        key=f"content_{row['id']}"
                    )

                    c1, c2 = st.columns(2)

                    # Update note
                    if c1.button("💾 Update", key=f"update_{row['id']}"):
                        notes_df.loc[idx, "title"] = edited_title
                        notes_df.loc[idx, "content"] = edited_content
                        save_notes(notes_df)
                        st.success("Note updated ✔️")
                        st.rerun()

                    # Delete note
                    if c2.button("🗑️ Delete", key=f"delete_{row['id']}"):
                        notes_df = notes_df.drop(idx).reset_index(drop=True)
                        save_notes(notes_df)
                        st.warning("Note deleted")
                        st.rerun()
