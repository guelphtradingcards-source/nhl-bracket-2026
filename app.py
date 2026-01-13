import streamlit as st
import pandas as pd
import requests
from PIL import Image
import os

# 1. PAGE SETUP
st.set_page_config(page_title="NHL 2026 Bracketology", layout="wide")

# --- CUSTOM CSS FOR NHL FEEL ---
st.markdown("""
<style>
    .matchup-card { background: #111; border: 1px solid #333; border-radius: 4px; padding: 10px; margin-bottom: 10px; }
    .team-row { display: flex; justify-content: space-between; align-items: center; padding: 5px 0; }
    .clinch-tag { font-size: 10px; font-weight: bold; padding: 2px 5px; border-radius: 3px; margin-left: 5px; }
    .clinch-x { background: #15803d; color: white; } /* Clinched */
    .bubble { background: #b91c1c; color: white; } /* Out */
    .hero-text { text-align: center; padding: 20px; background: #000; border-bottom: 3px solid #D0D3D4; }
</style>
""", unsafe_allow_html=True)

# 2. BRANDING & HERO
if os.path.exists("header.img"):
    st.image(Image.open("header.img"), use_container_width=True)

col_l, col_r = st.columns([1, 4])
with col_l:
    if os.path.exists("logo.img"):
        st.image(Image.open("logo.img"), width=150)
with col_r:
    st.title("NHL BRACKET CHALLENGE 2026")
    st.markdown("### *Predictive Standings & Magic Numbers*")

# 3. DATA ENGINE
@st.cache_data(ttl=3600)
def get_nhl_data():
    url = "https://api-web.nhle.com/v1/standings/now"
    data = requests.get(url).json()['standings']
    return pd.DataFrame([{
        'team': r['teamName']['default'], 'conf': r['conferenceName'], 
        'div': r['divisionName'], 'pts': r['points'], 'gp': r['gamesPlayed'],
        'w': r['wins'], 'l': r['losses'], 'ot': r['otLosses'],
        'logo': r['teamLogo']} for r in data])

df_base = get_nhl_data()

# 4. SIMULATION DIALOG (The Modal)
@st.dialog("Simulation Settings")
def sim_modal():
    st.session_state.target = st.selectbox("Focus Team", sorted(df_base['team'].tolist()))
    st.session_state.sim_games = st.slider("Games to Simulate", 0, 82-int(df_base['gp'].mean()), 0)
    st.session_state.f_wins = st.slider("Focus Team Wins", 0, st.session_state.sim_games, 0)
    st.session_state.sos = st.select_slider("Schedule Difficulty (SoS)", options=["Easy", "Standard", "Hard"], value="Standard")
    if st.button("Calculate Predictions"):
        st.rerun()

# Init State
if 'sim_games' not in st.session_state: st.session_state.sim_games = 0

if st.button("⚙️ Open Predictor Sliders"):
    sim_modal()

# 5. FEATURE 2: SOS & ADVANCED PREDICTION
df = df_base.copy()
# Adjust pace based on SoS: Easy (+5%), Hard (-5%)
sos_map = {"Easy": 1.05, "Standard": 1.0, "Hard": 0.95}
sos_adj = sos_map.get(st.session_state.get('sos', 'Standard'), 1.0)

for i, row in df.iterrows():
    rem = 82 - row['gp']
    sim_window = min(st.session_state.sim_games, rem)
    
    if row['team'] == st.session_state.get('target', ''):
        df.at[i, 'pts'] += (st.session_state.get('f_wins', 0) * 2)
    else:
        # Predictive record based on season pace * SoS
        pace = (row['pts'] / (row['gp'] * 2)) * sos_adj
        df.at[i, 'pts'] += round(pace * (sim_window * 2))

# 6. FEATURE 4: MAGIC NUMBERS & CLINCHING
# Simplified: If 100 pts, tagged as Clinched (x)
def get_clinch_tag(pts):
    if pts >= 100: return '<span class="clinch-tag clinch-x">X</span>'
    return ''

# 7. FEATURE 3: SEASON SERIES (MOCK)
# In a real app, you'd fetch H2H; here we display the match structure
def render_matchup(t1, t2, s1, s2):
    st.markdown(f"""
    <div class="matchup-card">
        <div class="team-row">
            <span><img src="{t1['logo']}" width="20"> {t1['team']} {get_clinch_tag(t1['pts'])}</span>
            <span class="pts">{int(t1['pts'])}</span>
        </div>
        <div style="text-align:center; color:#555; font-size:9px;">H2H: 2-1-0</div>
        <div class="team-row">
            <span><img src="{t2['logo']}" width="20"> {t2['team']} {get_clinch_tag(t2['pts'])}</span>
            <span class="pts">{int(t2['pts'])}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 8. LAYOUT
st.markdown("---")
col_e, col_w = st.columns(2)

def draw_bracket(conf, col):
    sub = df[df['conf'] == conf].sort_values('pts', ascending=False).head(8).reset_index()
    with col:
        st.subheader(f"{conf.upper()} CONFERENCE")
        for i in range(4):
            render_matchup(sub.iloc[i], sub.iloc[7-i], i+1, 8-i)

draw_bracket("Eastern", col_e)
draw_bracket("Western", col_w)

# 9. FEATURE 1: WILD CARD WATCH
st.markdown("---")
st.subheader("🏁 FEATURE 1: WILD CARD WATCH")
wc_e, wc_w = st.columns(2)

def draw_wc(conf, col):
    full_conf = df[df['conf'] == conf].sort_values('pts', ascending=False)
    # The 8th spot is the target
    target_pts = full_conf.iloc[7]['pts']
    bubble = full_conf.iloc[6:11] # 7th through 11th
    with col:
        for i, row in bubble.iterrows():
            diff = int(row['pts'] - target_pts)
            tag = f'<span class="clinch-tag bubble">{diff} OUT</span>' if diff < 0 else '<span class="clinch-tag clinch-x">IN</span>'
            st.write(f"{row['team']}: {int(row['pts'])} PTS {tag}")

draw_wc("Eastern", wc_e)
draw_wc_watch = draw_wc("Western", wc_w)
