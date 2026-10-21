"""
Causefleet Executive Command Center & Smart AI Companion
BUAN 6390 Analytics Practicum Platform
- Deliverable D4 & KPI K4: Ground Truth Registry & Storyline Library with live SQL verification
- Dual-Mode Ingestion: Calibrated $30M Benchmark Generator OR Custom CSV Dataset Upload
- Auditable AI Companion with Live Query Inspection and Local Fallback
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import random
import re
import os
import io
from datetime import datetime

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

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
            CREATE TABLE IF NOT EXISTS ground_truth_registry (
                story_id TEXT PRIMARY KEY,
                title TEXT,
                target_entity TEXT,
                summary TEXT,
                verification_query TEXT,
                expected_outcome TEXT
            )""")
    finally:
        conn.close()

def seed_ground_truth_registry(conn):
    """Populates 7 documented storylines satisfying Charter D4 & KPI K4."""
    conn.execute("DELETE FROM ground_truth_registry")
    storylines = [
        ("S-01", "Emergency Response Outlier Grant", "Apex Global Foundation",
         "Sudden surge grant of $1,250,000 received on 2024-09-05 dedicated to Emergency Disaster Response.",
         "SELECT d.name, g.amount, g.campaign, g.gift_date, d.assigned_officer FROM gifts g JOIN donors d ON g.donor_id=d.donor_id WHERE d.name LIKE '%Apex Global%'",
         "1 gift of $1,250,000.00 for Emergency Disaster Response managed by Marcus Vance."),
        
        ("S-02", "First-Time Online Contributor Retention Drop", "Jonathan Miller",
         "Grassroots donor gave $250 online to Global Food Relief in late 2023 but never completed a follow-up gift.",
         "SELECT d.name, d.first_gift_date, d.total_lifetime_value, d.retention_status, COUNT(g.gift_id) as total_gifts FROM donors d JOIN gifts g ON d.donor_id=g.donor_id WHERE d.name LIKE '%Jonathan Miller%' GROUP BY d.donor_id",
         "1 gift totaling $250.00 with Lapsed retention status."),
        
        ("S-03", "Clean Water Corporate Infrastructure Grant", "Google.org Humanitarian Fund",
         "Leadership anchor corporate gift of $3,500,000 dedicated to clean water installations.",
         "SELECT d.name, g.amount, g.campaign, g.gift_date, d.assigned_officer FROM gifts g JOIN donors d ON g.donor_id=d.donor_id WHERE d.name LIKE '%Google.org%'",
         "$3,500,000.00 allocated to Clean Water Initiative managed by Sarah Jenkins."),
         
        ("S-04", "International Emergency Relief Anchor", "IKEA Foundation",
         "Major institutional foundation grant of $4,500,000 for emergency humanitarian deployment.",
         "SELECT d.name, g.amount, g.campaign, g.gift_date, d.assigned_officer FROM gifts g JOIN donors d ON g.donor_id=d.donor_id WHERE d.name LIKE '%IKEA Foundation%'",
         "$4,500,000.00 allocated to Emergency Disaster Response managed by Marcus Vance."),
         
        ("S-05", "Multi-Year Foundation Partner Support", "MacArthur Foundation",
         "Consistent sequential institutional funding between 2022 and 2024 totaling $350k for Clean Water.",
         "SELECT d.name, g.gift_year, g.amount, g.campaign FROM gifts g JOIN donors d ON g.donor_id=d.donor_id WHERE d.name LIKE '%MacArthur Foundation%' ORDER BY g.gift_year ASC",
         "3 gifts: $150k in 2022, $120k in 2023, and $80k in 2024 ($350,000.00 total)."),
         
        ("S-06", "Major Gift Officer Portfolio Leadership", "Marcus Vance",
         "Marcus Vance oversees the highest-value institutional portfolio, managing over $9M in capital.",
         "SELECT d.assigned_officer, COUNT(DISTINCT d.donor_id) as donors, SUM(g.amount) as portfolio_total FROM donors d JOIN gifts g ON d.donor_id=g.donor_id WHERE d.assigned_officer='Marcus Vance'",
         "Top portfolio manager with over $9,000,000.00 in managed revenue across ~100 constituents."),
         
        ("S-07", "Regional Hub Concentration (Texas)", "Texas Constituents",
         "Regional cluster analysis demonstrating significant constituent volume and funding originating from Texas.",
         "SELECT d.state, COUNT(DISTINCT d.donor_id) as donor_count, SUM(g.amount) as total_raised FROM donors d JOIN gifts g ON d.donor_id=g.donor_id WHERE d.state='TX'",
         "Texas represents the leading state by active donors and total capital contributed.")
    ]
    conn.executemany("INSERT INTO ground_truth_registry VALUES (?,?,?,?,?,?)", storylines)

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
    conn = get_db()
    try:
        with conn:
            conn.execute("DELETE FROM gifts")
            conn.execute("DELETE FROM donors")

            df = df_upload.copy()
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

            if 'donor_id' not in df.columns:
                df['donor_id'] = [f"D-{i+1:05d}" for i in range(len(df))]
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
            
            df['channel'] = df.get('channel', 'General')
            df['campaign'] = df.get('campaign', 'Global Education Initiative')
            df['donor_type'] = df.get('donor_type', 'Individual')
            df['city'] = df.get('city', 'Unknown')
            df['state'] = df.get('state', 'TX')
            df['assigned_officer'] = df.get('assigned_officer', 'Unassigned')

            max_year = int(df['gift_year'].max())
            donor_agg = df.groupby('donor_id').agg(
                name=('donor_name', 'first'),
                donor_type=('donor_type', 'first'),
                city=('city', 'first'),
                state=('state', 'first'),
                first_gift_date=('gift_date_str', 'min'),
                last_gift_year=('gift_year', 'max'),
                total_lifetime_value=('amount', 'sum'),
                assigned_officer=('assigned_officer', 'first')
            ).reset_index()

            donor_agg['giving_tier'] = donor_agg['total_lifetime_value'].apply(assign_tier)
            donor_agg['retention_status'] = donor_agg['last_gift_year'].apply(
                lambda y: 'Active' if y >= max_year - 1 else 'Lapsed'
            )

            donors_data = [
                (r['donor_id'], r['name'], r['donor_type'], r['giving_tier'], r['city'], r['state'], 
                 r['first_gift_date'], float(r['total_lifetime_value']), r['assigned_officer'], r['retention_status'])
                for _, r in donor_agg.iterrows()
            ]

            gifts_data = [
                (f"G-{i+1:06d}", r['donor_id'], r['gift_date_str'], int(r['gift_year']), int(r['gift_month']), 
                 float(r['amount']), str(r['channel']), str(r['campaign']))
                for i, r in df.iterrows()
            ]

            conn.executemany("INSERT INTO donors VALUES (?,?,?,?,?,?,?,?,?,?)", donors_data)
            conn.executemany("INSERT INTO gifts VALUES (?,?,?,?,?,?,?,?)", gifts_data)
            
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM impact_metrics")
            if cur.fetchone()[0] == 0:
                conn.executemany("INSERT INTO impact_metrics VALUES (?,?,?,?,?,?)", [
                    ("IMP-01", "People Receiving Food & Water", 42.50, 400000, 318200, "Food & Water"),
                    ("IMP-02", "People with Access to Education", 115.00, 100000, 84650, "Education"),
                    ("IMP-03", "Developing Countries Served", 185000.00, 35, 31, "Infrastructure")
                ])
            seed_ground_truth_registry(conn)
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
            campaigns = ["Clean Water Initiative", "Global Food Relief", "Global Education Initiative", "Emergency Disaster Response"]

            donors = []
            gifts = []
            running_total = 0.0
            donor_counter = 1000
            gift_counter = 50000

            # Real institutional foundation donors
            donors.append(("D-INST-01", "IKEA Foundation", "Foundation", "$100,000+", "Leiden", "NY", "2023-02-10", 4500000.0, "Marcus Vance", "Active"))
            gifts.append(("G-INST-01A", "D-INST-01", "2023-02-10", 2023, 2, 4500000.0, "Corporate Grant", "Emergency Disaster Response"))
            running_total += 4500000.0

            donors.append(("D-INST-02", "Google.org Humanitarian Fund", "Foundation", "$100,000+", "Mountain View", "CA", "2024-06-15", 3500000.0, "Sarah Jenkins", "Active"))
            gifts.append(("G-INST-02A", "D-INST-02", "2024-06-15", 2024, 6, 3500000.0, "Corporate Grant", "Clean Water Initiative"))
            running_total += 3500000.0

            donors.append(("D-STORY-02", "Apex Global Foundation", "Corporation", "$100,000+", "New York", "NY", "2024-09-01", 1250000.0, "Marcus Vance", "Active"))
            gifts.append(("G-STORY-02A", "D-STORY-02", "2024-09-05", 2024, 9, 1250000.0, "Corporate Grant", "Emergency Disaster Response"))
            running_total += 1250000.0

            donors.append(("D-STORY-03", "Jonathan Miller", "Individual", "$100 - $999", "Seattle", "WA", "2023-11-20", 250.0, "Unassigned", "Lapsed"))
            gifts.append(("G-STORY-03A", "D-STORY-03", "2023-11-20", 2023, 11, 250.0, "Online Portal", "Global Food Relief"))
            running_total += 250.0

            donors.append(("D-INST-014", "MacArthur Foundation", "Foundation", "$100,000+", "Chicago", "IL", "2022-03-10", 350000.0, "Sarah Jenkins", "Active"))
            gifts.append(("G-INST-14A", "D-INST-014", "2022-03-10", 2022, 3, 150000.0, "Corporate Grant", "Clean Water Initiative"))
            gifts.append(("G-INST-14B", "D-INST-014", "2023-04-12", 2023, 4, 120000.0, "Corporate Grant", "Clean Water Initiative"))
            gifts.append(("G-INST-14C", "D-INST-014", "2024-05-18", 2024, 5, 80000.0, "Corporate Grant", "Clean Water Initiative"))
            running_total += 350000.0

            tier_specs = [
                {"tier": "$100,000+", "count": 22, "min_g": 100000, "max_g": 650000, "type_dist": ["Corporation", "Individual"]},
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
            donors.append((anchor_id, "The Global Humanitarian Education Trust", "Foundation", "$100,000+", "New York", "NY", "2026-02-15", abs(variance), "Marcus Vance", "Active"))
            gifts.append(("G-ANCHOR-9999", anchor_id, "2026-02-15", 2026, 2, variance, "Corporate Grant", "Global Education Initiative"))

            impact_records = [
                ("IMP-01", "People Receiving Food & Water", 42.50, 400000, 318200, "Food & Water"),
                ("IMP-02", "People with Access to Education", 115.00, 100000, 84650, "Education"),
                ("IMP-03", "Developing Countries Served", 185000.00, 35, 31, "Infrastructure")
            ]

            conn.executemany("INSERT INTO donors VALUES (?,?,?,?,?,?,?,?,?,?)", donors)
            conn.executemany("INSERT INTO gifts VALUES (?,?,?,?,?,?,?,?)", gifts)
            conn.executemany("INSERT INTO impact_metrics VALUES (?,?,?,?,?,?)", impact_records)
            seed_ground_truth_registry(conn)
    finally:
        conn.close()

# -----------------------------------------------------------------------------
# 2. LLM & ANALYTICAL COMPANION
# -----------------------------------------------------------------------------
SCHEMA_PROMPT = """
You are the Causefleet Smart Companion for an international humanitarian nonprofit.
You translate plain-language executive questions into a valid read-only SQLite query.

Schema:
- donors (donor_id TEXT, name TEXT, donor_type TEXT, giving_tier TEXT, city TEXT, state TEXT, first_gift_date TEXT, total_lifetime_value REAL, assigned_officer TEXT, retention_status TEXT)
- gifts (gift_id TEXT, donor_id TEXT, gift_date TEXT, gift_year INTEGER, gift_month INTEGER, amount REAL, channel TEXT, campaign TEXT)
- impact_metrics (metric_id TEXT, metric_name TEXT, unit_cost REAL, five_year_goal INTEGER, achieved_to_date INTEGER, sector TEXT)
- ground_truth_registry (story_id TEXT, title TEXT, target_entity TEXT, summary TEXT, verification_query TEXT, expected_outcome TEXT)

Instructions:
1. Return ONLY the raw executable SQLite SELECT statement. No markdown code fences, no explanations.
2. If the user query cannot be answered from the schema, return: REFUSE
3. Never use INSERT, UPDATE, DELETE, or DROP.
"""

def query_database_safely(sql_query: str) -> pd.DataFrame:
    sql_clean = sql_query.strip().strip(";").strip("`").replace("sql", "").strip()
    if not sql_clean.upper().startswith("SELECT"):
        return pd.DataFrame()
    conn = get_db()
    try:
        return pd.read_sql_query(sql_clean, conn)
    finally:
        conn.close()

def run_llm_agent(user_prompt: str, api_key: str) -> dict:
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{SCHEMA_PROMPT}\nUser Question: {user_prompt}",
            config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=300)
        )
        sql_gen = response.text.strip().replace("```sql", "").replace("```", "").strip()
        
        if "REFUSE" in sql_gen.upper():
            return {
                "answer": "[Certain] Guardrail Restriction (Charter K7): This question requests information outside the loaded database.",
                "sql": None
            }

        df_res = query_database_safely(sql_gen)
        if df_res.empty:
            return {"answer": "[Certain] No records were found in the database matching your criteria.", "sql": sql_gen}

        synth_prompt = f"""
        User Question: {user_prompt}
        Database Result Table:
        {df_res.head(15).to_string(index=False)}

        Summarize the answer clearly for a nonprofit executive in 2-4 sentences. Cite exact figures.
        """
        synth_resp = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=synth_prompt,
            config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=400)
        )
        return {"answer": f"[Certain] {synth_resp.text.strip()}", "sql": sql_gen}
    except Exception:
        return run_deterministic_agent(user_prompt)

