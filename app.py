import streamlit as st
import pandas as pd
import requests
from PIL import Image
import os
from datetime import datetime
import streamlit.components.v1 as components

# 1. PAGE SETUP
st.set_page_config(page_title="Playoff Bracket Tracker", layout="wide")

# 2. DATA ENGINE
@st.cache_data(ttl=600)
def get_nhl_data():
    url = "https://api-web.nhle.com/v1/standings/now"
    data = requests.get(url).json()['standings']
    return pd.DataFrame([{
        'team': r['teamName']['default'], 'conf': r['conferenceName'], 
        'div': r['divisionName'], 'pts': r['points'], 'gp': r['gamesPlayed'],
        'w': r['wins'], 'l': r['losses'], 'ot': r['otLosses'],
        'logo': r['teamLogo']} for r in data])

df_base = get_nhl_data()

# 3. BRANDING & HERO
if os.path.exists("header.img"):
    st.image(Image.open("header.img"), use_container_width=True)

# 4. SIMULATION MODAL
if 'sim_games' not in st.session_state: st.session_state.sim_games = 0
if 'f_wins' not in st.session_state: st.session_state.f_wins = 0

@st.dialog("Simulator Engine")
def open_sim():
    st.session_state.target_team = st.selectbox("Focus Team", sorted(df_base['team'].tolist()))
    max_rem = 82 - int(df_base['gp'].mean())
    st.session_state.sim_games = st.slider("Games to Sim", 0, max(1, max_rem), st.session_state.sim_games)
    st.session_state.f_wins = st.slider("Projected Wins", 0, max(1, st.session_state.sim_games), st.session_state.f_wins)
    if st.button("Apply Scenarios"): st.rerun()

col_logo, col_btn = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.img"): st.image(Image.open("logo.img"), width=120)
with col_btn:
    st.title("PLAYOFF BRACKET TRACKER")
    if st.button("⚙️ Simulation Settings", type="primary"): open_sim()

# 5. PREDICTIVE CALCULATION
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

# --- DIVISIONAL SEEDING LOGIC ---
def get_bracket_seeds(conf_name):
    conf_df = df[df['conf'] == conf_name].sort_values('pts', ascending=False)
    divs = conf_df['div'].unique()
    div_data = {}
    for d in divs:
        d_teams = conf_df[conf_df['div'] == d].sort_values('pts', ascending=False)
        div_data[d] = d_teams.head(3)
    
    auto_teams = pd.concat(div_data.values())
    wc = conf_df[~conf_df['team'].isin(auto_teams['team'])].sort_values('pts', ascending=False).head(2)
    
    d1_name, d2_name = list(div_data.keys())
    d1_win, d2_win = div_data[d1_name].iloc[0], div_data[d2_name].iloc[0]
    
    # Best Div Winner plays WC2
    if d1_win['pts'] >= d2_win['pts']:
        m1 = (d1_win, wc.iloc[1], f"{d1_name[0]}1", "WC2")
        m2 = (d2_win, wc.iloc[0], f"{d2_name[0]}1", "WC1")
    else:
        m1 = (d2_win, wc.iloc[1], f"{d2_name[0]}1", "WC2")
        m2 = (d1_win, wc.iloc[0], f"{d1_name[0]}1", "WC1")
    
    return m1, m2, div_data

# 6. TREE-STYLE CSS & HTML
bracket_css = """
<style>
    body { background-color: #000; color: white; font-family: 'Arial', sans-serif; }
    .bracket-tree { display: flex; justify-content: center; align-items: center; gap: 10px; padding: 20px; }
    .conf-bracket { display: flex; flex-direction: column; gap: 30px; width: 300px; }
    .matchup { background: #111; border: 1px solid #333; border-radius: 4px; overflow: hidden; }
    .team { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; border-bottom: 1px solid #222; }
    .team:last-child { border-bottom: none; }
    .name-wrap { display: flex; align-items: center; gap: 10px; font-weight: bold; font-size: 13px; }
    .seed { color: #666; font-size: 10px; width: 25px; font-weight: 900; }
    .rec { color: #555; font-size: 10px; font-weight: normal; margin-left: 5px; }
    .pts { font-weight: 900; color: #fff; background: #222; padding: 2px 6px; border-radius: 2px; }
    .cup-zone { text-align: center; width: 150px; }
</style>
"""

