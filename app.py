import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components

st.set_page_config(page_title="NHL Bracket 2026", layout="wide")

# --- DATA FETCH ---
@st.cache_data(ttl=3600)
def get_data():
    url = "https://api-web.nhle.com/v1/standings/now"
    data = requests.get(url).json()['standings']
    return pd.DataFrame([{
        'team': r['teamName']['default'], 'conf': r['conferenceName'], 
        'pts': r['points'], 'gp': r['gamesPlayed'], 'logo': r['teamLogo']} for r in data])

df = get_data()

# --- SIDEBAR ---
st.sidebar.header("Settings")
sim_games = st.sidebar.slider("Simulate Games", 0, 30, 0)
target = st.sidebar.selectbox("Focus Team", sorted(df['team'].tolist()))

# --- PACE CALCULATION ---
df['pace'] = df['pts'] / (df['gp'] * 2)
df['proj_pts'] = round(df['pts'] + (df['pace'] * (sim_games * 2)))

# Sort for Seeding
east = df[df['conf'] == 'Eastern'].sort_values('proj_pts', ascending=False).head(8).reset_index()
west = df[df['conf'] == 'Western'].sort_values('proj_pts', ascending=False).head(8).reset_index()

# --- HTML/CSS BRACKET DESIGN ---
def generate_matchup(t1, t2, seed_h, seed_l):
    color1 = "#fbbf24" if t1['team'] == target else "#f8fafc"
    color2 = "#fbbf24" if t2['team'] == target else "#f8fafc"
    return f"""
    <div style="background:#1e293b; border:1px solid #334155; border-radius:4px; margin:10px 0; width:220px;">
        <div style="display:flex; justify-content:space-between; padding:8px; border-bottom:1px solid #334155; color:{color1}; font-weight:bold;">
            <span><small style="color:#64748b; margin-right:5px;">{seed_h}</small>{t1['team']}</span>
            <span>{int(t1['proj_pts'])}</span>
        </div>
        <div style="display:flex; justify-content:space-between; padding:8px; color:{color2}; font-weight:bold;">
            <span><small style="color:#64748b; margin-right:5px;">{seed_l}</small>{t2['team']}</span>
            <span>{int(t2['proj_pts'])}</span>
        </div>
    </div>
    """

# Build the final HTML string
bracket_html = f"""
<div style="background:#0b0f19; padding:20px; font-family:sans-serif; display:flex; justify-content:space-around; align-items:center; border-radius:15px;">
    <div style="display:flex; flex-direction:column; gap:20px;">
        <h3 style="color:#38bdf8; text-align:center; font-size:14px;">EASTERN CONFERENCE</h3>
        {generate_matchup(east.iloc[0], east.iloc[7], 1, 8)}
        {generate_matchup(east.iloc[3], east.iloc[4], 4, 5)}
        {generate_matchup(east.iloc[2], east.iloc[5], 3, 6)}
        {generate_matchup(east.iloc[1], east.iloc[6], 2, 7)}
    </div>

    <div style="text-align:center;">
        <div style="font-size:40px;">🏆</div>
        <div style="color:#38bdf8; font-weight:900; letter-spacing:2px; margin-top:10px;">STANLEY CUP</div>
        <div style="color:#64748b; font-size:12px;">2026 FINALS</div>
    </div>

    <div style="display:flex; flex-direction:column; gap:20px;">
        <h3 style="color:#38bdf8; text-align:center; font-size:14px;">WESTERN CONFERENCE</h3>
        {generate_matchup(west.iloc[0], west.iloc[7], 1, 8)}
        {generate_matchup(west.iloc[3], west.iloc[4], 4, 5)}
        {generate_matchup(west.iloc[2], west.iloc[5], 3, 6)}
        {generate_matchup(west.iloc[1], west.iloc[6], 2, 7)}
    </div>
</div>
"""

# DISPLAY
st.title("NHL Playoff Bracket Predictor")
components.html(bracket_html, height=650)
