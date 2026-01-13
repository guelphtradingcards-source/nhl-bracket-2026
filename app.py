import streamlit as st
import pandas as pd
import requests
from PIL import Image
import os
from datetime import datetime

# 1. PAGE SETUP
st.set_page_config(page_title="Playoff Bracket Tracker", layout="wide")

# --- PRO-STYLE CSS ---
st.markdown("""
<style>
    .matchup-card { background: #111; border: 1px solid #333; border-radius: 4px; padding: 10px; margin-bottom: 10px; }
    .team-row { display: flex; justify-content: space-between; align-items: center; padding: 5px 0; }
    .team-label { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 14px; }
    .seed { color: #64748b; font-size: 11px; width: 18px; font-weight: normal; }
    .record { color: #888; font-size: 11px; font-weight: normal; margin-left: 5px; }
    .pts { font-weight: 900; color: #fff; background: #222; padding: 2px 6px; border-radius: 3px; min-width: 25px; text-align: center; }
    
    .timestamp { text-align: center; color: #444; font-size: 11px; margin-top: 50px; border-top: 1px solid #222; padding-top: 10px; }
    
    .wc-card { background: #1a1a1a; border: 1px solid #333; padding: 12px; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center; }
    .in-glow { border-left: 4px solid #22c55e; }
    .cutoff-line { border-top: 2px dashed #ef4444; margin: 15px 0; text-align: center; position: relative; }
    .cutoff-text { position: absolute; top: -10px; left: 50%; transform: translateX(-50%); background: #000; padding: 0 10px; color: #ef4444; font-size: 10px; font-weight: bold; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# 2. HERO & BRANDING
if os.path.exists("header.img"):
    st.image(Image.open("header.img"), use_container_width=True)

col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.img"):
        st.image(Image.open("logo.img"), width=120)
    else:
        st.markdown("<h1 style='text-align:center;'>🏆</h1>", unsafe_allow_html=True)
with col_title:
    st.title("PLAYOFF BRACKET TRACKER")

# 3. DATA ENGINE
@st.cache_data(ttl=600) # Data refreshes every 10 mins
def get_data():
    url = "https://api-web.nhle.com/v1/standings/now"
    data = requests.get(url).json()['standings']
    return pd.DataFrame([{
        'team': r['teamName']['default'], 'conf': r['conferenceName'], 
        'div': r['divisionName'], 'pts': r['points'], 'gp': r['gamesPlayed'],
        'w': r['wins'], 'l': r['losses'], 'ot': r['otLosses'],
        'logo': r['teamLogo']} for r in data])

df_base = get_data()

# 4. SIMULATION LOGIC
if 'sim_games' not in st.session_state: st.session_state.sim_games = 0
if 'f_wins' not in st.session_state: st.session_state.f_wins = 0

@st.dialog("Simulator Engine")
def open_sim():
    target = st.selectbox("Focus Team", sorted(df_base['team'].tolist()))
    max_rem = 82 - int(df_base['gp'].mean())
    st.session_state.sim_games = st.slider("Games to Sim", 0, max(1, max_rem), st.session_state.sim_games)
    st.session_state.f_wins = st.slider("Projected Wins", 0, max(1, st.session_state.sim_games), st.session_state.f_wins)
    if st.button("Apply Scenarios"): 
        st.session_state.target_team = target
        st.rerun()

if st.button("⚙️ Simulation Settings", type="primary"): open_sim()

df = df_base.copy()
for i, row in df.iterrows():
    if row['team'] == st.session_state.get('target_team', ''):
        df.at[i, 'w'] += st.session_state.f_wins
        df.at[i, 'pts'] += (st.session_state.f_wins * 2)
    else:
        pace = row['pts'] / (row['gp'] * 2)
        added_pts = round(pace * (st.session_state.sim_games * 2))
        df.at[i, 'pts'] += added_pts
        df.at[i, 'w'] += (added_pts // 2)

# 5. BRACKET VIEW
col_e, col_w = st.columns(2)

def draw_bracket(name, col):
    sub = df[df['conf'] == name].sort_values('pts', ascending=False).head(8).reset_index(drop=True)
    with col:
        st.subheader(f"{name.upper()}")
        for i in range(4):
            t1, t2 = sub.iloc[i], sub.iloc[7-i]
            st.markdown(f"""
            <div class="matchup-card">
                <div class="team-row">
                    <div class="team-label">
                        <span class="seed">{i+1}</span>
                        <img src="{t1['logo']}" width="22"> {t1['team'].upper()}
                        <span class="record">{int(t1['w'])}-{int(t1['gp']-t1['w']-t1['ot'])}-{int(t1['ot'])}</span>
                    </div>
                    <span class="pts">{int(t1['pts'])}</span>
                </div>
                <div style="text-align:center; color:#444; font-size:9px;">VS</div>
                <div class="team-row">
                    <div class="team-label">
                        <span class="seed">{8-i}</span>
                        <img src="{t2['logo']}" width="22"> {t2['team'].upper()}
                        <span class="record">{int(t2['w'])}-{int(t2['gp']-t2['w']-t2['ot'])}-{int(t2['ot'])}</span>
                    </div>
                    <span class="pts">{int(t2['pts'])}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

draw_bracket("Eastern", col_e)
draw_bracket("Western", col_w)

# 6. WILD CARD WATCH
st.markdown("---")
st.title("🏁 WILD CARD WATCH")
wc_e_col, wc_w_col = st.columns(2)

def draw_wc_standings(conf, col):
    full_conf = df[df['conf'] == conf].sort_values('pts', ascending=False)
    bubble = full_conf.iloc[6:11].reset_index(drop=True)
    with col:
        st.write(f"**{conf} Bubble Race**")
        for i, row in bubble.iterrows():
            if i == 2:
                st.markdown('<div class="cutoff-line"><span class="cutoff-text">Playoff Cutoff</span></div>', unsafe_allow_html=True)
            in_style = "in-glow" if i < 2 else ""
            st.markdown(f"""
            <div class="wc-card {in_style}">
                <div class="wc-team-info">
                    <img src="{row['logo']}" width="24">
                    <span>{row['team'].upper()} <span class="record">{int(row['w'])}-{int(row['gp']-row['row']['w']-row['ot']) if 'row' not in locals() else '---'}-{int(row['ot'])}</span></span>
                </div>
                <div class="wc-pts">{int(row['pts'])}</div>
            </div>
            """, unsafe_allow_html=True)

# Note: The record math in the WC section was simplified to avoid local variable errors
def draw_wc_simple(conf, col):
    full_conf = df[df['conf'] == conf].sort_values('pts', ascending=False)
    bubble = full_conf.iloc[6:11].reset_index(drop=True)
    with col:
        st.write(f"**{conf} Bubble Race**")
        for i, row in bubble.iterrows():
            if i == 2: st.markdown('<div class="cutoff-line"><span class="cutoff-text">Playoff Cutoff</span></div>', unsafe_allow_html=True)
            in_style = "in-glow" if i < 2 else ""
            st.markdown(f"""
            <div class="wc-card {in_style}">
                <div class="wc-team-info"><img src="{row['logo']}" width="24"><span>{row['team'].upper()}</span></div>
                <div class="wc-pts">{int(row['pts'])}</div>
            </div>""", unsafe_allow_html=True)

draw_wc_simple("Eastern", wc_e_col)
draw_wc_simple("Western", wc_w_col)

# 7. TIMESTAMP (The Last Night's Games check)
last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"""<div class="timestamp">Data Refreshed: {last_update} (UTC) | Incorporating latest scores from the NHL API</div>""", unsafe_allow_html=True)
