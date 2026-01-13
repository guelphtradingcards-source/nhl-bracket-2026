import streamlit as st
import pandas as pd
import requests
from PIL import Image
import os

# 1. PAGE SETUP
st.set_page_config(page_title="NHL Bracket 2026", layout="wide")

# --- STYLING (The Pro Black/Silver Look) ---
st.markdown("""
<style>
    .matchup-card { background: #111; border: 1px solid #333; border-radius: 4px; padding: 10px; margin-bottom: 10px; }
    .team-row { display: flex; justify-content: space-between; align-items: center; padding: 5px 0; }
    .pts { font-weight: 900; color: #fff; }
    .wc-table { width: 100%; color: #eee; border-collapse: collapse; }
    .wc-table th { border-bottom: 2px solid #444; text-align: left; padding: 10px; color: #888; font-size: 12px; }
    .wc-table td { padding: 10px; border-bottom: 1px solid #222; }
    .in-tag { color: #22c55e; font-weight: bold; }
    .out-tag { color: #ef4444; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# 2. HERO SECTION
if os.path.exists("header.img"):
    st.image(Image.open("header.img"), use_container_width=True)

col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.img"):
        st.image(Image.open("logo.img"), width=120)
    else:
        st.markdown("<h1 style='text-align:center;'>🏆</h1>", unsafe_allow_html=True)
with col_title:
    st.title("2026 NHL PLAYOFF PREDICTOR")

# 3. DATA & SESSION STATE
if 'sim_games' not in st.session_state: st.session_state.sim_games = 0
if 'f_wins' not in st.session_state: st.session_state.f_wins = 0

@st.cache_data(ttl=3600)
def get_data():
    url = "https://api-web.nhle.com/v1/standings/now"
    data = requests.get(url).json()['standings']
    return pd.DataFrame([{
        'team': r['teamName']['default'], 'conf': r['conferenceName'], 
        'div': r['divisionName'], 'pts': r['points'], 'gp': r['gamesPlayed'],
        'logo': r['teamLogo']} for r in data])

df_base = get_data()

# 4. BUG FIX: SLIDER MODAL
@st.dialog("Prediction Engine")
def open_sim():
    st.write("Project the remainder of the season.")
    target = st.selectbox("Focus Team", sorted(df_base['team'].tolist()))
    
    # Error prevention: check max games left
    avg_rem = 82 - int(df_base['gp'].mean())
    # Slider logic: Ensure max_value > 0
    max_sim = max(1, avg_rem) 
    
    st.session_state.sim_games = st.slider("Games Remaining", 0, max_sim, st.session_state.sim_games)
    
    # Reset wins if they exceed new sim window
    max_wins = max(1, st.session_state.sim_games)
    st.session_state.f_wins = st.slider(f"{target} Wins", 0, max_wins, min(st.session_state.f_wins, max_wins))
    
    if st.button("Apply Scenarios"):
        st.session_state.target_team = target
        st.rerun()

if st.button("⚙️ Open Simulation Settings", type="primary"):
    open_sim()

# 5. PREDICTIVE LOGIC
df = df_base.copy()
df['p_pct'] = df['pts'] / (df['gp'] * 2)

for i, row in df.iterrows():
    if row['team'] == st.session_state.get('target_team', ''):
        df.at[i, 'pts'] += (st.session_state.f_wins * 2)
    else:
        add = round(row['p_pct'] * (st.session_state.sim_games * 2))
        df.at[i, 'pts'] += add

# 6. BRACKET RENDERING
def draw_matchup(t1, t2):
    st.markdown(f"""
    <div class="matchup-card">
        <div class="team-row">
            <span><img src="{t1['logo']}" width="20"> {t1['team']}</span>
            <span class="pts">{int(t1['pts'])}</span>
        </div>
        <div style="text-align:center; font-size:10px; color:#444; margin:5px 0;">VS</div>
        <div class="team-row">
            <span><img src="{t2['logo']}" width="20"> {t2['team']}</span>
            <span class="pts">{int(t2['pts'])}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

col_e, col_w = st.columns(2)

def build_conf(name, col):
    sub = df[df['conf'] == name].sort_values('pts', ascending=False).head(8).reset_index()
    with col:
        st.subheader(f"{name.upper()}")
        for i in range(4):
            draw_matchup(sub.iloc[i], sub.iloc[7-i])

build_conf("Eastern", col_e)
build_conf("Western", col_w)

# 7. BUG FIX: WILD CARD WATCH (HTML Rendering)
st.markdown("---")
st.title("🏁 WILD CARD WATCH")
wc_e_col, wc_w_col = st.columns(2)

def draw_wc_section(conf_name, col):
    # Get everyone below the top 6 in conference (Simple WC logic)
    full_conf = df[df['conf'] == conf_name].sort_values('pts', ascending=False)
    cutoff = full_conf.iloc[7]['pts']
    bubble = full_conf.iloc[6:12] # Teams around the cut line
    
    with col:
        st.write(f"**{conf_name} Bubble**")
        html = "<table class='wc-table'><tr><th>TEAM</th><th>PTS</th><th>GP</th><th>STATUS</th></tr>"
        for _, row in bubble.iterrows():
            diff = int(row['pts'] - cutoff)
            status = "<span class='in-tag'>IN</span>" if diff >= 0 else f"<span class='out-tag'>{diff} OUT</span>"
            html += f"<tr><td>{row['team']}</td><td>{int(row['pts'])}</td><td>{int(row['gp'])}</td><td>{status}</td></tr>"
        html += "</table>"
        # FIX: Use st.markdown with unsafe_allow_html
        st.markdown(html, unsafe_allow_html=True)

draw_wc_section("Eastern", wc_e_col)
draw_wc_section("Western", wc_w_col)