def build_matchup_html(t1, t2, s1, s2):
    def rec(t): return f"{int(t['w'])}-{int(t['gp']-t['w']-t['ot'])}-{int(t['ot'])}"
    return f"""
    <div class="matchup">
        <div class="team">
            <div class="name-wrap"><span class="seed">{s1}</span><img src="{t1['logo']}" width="20"> {t1['team'].upper()}<span class="rec">{rec(t1)}</span></div>
            <div class="pts">{int(t1['pts'])}</div>
        </div>
        <div class="team">
            <div class="name-wrap"><span class="seed">{s2}</span><img src="{t2['logo']}" width="20"> {t2['team'].upper()}<span class="rec">{rec(t2)}</span></div>
            <div class="pts">{int(t2['pts'])}</div>
        </div>
    </div>
    """

# Prepare Brackets
e_m1, e_m2, e_divs = get_bracket_seeds("Eastern")
w_m1, w_m2, w_divs = get_bracket_seeds("Western")

def get_conf_html(m1, m2, divs):
    # Round 1 Divisional Pairings (2v3)
    d1_name = m1[0]['div']
    d1_2, d1_3 = divs[d1_name].iloc[1], divs[d1_name].iloc[2]
    d2_name = m2[0]['div']
    d2_2, d2_3 = divs[d2_name].iloc[1], divs[d2_name].iloc[2]
    
    return f"""
    <div class="conf-bracket">
        <div style="color:#444; font-size:10px; text-align:center; border-bottom:1px solid #333; margin-bottom:5px;">{d1_name.upper()}</div>
        {build_matchup_html(m1[0], m1[1], m1[2], m1[3])}
        {build_matchup_html(d1_2, d1_3, f"{d1_name[0]}2", f"{d1_name[0]}3")}
        <div style="color:#444; font-size:10px; text-align:center; border-bottom:1px solid #333; margin-bottom:5px; margin-top:15px;">{d2_name.upper()}</div>
        {build_matchup_html(m2[0], m2[1], m2[2], m2[3])}
        {build_matchup_html(d2_2, d2_3, f"{d2_name[0]}2", f"{d2_name[0]}3")}
    </div>
    """

# 7. RENDER FULL PAGE
tree_html = f"""
{bracket_css}
<div class="bracket-tree">
    {get_conf_html(e_m1, e_m2, e_divs)}
    <div class="cup-zone">
        <div style="font-size:60px;">🏆</div>
        <div style="font-weight:900; letter-spacing:3px; margin-top:10px; color:#fff;">2026</div>
        <div style="font-size:10px; color:#555;">STANLEY CUP FINAL</div>
    </div>
    {get_conf_html(w_m1, w_m2, w_divs)}
</div>
"""

components.html(tree_html, height=750)

# 8. RESTORED WILD CARD WATCH (FIXED)
st.markdown("---")
st.title("🏁 WILD CARD WATCH")
wc_e, wc_w = st.columns(2)

def draw_wc_cards(conf_name, col):
    full_conf = df[df['conf'] == conf_name].sort_values('pts', ascending=False)
    # Filter out top 3 in each division
    auto_teams = []
    for d in full_conf['div'].unique():
        auto_teams.extend(full_conf[full_conf['div'] == d].sort_values('pts', ascending=False).head(3)['team'].tolist())
    
    wc_race = full_conf[~full_conf['team'].isin(auto_teams)].head(5)
    cutoff = wc_race.iloc[1]['pts'] if len(wc_race) > 1 else 0
    
    with col:
        st.write(f"**{conf_name} Bubble**")
        for i, (idx, row) in enumerate(wc_race.iterrows()):
            if i == 2: st.markdown("<div style='border-top:2px dashed #ef4444; margin:10px 0; text-align:center;'><span style='font-size:10px; color:#ef4444; font-weight:bold;'>CUTOFF</span></div>", unsafe_allow_html=True)
            diff = int(row['pts'] - cutoff)
            status = "✅ IN" if i < 2 else f"❌ {abs(diff)} OUT"
            st.markdown(f"""
            <div style="background:#111; padding:10px; border-radius:4px; border:1px solid #333; display:flex; justify-content:space-between; margin-bottom:5px;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <img src="{row['logo']}" width="20">
                    <span style="font-weight:bold; font-size:14px;">{row['team'].upper()}</span>
                </div>
                <div style="display:flex; align-items:center; gap:15px;">
                    <span style="color:#666; font-size:12px;">{int(row['w'])}-{int(row['gp']-row['w']-row['ot'])}-{int(row['ot'])}</span>
                    <span style="font-size:12px; font-weight:bold;">{status}</span>
                    <span style="background:#222; padding:2px 8px; border-radius:2px; font-weight:900;">{int(row['pts'])}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

draw_wc_cards("Eastern", wc_e)
draw_wc_cards("Western", wc_w)

st.markdown(f"<div style='text-align:center; color:#444; font-size:10px; margin-top:30px;'>DATA REFRESHED: {datetime.now().strftime('%H:%M:%S')} UTC</div>", unsafe_allow_html=True)
