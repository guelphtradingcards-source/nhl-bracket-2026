import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components

# Page setup
st.set_page_config(page_title="NHL Bracket 2026", layout="wide")

# --- DATA FETCHING ---
@st.cache_data(ttl=3600)
def get_data():
    url = "https://api-web.nhle.com/v1/standings/now"
    resp = requests.get(url).json()
    return pd.DataFrame([{
        'team': r['teamName']['default'], 'conf': r['conferenceName'], 
        'pts': r['points'], 'gp': r['gamesPlayed'],
        'w': r['wins'], 'l': r['losses'], 'ot': r['otLosses'],
        'logo': r['teamLogo']} for r in resp['standings']])

df_base = get_data()

# --- SIDEBAR CONTROLS ---
st.sidebar.title("NHL BRACKET SETTINGS")
sim_games = st.sidebar.slider("Simulate Next X Games", 0, 30, 0)
target = st.sidebar.selectbox("Select Focus Team", sorted(df_base['team'].tolist()), index=df_base['team'].tolist().index("Toronto Maple Leafs"))
f_wins = st.sidebar.slider(f"{target} Wins", 0, 35, 0)
f_otl = st.sidebar.slider(f"{target} OT Losses", 0, 10, 0)

# --- PREDICTIVE LOGIC ---
df = df_base.copy()
df['pace'] = df['pts'] / (df['gp'] * 2)

for i, row in df.iterrows():
    if row['team'] == target:
        df.at[i, 'w'] += f_wins
        df.at[i, 'ot'] += f_otl
        df.at[i, 'pts'] += (f_wins * 2) + f_otl
    else:
        add_pts = round(row['pace'] * (sim_games * 2))
        df.at[i, 'pts'] += add_pts
        df.at[i, 'w'] += (add_pts // 2)
        df.at[i, 'ot'] += (add_pts % 2)

# Seeding
east = df[df['conf'] == 'Eastern'].sort_values('pts', ascending=False).head(8).reset_index()
west = df[df['conf'] == 'Western'].sort_values('pts', ascending=False).head(8).reset_index()

# --- CSS FOR NHL BRANDING & MOBILE ---
# Using NHL Official Colors: #000000 (Black), #D0D3D4 (Light Silver), #FFFFFF (White)
nhl_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Condensed:wght@700&family=Roboto:wght@400;900&display=swap');
    
    body { background-color: #111 !important; color: white; font-family: 'Roboto', sans-serif; }
    
    .bracket-container {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 40px;
        background: #000;
        padding: 20px;
        border-radius: 8px;
    }

    .conference-section {
        display: flex;
        flex-direction: column;
        gap: 15px;
        min-width: 280px;
    }

    .conf-header {
        background: #D0D3D4;
        color: #000;
        text-align: center;
        font-family: 'Roboto Condensed', sans-serif;
        font-weight: bold;
        padding: 5px;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .matchup-box {
        background: #222;
        border: 1px solid #444;
        border-radius: 2px;
        overflow: hidden;
    }

    .team-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 12px;
        height: 45px;
        border-bottom: 1px solid #333;
    }
    
    .team-row:last-child { border-bottom: none; }

    .team-label { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 14px; color: #eee; }
    .seed { color: #888; font-size: 11px; width: 15px; }
    .pts { color: #fff; font-weight: 900; background: #333; padding: 2px 8px; border-radius: 3px; min-width: 30px; text-align: center; }
    
    .focus-team { background: #444 !important; border-left: 4px solid #fff; }
    .focus-team .team-label { color: #fbbf24 !important; }

    /* Center Final Branding */
    .final-center {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        min-width: 200px;
    }
    
    @media (max-width: 800px) {
        .bracket-container { flex-direction: column; align-items: center; }
        .final-center { order: -1; margin-bottom: 20px; }
    }
</style>
"""

def generate_matchup(t1, t2, s_h, s_l):
    f1 = "focus-team" if t1['team'] == target else ""
    f2 = "focus-team" if t2['team'] == target else ""
    return f"""
    <div class="matchup-box">
        <div class="team-row {f1}">
            <div class="team-label"><span class="seed">{s_h}</span><img src="{t1['logo']}" width="25"> {t1['team'].upper()}</div>
            <div class="pts">{int(t1['pts'])}</div>
        </div>
        <div class="team-row {f2}">
            <div class="team-label"><span class="seed">{s_l}</span><img src="{t2['logo']}" width="25"> {t2['team'].upper()}</div>
            <div class="pts">{int(t2['pts'])}</div>
        </div>
    </div>
    """

# --- BUILD PAGE ---
st.title("STANLEY CUP PLAYOFF BRACKET")
st.markdown(f"**Live Projection: {sim_games} Game Prediction Window**", help="Adjust simulation in the sidebar.")

# Pairings 1v8, 2v7, 3v6, 4v5
bracket_html = f"""
{nhl_css}
<div class="bracket-container">
    <div class="conference-section">
        <div class="conf-header">Eastern Conference</div>
        {generate_matchup(east.iloc[0], east.iloc[7], 1, 8)}
        {generate_matchup(east.iloc[3], east.iloc[4], 4, 5)}
        {generate_matchup(east.iloc[2], east.iloc[5], 3, 6)}
        {generate_matchup(east.iloc[1], east.iloc[6], 2, 7)}
    </div>

    <div class="final-center">
        <img src="https://www-league.nhlstatic.com/builds/site-core/6be5f75e5dca800d5edb9b07cd46432bbadd7828_1457019658/images/footer/shield_dark_en.svg" width="80">
        <h2 style="margin-top:20px; font-family:'Roboto Condensed'; letter-spacing:3px;">2026</h2>
        <p style="font-size:10px; color:#888;">STANLEY CUP® PLAYOFFS</p>
    </div>

    <div class="conference-section">
        <div class="conf-header">Western Conference</div>
        {generate_matchup(west.iloc[0], west.iloc[7], 1, 8)}
        {generate_matchup(west.iloc[3], west.iloc[4], 4, 5)}
        {generate_matchup(west.iloc[2], west.iloc[5], 3, 6)}
        {generate_matchup(west.iloc[1], west.iloc[6], 2, 7)}
    </div>
</div>
"""

components.html(bracket_html, height=800, scrolling=True)
