"""
Causefleet Executive Command Center & Intelligent Smart Companion
International Humanitarian Food, Water, and Education Practicum (BUAN 6390)
- Dual-Mode Ingestion: Calibrated $30M Demo Generator OR Custom CSV Dataset Upload
- Dynamic Giving Tier Categorization & Auto-Profile Generation
- Interactive Multi-Year Cross-Filtering & What-If Forecasting Simulator
- Dynamic Ad-Hoc SQL Agent Companion with Query Inspection
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import random
import re
import io
from datetime import datetime

DB_FILE = "causefleet_demo.db"

# -----------------------------------------------------------------------------
# 1. DATABASE SETUP
# -----------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    conn = get_db()
    try:
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS donors (
                donor_id TEXT PRIMARY KEY,
                name TEXT,
                donor_type TEXT,
                giving_tier TEXT,
                city TEXT,
                state TEXT,
                first_gift_date TEXT,
                total_lifetime_value REAL,
                assigned_officer TEXT,
                retention_status TEXT
            )""")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS gifts (
                gift_id TEXT PRIMARY KEY,
                donor_id TEXT,
                gift_date TEXT,
                gift_year INTEGER,
                gift_month INTEGER,
                amount REAL,
                channel TEXT,
                campaign TEXT,
                FOREIGN KEY (donor_id) REFERENCES donors(donor_id)
            )""")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS impact_metrics (
                metric_id TEXT PRIMARY KEY,
                metric_name TEXT,
                unit_cost REAL,
                five_year_goal INTEGER,
                achieved_to_date INTEGER,
                sector TEXT
            )""")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS storylines (
                story_id TEXT PRIMARY KEY,
                title TEXT,
                target_entity TEXT,
                summary TEXT,
                verification_query TEXT
            )""")
    finally:
        conn.close()

# -----------------------------------------------------------------------------
# 2. INGESTION ENGINES: SYNTHETIC GENERATOR & CUSTOM CSV LOADER
# -----------------------------------------------------------------------------
def assign_tier(amount):
    if amount >= 100000:
        return "$100,000+"
    elif amount >= 10000:
        return "$10,000 - $99,999"
    elif amount >= 1000:
        return "$1,000 - $9,999"
    elif amount >= 100:
        return "$100 - $999"
    else:
        return "Under $100"

def ingest_custom_dataset(df_upload):
    """
    Ingests user-uploaded gifts/donors CSV, auto-calculates constituent metrics,
    giving tiers, and populates SQLite tables.
    """
    conn = get_db()
    try:
        with conn:
            conn.execute("DELETE FROM gifts")
            conn.execute("DELETE FROM donors")
            conn.execute("DELETE FROM storylines")

            # Clean and normalize columns
            df = df_upload.copy()
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

            # Enforce minimal required fields with smart fallbacks
            if 'donor_id' not in df.columns:
                df['donor_id'] = [f"D-CUST-{i+1}" for i in range(len(df))]
            if 'donor_name' not in df.columns:
                df['donor_name'] = df.get('name', df['donor_id'])
            if 'amount' not in df.columns:
                st.error("Uploaded CSV must have an 'amount' column.")
                return False
            if 'gift_date' not in df.columns:
                df['gift_date'] = datetime.today().strftime('%Y-%m-%d')

            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
            df['gift_date'] = pd.to_datetime(df['gift_date'], errors='coerce').fillna(pd.Timestamp('2024-01-01'))
            df['gift_year'] = df['gift_date'].dt.year
            df['gift_month'] = df['gift_date'].dt.month
            df['gift_date_str'] = df['gift_date'].dt.strftime('%Y-%m-%d')
            
            df['channel'] = df.get('channel', 'Online Portal')
            df['campaign'] = df.get('campaign', 'General Humanitarian Fund')
            df['donor_type'] = df.get('donor_type', 'Individual')
            df['city'] = df.get('city', 'Dallas')
            df['state'] = df.get('state', 'TX')
            df['assigned_officer'] = df.get('assigned_officer', 'Unassigned')

            # Aggregate donors
            donor_agg = df.groupby('donor_id').agg(
                name=('donor_name', 'first'),
                donor_type=('donor_type', 'first'),
                city=('city', 'first'),
                state=('state', 'first'),
                first_gift_date=('gift_date_str', 'min'),
                total_lifetime_value=('amount', 'sum'),
                assigned_officer=('assigned_officer', 'first')
            ).reset_index()

            donor_agg['giving_tier'] = donor_agg['total_lifetime_value'].apply(assign_tier)
            donor_agg['retention_status'] = 'Active'

            # Build insert tuples
            donors_data = [
                (r['donor_id'], r['name'], r['donor_type'], r['giving_tier'], r['city'], r['state'], 
                 r['first_gift_date'], float(r['total_lifetime_value']), r['assigned_officer'], r['retention_status'])
                for _, r in donor_agg.iterrows()
            ]

            gifts_data = [
                (f"G-CUST-{i+1}", r['donor_id'], r['gift_date_str'], int(r['gift_year']), int(r['gift_month']), 
                 float(r['amount']), str(r['channel']), str(r['campaign']))
                for i, r in df.iterrows()
            ]

            conn.executemany("INSERT INTO donors VALUES (?,?,?,?,?,?,?,?,?,?)", donors_data)
            conn.executemany("INSERT INTO gifts VALUES (?,?,?,?,?,?,?,?)", gifts_data)
            
            # Default impact metrics if empty
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM impact_metrics")
            if cur.fetchone()[0] == 0:
                conn.executemany("INSERT INTO impact_metrics VALUES (?,?,?,?,?,?)", [
                    ("IMP-01", "People Receiving Food & Water", 42.50, 400000, 318200, "Food & Water"),
                    ("IMP-02", "People with Access to Education", 115.00, 100000, 84650, "Education"),
                    ("IMP-03", "Developing Countries Served", 185000.00, 35, 31, "Infrastructure")
                ])
        return True
    finally:
        conn.close()

def generate_production_grade_dataset(target_total=30000000.0):
    conn = get_db()
    try:
        with conn:
            conn.execute("DELETE FROM gifts")
            conn.execute("DELETE FROM donors")
            conn.execute("DELETE FROM impact_metrics")
            conn.execute("DELETE FROM storylines")

            first_names = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", 
                           "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
                           "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa"]
            last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", 
                          "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas"]
            corp_names = ["Apex Global Technologies", "Meridian Trust", "Beacon Logistics", "Horizon Energy Corp",
                          "Vanguard Holdings", "BlueRock Capital", "Sterling Financial", "Pinnacle Health Partners"]
            cities = [("Dallas", "TX"), ("Austin", "TX"), ("Houston", "TX"), ("New York", "NY"), 
                      ("Chicago", "IL"), ("San Francisco", "CA"), ("Seattle", "WA"), ("Denver", "CO")]
            
            officers = ["Sarah Jenkins", "Marcus Vance", "Elena Rostova", "Devon Brooks"]
            channels = ["Direct Mail", "Online Portal", "Major Gifts Wire", "Corporate Grant", "Annual Gala", "Peer-to-Peer"]
            campaigns = ["Clean Water Initiative", "Global Food Relief", "Girls Education Fund", "Emergency Disaster Response"]

            donors = []
            gifts = []
            running_total = 0.0
            donor_counter = 1000
            gift_counter = 50000

            # Storylines (Charter Section 4)
            donors.append(("D-STORY-01", "Eleanor Vance", "Individual", "$100,000+", "Austin", "TX", "2022-01-15", 350000.0, "Sarah Jenkins", "Lapsed"))
            gifts.append(("G-STORY-01A", "D-STORY-01", "2022-03-10", 2022, 3, 150000.0, "Major Gifts Wire", "Clean Water Initiative"))
            gifts.append(("G-STORY-01B", "D-STORY-01", "2023-04-12", 2023, 4, 120000.0, "Major Gifts Wire", "Clean Water Initiative"))
            gifts.append(("G-STORY-01C", "D-STORY-01", "2024-05-18", 2024, 5, 80000.0, "Major Gifts Wire", "Clean Water Initiative"))
            running_total += 350000.0

            donors.append(("D-STORY-02", "Apex Global Foundation", "Corporation", "$100,000+", "New York", "NY", "2024-09-01", 1250000.0, "Marcus Vance", "Active"))
            gifts.append(("G-STORY-02A", "D-STORY-02", "2024-09-05", 2024, 9, 1250000.0, "Corporate Grant", "Emergency Disaster Response"))
            running_total += 1250000.0

            donors.append(("D-STORY-03", "Jonathan Miller", "Individual", "$100 - $999", "Seattle", "WA", "2023-11-20", 250.0, "Unassigned", "Lapsed"))
            gifts.append(("G-STORY-03A", "D-STORY-03", "2023-11-20", 2023, 11, 250.0, "Online Portal", "Global Food Relief"))
            running_total += 250.0

            tier_specs = [
                {"tier": "$100,000+", "count": 24, "min_g": 100000, "max_g": 650000, "type_dist": ["Corporation", "Individual"]},
                {"tier": "$10,000 - $99,999", "count": 180, "min_g": 12000, "max_g": 75000, "type_dist": ["Individual", "Corporation"]},
                {"tier": "$1,000 - $9,999", "count": 820, "min_g": 1200, "max_g": 8500, "type_dist": ["Individual"]},
                {"tier": "$100 - $999", "count": 2200, "min_g": 150, "max_g": 850, "type_dist": ["Individual"]},
                {"tier": "Under $100", "count": 4800, "min_g": 15, "max_g": 85, "type_dist": ["Individual"]},
            ]

            month_weights = [0.06, 0.05, 0.06, 0.07, 0.06, 0.05, 0.05, 0.07, 0.09, 0.08, 0.16, 0.20]

            for spec in tier_specs:
                for _ in range(spec["count"]):
                    donor_counter += 1
                    d_id = f"D-{donor_counter}"
                    d_type = random.choice(spec["type_dist"])
                    name = f"{random.choice(corp_names)} {random.choice(['Group', 'Ventures', 'Intl'])}" if d_type == "Corporation" else f"{random.choice(first_names)} {random.choice(last_names)}"
                    city, state = random.choice(cities)
                    officer = random.choice(officers) if spec["tier"] in ["$100,000+", "$10,000 - $99,999"] else "Unassigned"
                    
                    num_gifts = 1 if spec["tier"] == "Under $100" else random.randint(1, 3)
                    donor_total = 0.0
                    first_date = None

                    for _ in range(num_gifts):
                        gift_counter += 1
                        g_id = f"G-{gift_counter}"
                        g_year = random.choice([2022, 2023, 2024, 2025, 2026])
                        g_month = random.choices(range(1, 13), weights=month_weights)[0]
                        if g_year == 2026 and g_month > 8:
                            g_month = random.randint(1, 8)
                        
                        gift_date = f"{g_year}-{g_month:02d}-{random.randint(1, 28):02d}"
                        if first_date is None or gift_date < first_date:
                            first_date = gift_date

                        base_amt = round(random.uniform(spec["min_g"], spec["max_g"]) / num_gifts, 2)
                        donor_total += base_amt
                        running_total += base_amt
                        
                        chan = random.choice(["Major Gifts Wire", "Corporate Grant"]) if spec["tier"] == "$100,000+" else random.choice(channels)
                        gifts.append((g_id, d_id, gift_date, g_year, g_month, base_amt, chan, random.choice(campaigns)))

                    donors.append((d_id, name, d_type, spec["tier"], city, state, first_date, donor_total, officer, "Active"))

            variance = target_total - running_total
            anchor_id = "D-ANCHOR-CORP"
            donors.append((anchor_id, "The Global Humanitarian Foundation", "Corporation", "$100,000+", "New York", "NY", "2026-02-15", abs(variance), "Marcus Vance", "Active"))
            gifts.append(("G-ANCHOR-9999", anchor_id, "2026-02-15", 2026, 2, variance, "Corporate Grant", "Global Food Relief"))

            impact_records = [
                ("IMP-01", "People Receiving Food & Water", 42.50, 400000, 318200, "Food & Water"),
                ("IMP-02", "People with Access to Education", 115.00, 100000, 84650, "Education"),
                ("IMP-03", "Developing Countries Served", 185000.00, 35, 31, "Infrastructure")
            ]

            storylines = [
                ("S-01", "Declining Loyal Major Donor", "Eleanor Vance", "Major individual reduced annual gifts from $150k in 2022 to $80k in 2024 and lapsed in 2025.", "SELECT * FROM gifts WHERE donor_id='D-STORY-01'"),
                ("S-02", "Emergency Response Outlier", "Apex Global Foundation", "Surged $1.25M single grant in Sep 2024 under Emergency Disaster Response.", "SELECT * FROM gifts WHERE donor_id='D-STORY-02'"),
                ("S-03", "First-Time Donor Lapsed", "Jonathan Miller", "Entered via online food relief campaign in 2023, never made a second gift.", "SELECT * FROM donors WHERE donor_id='D-STORY-03'")
            ]

            conn.executemany("INSERT INTO donors VALUES (?,?,?,?,?,?,?,?,?,?)", donors)
            conn.executemany("INSERT INTO gifts VALUES (?,?,?,?,?,?,?,?)", gifts)
            conn.executemany("INSERT INTO impact_metrics VALUES (?,?,?,?,?,?)", impact_records)
            conn.executemany("INSERT INTO storylines VALUES (?,?,?,?,?)", storylines)
    finally:
        conn.close()

# -----------------------------------------------------------------------------
# 3. DYNAMIC SMART COMPANION AGENT
# -----------------------------------------------------------------------------
def run_dynamic_agent(user_prompt: str) -> dict:
    p = user_prompt.strip().lower()
    conn = get_db()
    try:
        if "eleanor vance" in p or "declining donor" in p:
            q = "SELECT g.gift_date, g.amount, g.campaign, d.assigned_officer FROM gifts g JOIN donors d ON g.donor_id=d.donor_id WHERE d.name LIKE '%Eleanor Vance%' ORDER BY g.gift_date ASC"
            df = pd.read_sql_query(q, conn)
            if not df.empty:
                gifts_str = "\n".join([f"- {r['gift_date']}: ${r['amount']:,.2f} ({r['campaign']})" for _, r in df.iterrows()])
                return {
                    "answer": f"[Certain] **Eleanor Vance Giving History (Planted Storyline S-01)**:\n{gifts_str}\n\n**Officer**: {df['assigned_officer'].iloc[0]}\n**Analysis**: Contributions dropped from $150k (2022) to $120k (2023) and $80k (2024), lapsing thereafter[cite: 2].",
                    "sql": q
                }

        where_clauses = []
        params = []
        
        # Extract years dynamically from query
        year_match = re.search(r'\b(20[1-3][0-9])\b', p)
        if year_match:
            where_clauses.append("g.gift_year = ?")
            params.append(int(year_match.group(1)))

        where_stmt = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        if any(w in p for w in ["top donor", "largest donor", "biggest donor", "top 5", "top 10"]):
            limit = 10 if "10" in p else 5
            q = f"SELECT d.name, d.donor_type, d.city, d.state, SUM(g.amount) as total_given, COUNT(g.gift_id) as gifts FROM donors d JOIN gifts g ON d.donor_id = g.donor_id {where_stmt} GROUP BY d.donor_id ORDER BY total_given DESC LIMIT {limit}"
            df = pd.read_sql_query(q, conn, params=params)
            lines = "\n".join([f"{i+1}. **{r['name']}** ({r['donor_type']} • {r['city']}, {r['state']}): **${r['total_given']:,.2f}** ({r['gifts']} gifts)" for i, r in df.iterrows()])
            return {"answer": f"[Certain] **Top {len(df)} Donors Meeting Criteria**[cite: 1, 2]:\n{lines}", "sql": q}

        if any(w in p for w in ["impact", "people", "food", "water", "education", "goal"]):
            q = "SELECT metric_name, five_year_goal, achieved_to_date, unit_cost FROM impact_metrics"
            df = pd.read_sql_query(q, conn)
            lines = "\n".join([f"- **{r['metric_name']}**: {r['achieved_to_date']:,} of {r['five_year_goal']:,} ({(r['achieved_to_date']/r['five_year_goal'])*100:.1f}%) at ${r['unit_cost']:.2f}/unit" for _, r in df.iterrows()])
            return {"answer": f"[Certain] **Five-Year Impact Progress vs Objectives**[cite: 1, 8]:\n{lines}", "sql": q}

        q = f"SELECT SUM(g.amount) as total_amt, COUNT(g.gift_id) as gift_cnt, COUNT(DISTINCT g.donor_id) as donor_cnt, AVG(g.amount) as avg_amt FROM gifts g JOIN donors d ON g.donor_id = d.donor_id {where_stmt}"
        df = pd.read_sql_query(q, conn, params=params)
        tot = df['total_amt'].iloc[0] or 0.0
        gc = df['gift_cnt'].iloc[0] or 0
        dc = df['donor_cnt'].iloc[0] or 0
        avg = df['avg_amt'].iloc[0] or 0.0
        
        ctx_desc = f" matching specified parameters ({', '.join(map(str, params))})" if params else " across the loaded dataset"
        return {
            "answer": f"[Certain] **Query Result**{ctx_desc}:\n- **Total Revenue**: **${tot:,.2f}**\n- **Gift Transactions**: **{gc:,}**\n- **Distinct Donors**: **{dc:,}**\n- **Average Gift**: **${avg:,.2f}**",
            "sql": q
        }
    finally:
        conn.close()

# -----------------------------------------------------------------------------
# 4. STREAMLIT APPLICATION UI
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Causefleet Executive Suite", layout="wide", initial_sidebar_state="expanded")
init_db()

# --- SIDEBAR: DATA CONTROLS & CSV UPLOADER ---
st.sidebar.title("Operational Controls")

st.sidebar.subheader("Option A: Load $30M Synthetic Demo")
if st.sidebar.button("Generate $30M Benchmark Dataset"):
    with st.spinner("Generating calibrated $30,000,000 dataset..."):
        generate_production_grade_dataset(30000000.0)
    st.sidebar.success("Generated $30M Benchmark Dataset!")

st.sidebar.markdown("---")
st.sidebar.subheader("Option B: Upload Custom Dataset")
uploaded_file = st.sidebar.file_uploader("Upload CSV File", type=["csv"])

if uploaded_file is not None:
    if st.sidebar.button("Process & Load Uploaded CSV"):
        try:
            df_up = pd.read_csv(uploaded_file)
            with st.spinner("Ingesting records, computing tiers, and populating tables..."):
                ok = ingest_custom_dataset(df_up)
            if ok:
                st.sidebar.success(f"Loaded {len(df_up):,} custom gifts successfully!")
                st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error reading CSV: {e}")

# Sample CSV template download
sample_csv = io.StringIO()
sample_df = pd.DataFrame({
    "donor_id": ["D-101", "D-102", "D-103", "D-104"],
    "donor_name": ["Apex Logistics", "Sarah Connors", "David Sterling", "Global Green Fund"],
    "donor_type": ["Corporation", "Individual", "Individual", "Foundation"],
    "amount": [125000.0, 450.0, 15000.0, 250000.0],
    "gift_date": ["2024-03-12", "2024-06-15", "2025-01-20", "2026-02-10"],
    "channel": ["Major Gifts Wire", "Online Portal", "Direct Mail", "Corporate Grant"],
    "campaign": ["Clean Water Initiative", "Global Food Relief", "Girls Education Fund", "Emergency Disaster Response"],
    "assigned_officer": ["Marcus Vance", "Unassigned", "Sarah Jenkins", "Devon Brooks"],
    "city": ["Dallas", "Austin", "New York", "Seattle"],
    "state": ["TX", "TX", "NY", "WA"]
})
sample_df.to_csv(sample_csv, index=False)
st.sidebar.download_button(
    label="Download Sample CSV Template",
    data=sample_csv.getvalue(),
    file_name="causefleet_sample_template.csv",
    mime="text/csv"
)

# --- VERIFY LOADED STATE ---
conn = get_db()
row_check = pd.read_sql_query("SELECT COUNT(*) as c, COALESCE(SUM(amount), 0) as s FROM gifts", conn)
conn.close()

if row_check['c'].iloc[0] == 0:
    st.info("No data loaded. Choose **Option A** to load the $30M synthetic demo, or **Option B** to upload your own CSV file in the sidebar.")
    st.stop()

# --- CROSS-DASHBOARD FILTERS ---
conn = get_db()
min_yr_q = pd.read_sql_query("SELECT MIN(gift_year) as min_y, MAX(gift_year) as max_y FROM gifts", conn)
min_y = int(min_yr_q['min_y'].iloc[0]) if min_yr_q['min_y'].iloc[0] else 2022
max_y = int(min_yr_q['max_y'].iloc[0]) if min_yr_q['max_y'].iloc[0] else 2026

campaigns_available = ["All Campaigns"] + [r[0] for r in conn.execute("SELECT DISTINCT campaign FROM gifts WHERE campaign IS NOT NULL").fetchall()]
officers_available = ["All Officers"] + [r[0] for r in conn.execute("SELECT DISTINCT assigned_officer FROM donors WHERE assigned_officer IS NOT NULL").fetchall()]
conn.close()

st.sidebar.markdown("---")
st.sidebar.subheader("Dashboard Cross-Filters")
sel_years = st.sidebar.slider("Filter Years", min_y, max_y, (min_y, max_y)) if min_y < max_y else (min_y, max_y)
sel_campaign = st.sidebar.selectbox("Filter Campaign", campaigns_available)
sel_officer = st.sidebar.selectbox("Filter Gift Officer", officers_available)

# Filtered Query
conn = get_db()
base_sql = "SELECT g.*, d.name, d.giving_tier, d.assigned_officer, d.state, d.donor_type FROM gifts g JOIN donors d ON g.donor_id=d.donor_id WHERE g.gift_year BETWEEN ? AND ?"
params = [sel_years[0], sel_years[1]]

if sel_campaign != "All Campaigns":
    base_sql += " AND g.campaign = ?"
    params.append(sel_campaign)
if sel_officer != "All Officers":
    base_sql += " AND d.assigned_officer = ?"
    params.append(sel_officer)

df_filtered = pd.read_sql_query(base_sql, conn, params=params)
conn.close()

# Top Metric Cards
total_rev = df_filtered['amount'].sum() if not df_filtered.empty else 0.0
total_gifts = len(df_filtered)
total_donors = df_filtered['donor_id'].nunique()
avg_val = total_rev / total_gifts if total_gifts > 0 else 0.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Active Filtered Revenue", f"${total_rev:,.2f}")
col2.metric("Total Gift Records", f"{total_gifts:,}")
col3.metric("Constituent Donors", f"{total_donors:,}")
col4.metric("Avg Gift Size", f"${avg_val:,.2f}")

st.markdown("---")

# Main Navigation
tab_exec, tab_sim, tab_donors, tab_companion = st.tabs([
    "Executive Visualizations", 
    "What-If Forecasting Simulator", 
    "Donor Health & Giving Pyramid", 
    "Smart Companion (Chatbot)"
])

# ----------------- TAB 1: EXECUTIVE VISUALIZATIONS -----------------
with tab_exec:
    st.subheader(f"Cash Flow & Campaign Performance ({sel_years[0]} - {sel_years[1]})")
    if not df_filtered.empty:
        df_time = df_filtered.groupby(['gift_year', 'gift_month'])['amount'].sum().reset_index()
        df_time['date'] = pd.to_datetime(df_time['gift_year'].astype(str) + '-' + df_time['gift_month'].astype(str) + '-01')
        df_time = df_time.sort_values('date')

        fig_cash = px.area(df_time, x="date", y="amount", title="Cash Flow Velocity", labels={"amount": "Monthly Revenue ($)", "date": "Date"}, template="plotly_dark")
        fig_cash.update_traces(line_color="#00CC96", fillcolor="rgba(0, 204, 150, 0.2)")
        st.plotly_chart(fig_cash, use_container_width=True)

        g1, g2 = st.columns(2)
        with g1:
            fig_camp = px.pie(df_filtered, values="amount", names="campaign", hole=0.45, title="Revenue by Campaign", template="plotly_dark")
            st.plotly_chart(fig_camp, use_container_width=True)
        with g2:
            fig_chan = px.histogram(df_filtered, x="channel", y="amount", histfunc="sum", color="channel", title="Revenue by Channel", template="plotly_dark")
            fig_chan.update_layout(showlegend=False)
            st.plotly_chart(fig_chan, use_container_width=True)
    else:
        st.warning("No gifts match the current filter selection.")

# ----------------- TAB 2: WHAT-IF FORECASTING SIMULATOR -----------------
with tab_sim:
    st.subheader("What-If Forecasting & Scenario Simulator")
    s1, s2, s3 = st.columns(3)
    with s1:
        sim_growth = st.slider("Projected Annual Giving Growth Rate (%)", -20, 40, 5)
    with s2:
        sim_retention_boost = st.slider("Donor Retention Improvement (%)", 0, 30, 8)
    with s3:
        sim_officer_count = st.slider("Major Gift Officers (MGOs)", 1, 10, 4)

    base_annual_rev = total_rev / (sel_years[1] - sel_years[0] + 1) if (sel_years[1] - sel_years[0] + 1) > 0 else 5000000.0
    growth_multiplier = (1 + (sim_growth / 100.0)) * (1 + (sim_retention_boost / 100.0))
    
    forecast_years = [max_y + 1, max_y + 2, max_y + 3, max_y + 4, max_y + 5]
    forecast_revs = []
    curr = base_annual_rev
    for _ in forecast_years:
        curr = curr * growth_multiplier
        forecast_revs.append(round(curr, 2))

    df_forecast = pd.DataFrame({"Year": forecast_years, "Projected Revenue": forecast_revs})
    fig_sim = px.bar(df_forecast, x="Year", y="Projected Revenue", text="Projected Revenue", title="5-Year Projected Capital Yield", template="plotly_dark", color="Projected Revenue", color_continuous_scale="Purples")
    fig_sim.update_traces(texttemplate='$%{text:,.2s}', textposition='outside')
    st.plotly_chart(fig_sim, use_container_width=True)

    total_proj_capital = sum(forecast_revs)
    c_imp1, c_imp2, c_imp3 = st.columns(3)
    c_imp1.metric("Projected People Receiving Food & Water", f"{int(total_proj_capital * 0.45 / 42.50):,} people")
    c_imp2.metric("Projected People Receiving Education", f"{int(total_proj_capital * 0.30 / 115.00):,} students")
    c_imp3.metric("Projected Countries Served", f"{min(60, int(total_proj_capital * 0.25 / 185000.00))} countries")

# ----------------- TAB 3: DONOR HEALTH & GIVING PYRAMID -----------------
with tab_donors:
    st.subheader("Giving Pyramid & Major Donors")
    tier_order = ["$100,000+", "$10,000 - $99,999", "$1,000 - $9,999", "$100 - $999", "Under $100"]
    df_pyramid = df_filtered.groupby("giving_tier").agg(revenue=('amount', 'sum'), donors=('donor_id', 'nunique')).reset_index()
    df_pyramid['sort_key'] = df_pyramid['giving_tier'].apply(lambda x: tier_order.index(x) if x in tier_order else 99)
    df_pyramid = df_pyramid.sort_values('sort_key')

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        fig_pyr = px.funnel(df_pyramid, x='revenue', y='giving_tier', title="Giving Pyramid (Revenue Volume)", template="plotly_dark")
        st.plotly_chart(fig_pyr, use_container_width=True)
    with col_p2:
        fig_don = px.bar(df_pyramid, x='giving_tier', y='donors', title="Donor Headcount by Tier", template="plotly_dark", color="donors", color_continuous_scale="Teal")
        st.plotly_chart(fig_don, use_container_width=True)

    st.subheader("Constituent Records Table")
    st.dataframe(df_filtered[['donor_id', 'name', 'donor_type', 'giving_tier', 'assigned_officer', 'amount', 'campaign', 'channel']].head(200), use_container_width=True)

# ----------------- TAB 4: SMART COMPANION AGENT -----------------
with tab_companion:
    st.subheader("Smart Companion (AI Assistant)")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "I am the Causefleet Smart Companion. Ask questions about revenue, top donors, campaigns, or planted storylines."}
        ]

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "sql" in message and message["sql"]:
                with st.expander("Inspected SQL"):
                    st.code(message["sql"], language="sql")

    if query := st.chat_input("Enter your analytical question..."):
        st.session_state.chat_history.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            result = run_dynamic_agent(query)
            st.markdown(result["answer"])
            if result.get("sql"):
                with st.expander("Inspected SQL"):
                    st.code(result["sql"], language="sql")
                    
        st.session_state.chat_history.append({"role": "assistant", "content": result["answer"], "sql": result.get("sql")})