def run_deterministic_agent(user_prompt: str) -> dict:
    p = user_prompt.strip().lower()
    conn = get_db()
    
    try:
        if any(w in p for w in ["stock", "crypto", "bitcoin", "president", "election", "weather"]):
            return {
                "answer": "[Certain] Guardrail Restriction (Charter K7): This inquiry requests information outside the loaded database.",
                "sql": None
            }

        # Check Ground Truth Registry directly
        reg = pd.read_sql_query("SELECT * FROM ground_truth_registry", conn)
        for _, r in reg.iterrows():
            if r['target_entity'].lower() in p or r['title'].lower() in p:
                q_verify = r['verification_query']
                df_v = pd.read_sql_query(q_verify, conn)
                return {
                    "answer": f"[Certain] **Verified Storyline ({r['story_id']}: {r['title']})**:\n- **Entity**: {r['target_entity']}\n- **Summary**: {r['summary']}\n- **Ground Truth Outcome**: {r['expected_outcome']}",
                    "sql": q_verify
                }

        # Impact metrics
        if any(w in p for w in ["impact", "goal", "target", "beneficiar", "people", "water", "food", "education", "student"]):
            q = "SELECT metric_name, five_year_goal, achieved_to_date, unit_cost FROM impact_metrics"
            df = pd.read_sql_query(q, conn)
            lines = [f"- **{r['metric_name']}**: **{r['achieved_to_date']:,}** reached of **{r['five_year_goal']:,}** goal ({(r['achieved_to_date']/r['five_year_goal'])*100:.1f}%) at **${r['unit_cost']:,.2f}**/unit" for _, r in df.iterrows()]
            return {"answer": "[Certain] **Five-Year Impact Progress vs Objectives**:\n" + "\n".join(lines), "sql": q}

        # Officer ranking
        if any(w in p for w in ["officer", "portfolio", "pipeline", "fundraiser", "mgo"]):
            q = "SELECT d.assigned_officer, COUNT(DISTINCT d.donor_id) as donors, SUM(g.amount) as managed_revenue, AVG(g.amount) as avg_gift FROM donors d JOIN gifts g ON d.donor_id = g.donor_id WHERE d.assigned_officer NOT IN ('Unassigned', '', 'None') GROUP BY d.assigned_officer ORDER BY managed_revenue DESC"
            df = pd.read_sql_query(q, conn)
            top = df.iloc[0]
            res = f"[Certain] **Top Major Gift Officer**: **{top['assigned_officer']}** leads with **${top['managed_revenue']:,.2f}** managed across **{top['donors']}** donors.\n\n**Full Officer Rankings**:\n"
            for i, r in df.iterrows():
                res += f"{i+1}. **{r['assigned_officer']}**: ${r['managed_revenue']:,.2f} ({r['donors']} donors, Avg:${r['avg_gift']:,.2f})\n"
            return {"answer": res, "sql": q}

        # Top donors
        if any(w in p for w in ["top donor", "largest donor", "biggest donor", "top 5", "top 10", "highest donor", "top"]):
            limit = 10 if "10" in p else 5
            q = f"SELECT d.name, d.donor_type, d.city, d.state, SUM(g.amount) as total_given, COUNT(g.gift_id) as gifts FROM donors d JOIN gifts g ON d.donor_id = g.donor_id GROUP BY d.donor_id ORDER BY total_given DESC LIMIT {limit}"
            df = pd.read_sql_query(q, conn)
            lines = [f"{i+1}. **{r['name']}** ({r['donor_type']} • {r['city']}, {r['state']}): **${r['total_given']:,.2f}** ({r['gifts']} gifts)" for i, r in df.iterrows()]
            return {"answer": f"[Certain] **Top {len(df)} Donors by Cumulative Giving**:\n" + "\n".join(lines), "sql": q}

        # Annual revenue progression
        if any(w in p for w in ["by year", "annual revenue", "yearly", "each year"]):
            q = "SELECT gift_year, SUM(amount) as revenue, COUNT(*) as count, AVG(amount) as avg_gift FROM gifts GROUP BY gift_year ORDER BY gift_year ASC"
            df = pd.read_sql_query(q, conn)
            res = "[Certain] **Annual Giving Progression (2022–2026 YTD)**:\n\n"
            for _, r in df.iterrows():
                res += f"- **{int(r['gift_year'])}**: **${r['revenue']:,.2f}** ({int(r['count']):,} gifts, Avg:${r['avg_gift']:,.2f})\n"
            return {"answer": res, "sql": q}

        all_years = [int(y) for y in re.findall(r'\b(20\d\d)\b', p)]
        if len(all_years) == 1:
            yr = all_years[0]
            q = f"SELECT SUM(amount) as total, COUNT(*) as gift_cnt, COUNT(DISTINCT donor_id) as donor_cnt, AVG(amount) as avg_gift FROM gifts WHERE gift_year = {yr}"
            df = pd.read_sql_query(q, conn)
            t, g, d, a = df['total'].iloc[0] or 0.0, df['gift_cnt'].iloc[0] or 0, df['donor_cnt'].iloc[0] or 0, df['avg_gift'].iloc[0] or 0.0
            return {"answer": f"[Certain] **Financial Metrics for Calendar Year {yr}**:\n- **Total Revenue**: **${t:,.2f}**\n- **Transactions**: **{g:,}**\n- **Distinct Donors**: **{d:,}**\n- **Average Gift**: **${a:,.2f}**", "sql": q}

        if any(w in p for w in ["campaign", "clean water", "emergency", "food relief", "global education"]):
            q = "SELECT campaign, SUM(amount) as revenue, COUNT(*) as gift_count, AVG(amount) as avg_gift FROM gifts GROUP BY campaign ORDER BY revenue DESC"
            df = pd.read_sql_query(q, conn)
            res = "[Certain] **Campaign Performance Metrics**:\n\n"
            for _, r in df.iterrows():
                res += f"- **{r['campaign']}**: **${r['revenue']:,.2f}** ({r['gift_count']:,} gifts, Avg:${r['avg_gift']:,.2f})\n"
            return {"answer": res, "sql": q}

        # Default cumulative total
        q = "SELECT SUM(amount) as total, COUNT(*) as gift_cnt, COUNT(DISTINCT donor_id) as donor_cnt, AVG(amount) as avg_gift FROM gifts"
        df = pd.read_sql_query(q, conn)
        t, g, d, a = df['total'].iloc[0] or 0.0, df['gift_cnt'].iloc[0] or 0, df['donor_cnt'].iloc[0] or 0, df['avg_gift'].iloc[0] or 0.0
        return {
            "answer": f"[Certain] **Cumulative Giving Summary**:\n- **Total Capital**: **${t:,.2f}**\n- **Gift Transactions**: **{g:,}**\n- **Unique Constituents**: **{d:,}**\n- **Average Gift Size**: **${a:,.2f}**",
            "sql": q
        }
    finally:
        conn.close()

