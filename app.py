import streamlit as st
import pandas as pd
import requests
from PIL import Image
import os
from datetime import datetime

# 1. PAGE SETUP
st.set_page_config(page_title="NHL Playoff Bracket Tracker", layout="wide")

# --- NHL BRANDING CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Condensed:wght@700&family=Roboto:wght@400;900&display=swap');
    
    body { background-color: #000 !important; color: white; font-family: 'Roboto', sans-serif; }
    
    /* Bracket Container */
    .bracket-wrapper { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; padding: 20px; background: #000; }
    
    /* Division Labels */
    .div-header { 
        background: #222; color: #aaa; text-align: center; font-family: 'Roboto Condensed'; 
        font-weight: bold; padding: 4px; font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px;
        border-bottom: 2px solid #38bdf8; margin-bottom: 10px;
    }

    .matchup-card { background: #111; border: 1px solid #333; border-radius: 2px; padding: 8px; margin-bottom: 15px; position: relative; }
    .team-row { display: flex; justify-content: space-between; align-items: center; height: 35px; }
    .team-label { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 13px; }
    
    /* Seed Labels (A1, M2, WC1 etc) */
    .seed-tag { color: #888; font-size: 10px; width: 30px; font-weight: 900; }
    .pts { color: #fff; font-weight: 900; background: #222; padding: 2px 6px; border-radius: 2px; font-size: 12px; }
    
    .vs-line { text-align: center; color: #444; font-size: 9px; margin: 2px 0; font-weight: bold; }
    .timestamp { text-align: center; color: #444; font-size: 10px; margin-top: 40px; }
</style>
""", unsafe_allow_html=True)

# 2. BRANDING
if os.path.exists("header.img"): st.image(Image.open("header.img"), use_container_width=True)

# 3. DATA & SIMULATION
@st.cache_data(ttl=600)
def get_nhl_standings():
    url = "https://api-web.nhle.com/v1/standings/now"
    data = requests.get(url).json()['standings']
    return pd.DataFrame([{
        'team': r['teamName']['default'], 'conf': r['conferenceName'], 
        'div': r['divisionName'], 'pts': r['points'], 'gp': r['gamesPlayed'],
        'w': r['wins'], 'l': r['losses'], 'ot': r['otLosses'],
        'logo': r['teamLogo']} for r in data])

df_base = get_nhl_standings()

# Simulation Settings (Modal)
if 'sim_games' not in st.session_state: st.session_state.sim_games = 0
if 'f_wins' not in st.session_state: st.session_state.f_wins = 0

@st.dialog("Bracket Simulator")
def open_sim():
    st.session_state.target_team = st.selectbox("Team to Track", sorted(df_base['team'].tolist()))
    st.session_state.sim_games = st.slider("Games Remaining", 0, 30, st.session_state.sim_games)
    st.session_state.f_wins = st.slider("Wins in that Span", 0, st.session_state.sim_games, st.session_state.f_wins)
    if st.button("Update Bracket"): st.rerun()

if st.button("⚙️ Simulation Settings"): open_sim()

# 4. ADVANCED BRACKET LOGIC
df = df_base.copy()
for i, row in df.iterrows():
    if row['team'] == st.session_state.get('target_team', ''):
        df.at[i, 'pts'] += (st.session_state.f_wins * 2)
    else:
        pace = row['pts'] / (row['gp'] * 2)
        df.at[i, 'pts'] += round(pace * (st.session_state.sim_games * 2))

def get_bracket_seeds(conf_name):
    conf_df = df[df['conf'] == conf_name].sort_values('pts', ascending=False)
    
    # 1. Get Top 3 per division
    divisions = conf_df['div'].unique()
    div_winners = {}
    div_matchups = {}
    
    for d in divisions:
        d_teams = conf_df[df['div'] == d].sort_values('pts', ascending=False)
        # Divisional Seeds 1, 2, 3
        div_winners[d] = d_teams.iloc[0]
        div_matchups[d] = (d_teams.iloc[1], d_teams.iloc[2]) # 2 vs 3

    # 2. Wild Cards (next 2 best regardless of division)
    auto_teams = []
    for d in divisions: auto_teams.extend(conf_df[df['div'] == d].head(3)['team'].tolist())
    
    wc_df = conf_df[~conf_df['team'].isin(auto_teams)].sort_values('pts', ascending=False)
    wc1, wc2 = wc_df.iloc[0], wc_df.iloc[1]

    # 3. Matchup 1vWC Logic (Best Div winner plays WC2)
    d1_lead, d2_lead = list(div_winners.values())[0], list(div_winners.values())[1]
    if d1_lead['pts'] >= d2_lead['pts']:
        m1 = (d1_lead, wc2, f"{d1_lead['div'][0]}1", "WC2")
        m2 = (d2_lead, wc1, f"{d2_lead['div'][0]}1", "WC1")
    else:
        m1 = (d2_lead, wc2, f"{d2_lead['div'][0]}1", "WC2")
        m2 = (d1_lead, wc1, f"{d1_lead['div'][0]}1", "WC1")
        
    return m1, m2, div_matchups

# 5. RENDER THE TREE
def render_matchup(t1, t2, s1, s2):
    st.markdown(f"""
    <div class="matchup-card">
        <div class="team-row">
            <div class="team-label"><span class="seed-tag">{s1}</span><img src="{t1['logo']}" width="20"> {t1['team'].upper()}</div>
            <div class="pts">{int(t1['pts'])}</div>
        </div>
        <div class="vs-line">VS</div>
        <div class="team-row">
            <div class="team-label"><span class="seed-tag">{s2}</span><img src="{t2['logo']}" width="20"> {t2['team'].upper()}</div>
            <div class="pts">{int(t2['pts'])}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

col_e, col_w = st.columns(2)

def draw_conference(name, col):
    m1, m2, divs = get_bracket_seeds(name)
    with col:
        st.subheader(f"{name.upper()} CONFERENCE")
        
        # Division 1 Bracket
        st.markdown(f'<div class="div-header">{m1[0]["div"]} Division</div>', unsafe_allow_html=True)
        render_matchup(m1[0], m1[1], m1[2], m1[3])
        d1_2, d1_3 = divs[m1[0]['div']]
        render_matchup(d1_2, d1_3, f"{m1[0]['div'][0]}2", f"{m1[0]['div'][0]}3")
        
        # Division 2 Bracket
        st.markdown(f'<div class="div-header">{m2[0]["div"]} Division</div>', unsafe_allow_html=True)
        render_matchup(m2[0], m2[1], m2[2], m2[3])
        d2_2, d2_3 = divs[m2[0]['div']]
        render_matchup(d2_2, d2_3, f"{m2[0]['div'][0]}2", f"{m2[0]['div'][0]}3")

draw_conference("Eastern", col_e)
draw_conference("Western", col_w)

st.markdown(f'<div class="timestamp">LAST UPDATED: {datetime.now().strftime("%I:%M %p")} ET | LIVE 2026 STANDINGS</div>', unsafe_allow_html=True)

