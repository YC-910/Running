import streamlit as st
import pandas as pd
from datetime import date
import os
import altair as alt

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="Run Performance",
    layout="wide",
    initial_sidebar_state="collapsed"
)

FILE = "runs.csv"
NOTES_FILE = "notes.csv"

# ==================================================
# Helpers
# ==================================================
def to_minutes(h, m, s):
    return h * 60 + m + s / 60

def load_runs():
    if os.path.exists(FILE):
        return pd.read_csv(FILE)
    return pd.DataFrame(columns=["date", "distance_km", "time_min", "pace_min_per_km"])

def save_run(run):
    df = load_runs()
    df = pd.concat([df, pd.DataFrame([run])], ignore_index=True)
    df.to_csv(FILE, index=False)

def format_pace(p):
    m = int(p)
    s = int(round((p - m) * 60))
    return f"{m}:{s:02d}"

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
# Notes Helpers
# ==================================================
def load_notes():
    if os.path.exists(NOTES_FILE):
        return pd.read_csv(NOTES_FILE)
    return pd.DataFrame(columns=["id", "date", "title", "content"])

def save_notes(df):
    df.to_csv(NOTES_FILE, index=False)

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
    <h2>🏃 Run Performance</h2>
    <p>Garmin-level insights. Strava-grade aesthetics.</p>
</div>
""", unsafe_allow_html=True)

# ==================================================
# MAIN TABS
# ==================================================
tools, log, dash, calendar, body_measure, notes_tab = st.tabs([
    "⚡ Tools",
    "📝 Log Run",
    "📊 Performance",
    "📅 Calendar",
    "🏋️‍♂️ Body Measurement",
    "📝 Notes"
])

# ==================================================
# TOOLS
# ==================================================
with tools:
    pace_converter, speed_converter = st.tabs([
        "🧮 Pace Converter",
        "🚀 Speed Converter"
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
            p = st.number_input(
                "Pace (min/km)", 0.1, step=0.1, value=5.0, key="d_p"
            )

            c1, c2, c3 = st.columns(3)
            h = c1.number_input("Hours", 0, key="d_h")
            m = c2.number_input("Minutes", 0, key="d_m")
            s = c3.number_input("Seconds", 0, 59, key="d_s")

            if st.button("Calculate Distance", key="d_btn"):
                t = to_minutes(h, m, s)
                st.success(f"{t / p:.2f} km")

        # ---------------- Time ----------------
        with time:
            st.markdown("### Time Calculator")
            d = st.number_input(
                "Distance (km)", 0.1, step=0.1, value=5.0, key="t_d"
            )
            p = st.number_input(
                "Pace (min/km)", 0.1, step=0.1, value=5.0, key="t_p"
            )

            if st.button("Calculate Time", key="t_btn"):
                t = d * p
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
        t = to_minutes(h,m,s)
        save_run({
            "date": d.strftime("%d/%m/%Y"),
            "distance_km": km,
            "time_min": round(t,2),
            "pace_min_per_km": round(t/km,2)
        })
        st.success("Activity saved")

# ==================================================
# DASHBOARD
# ==================================================
with dash:
    df = load_runs()
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


# ==================================================
# CALENDAR VIEW - Proper Table + Monthly Summary
# ==================================================
with calendar:
    st.markdown("### 📅 Monthly Training Calendar")
    df = load_runs()
    
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
with body_measure:   # NEW TAB ADDED
    st.markdown("### 🧍 Go to Advanced Body Measurement System")
    st.markdown(
        """
        Click the button below to open your **Advanced Body Measurement** app.
        """)
    
    # Styled button consistent with your theme
    st.markdown(
        '<a href="http://localhost:8501/" target="_blank">'
        '<button style="background: linear-gradient(90deg, #ff6a00, #ff9800);'
        'color:white;padding:12px 24px;border:none;border-radius:14px;font-weight:700;'
        'font-size:16px;box-shadow: 0 8px 20px #00000080;">'
        'Open Advanced Body Measurement</button></a>',
        unsafe_allow_html=True
    )

# ==================================================
# NOTES TAB - Add / Edit / Delete / Search Notes
# ==================================================
with notes_tab:
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
                new_note = {
                    "id": int(notes_df["id"].max() + 1) if not notes_df.empty else 1,
                    "date": date.today().strftime("%d/%m/%Y"),
                    "title": note_title,
                    "content": note_content
                }
                notes_df = pd.concat(
                    [notes_df, pd.DataFrame([new_note])],
                    ignore_index=True
                )
                save_notes(notes_df)
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