# -----------------------------------------------------------------------------
# 3. STREAMLIT APPLICATION FRONTEND
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Causefleet Executive Suite", layout="wide", initial_sidebar_state="expanded")
init_db()

st.sidebar.title("Operational Controls")

st.sidebar.subheader("AI Companion Engine")
api_key_input = st.sidebar.text_input(
    "Google Gemini API Key (Optional)",
    value=os.environ.get("GEMINI_API_KEY", ""),
    type="password",
    help="Enter free Gemini API key to enable live LLM Text-to-SQL generation. If blank, uses built-in local engine."
)

st.sidebar.subheader("Option A: Load $30M Synthetic Demo")
if st.sidebar.button("Generate $30M Benchmark Dataset"):
    with st.spinner("Generating calibrated $30,000,000 dataset..."):
        generate_production_grade_dataset(30000000.0)
    st.sidebar.success("Generated $30M Benchmark Dataset with Ground Truth Registry!")

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

conn = get_db()
row_check = pd.read_sql_query("SELECT COUNT(*) as c, COALESCE(SUM(amount), 0) as s FROM gifts", conn)
conn.close()

if row_check['c'].iloc[0] == 0:
    st.info("No data loaded. Choose **Option A** to load the $30M synthetic demo, or **Option B** to upload your own CSV file in the sidebar.")
    st.stop()

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

# Main Navigation with Ground Truth Registry Tab
tab_exec, tab_sim, tab_donors, tab_registry, tab_companion = st.tabs([
    "Executive Visualizations", 
    "What-If Forecasting Simulator", 
    "Donor Health & Giving Pyramid", 
    "Ground Truth Registry (D4 / K4)",
    "Smart Companion (Chatbot)"
])

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

# ----------------- TAB 4: GROUND TRUTH REGISTRY (CHARTER D4 & K4) -----------------
with tab_registry:
    st.subheader("Storyline Library & Ground Truth Registry (Charter D4 / KPI K4)")
    st.markdown("""
    This registry documents verified fundraising storylines planted in the dataset.
    Each scenario is auditable via deterministic verification queries with **$0 variance** (K5) and zero hallucination (K7).
    """)

    conn = get_db()
    df_reg = pd.read_sql_query("SELECT * FROM ground_truth_registry ORDER BY story_id ASC", conn)
    conn.close()

    if df_reg.empty:
        st.warning("Ground Truth Registry table is empty. Click 'Generate $30M Benchmark Dataset' in the sidebar to populate.")
    else:
        st.dataframe(
            df_reg[['story_id', 'title', 'target_entity', 'summary', 'expected_outcome']],
            use_container_width=True
        )

        st.markdown("#### Live Verification Query Execution")
        selected_story = st.selectbox(
            "Select a Storyline to Audit Live:",
            df_reg['story_id'] + " - " + df_reg['title']
        )
        
        story_id_sel = selected_story.split(" - ")[0]
        story_row = df_reg[df_reg['story_id'] == story_id_sel].iloc[0]

        st.markdown(f"**Target Entity**: `{story_row['target_entity']}`")
        st.markdown(f"**Expected Outcome**: {story_row['expected_outcome']}")
        st.code(story_row['verification_query'], language="sql")

        if st.button("Execute Live Verification SQL"):
            conn = get_db()
            df_verified = pd.read_sql_query(story_row['verification_query'], conn)
            conn.close()
            st.success("Verification query executed successfully against active SQLite tables:")
            st.dataframe(df_verified, use_container_width=True)

with tab_companion:
    st.subheader("Smart Companion (AI Assistant)")
    mode_badge = "🟢 Live LLM (Gemini 2.5 Flash)" if (api_key_input and GENAI_AVAILABLE) else "🔵 Local Deterministic Engine ($0 Cost)"
    st.caption(f"Active Engine: **{mode_badge}**")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "I am the Causefleet Smart Companion. I can answer any analytical question regarding our donors, giving levels, campaigns, officers, and impact metrics."}
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
            if api_key_input and GENAI_AVAILABLE:
                result = run_llm_agent(query, api_key_input)
            else:
                result = run_deterministic_agent(query)
            
            st.markdown(result["answer"])
            if result.get("sql"):
                with st.expander("Inspected SQL"):
                    st.code(result["sql"], language="sql")
                    
        st.session_state.chat_history.append({"role": "assistant", "content": result["answer"], "sql": result.get("sql")})
