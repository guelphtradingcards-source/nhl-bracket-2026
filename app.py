import streamlit as st
import pandas as pd
import requests

# Page Config
st.set_page_config(page_title="NHL 2026 Bracket Predictor", layout="wide")

# --- NHL DESIGNER CSS ---
st.markdown("""
<style>
    /* Main Bracket Container */
    .bracket-wrapper {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background-color: #0b0f19;
        padding: 40px 20px;
        border-radius: 20px;
        overflow-x: auto;
    }

    /* Conference Columns */
    .conference {
        display: flex;
        flex-direction: column;
        justify-content: space-around;
        height: 600px;
        width: 300px;
    }

    /* Matchup Box */
    .matchup-container {
        display: flex;
        flex-direction: column;
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 4px;
        width: 100%;
        position: relative;
    }

    /* The "Connectors" (Lines) */
    .matchup-container::after {
        content: "";
        position: absolute;
        top: 50%;
        width: 20px;
        height: 2px;
        background: #334155;
    }
    
    .east-matchup::after { right: -20px; }
    .west-matchup::after { left: -20px; }

    .team-slot {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 12px;
        height: 40px;
    }
    
    .team-slot:first-child { border-bottom: 1px solid #334155; }
    
    .team-name {
        font-size: 13px;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 8px;
        color: #f8fafc;
    }

    .seed { color: #64748b; font-size: 10px; width: 15px; }
    .score { font-weight: 900; color: #38bdf8; }
    .focus-team { color: #fbbf24 !important; }
    
    /* Stanley Cup Center Area */
    .cup-center {
        text-align: center;
        width: 200px;
        display: flex;
        flex-direction: column;
        align-items: center;
        color: #94a3b8;
    }
</style>
""", unsafe_allow_html=True)

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

# --- SIDEBAR ---
st.sidebar.header("🏆 Bracket Settings")
sim_games = st.sidebar.slider("Simulate Next X Games", 0, 35, 0)
target = st.sidebar.selectbox("Focus Team", sorted(df_base['team'].tolist()), index=df_base['team'].tolist().index("Toronto Maple Leafs"))
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

# --- RENDER BRACKET ---
st.title("🏒 Stanley Cup Playoff Picture")

def get_matchup_html(t1, t2, side, seed_high, seed_low):
    c1 = "focus-team" if t1['team'] == target else ""
    c2 = "focus-team" if t2['team'] == target else ""
    
    return f"""
    <div class="matchup-container {side}-matchup">
        <div class="team-slot">
            <span class="team-name {c1}"><span class="seed">{seed_high}</span><img src="{t1['logo']}" width="20"> {t1['team']}</span>
            <span class="score">{t1['pts']}</span>
        </div>
        <div class="team-slot">
            <span class="team-name {c2}"><span class="seed">{seed_low}</span><img src="{t2['logo']}" width="20"> {t2['team']}</span>
            <span class="score">{t2['pts']}</span>
        </div>
    </div>
    """

# Prepare Standings
east = df[df['conf'] == 'Eastern'].sort_values('pts', ascending=False).head(8).reset_index()
west = df[df['conf'] == 'Western'].sort_values('pts', ascending=False).head(8).reset_index()

# Layout
bracket_html = f"""
<div class="bracket-wrapper">
    <div class="conference">
        {get_matchup_html(east.iloc[0], east.iloc[7], "east", 1, 8)}
        {get_matchup_html(east.iloc[3], east.iloc[4], "east", 4, 5)}
        {get_matchup_html(east.iloc[2], east.iloc[5], "east", 3, 6)}
        {get_matchup_html(east.iloc[1], east.iloc[6], "east", 2, 7)}
    </div>

    <div class="cup-center">
        <img src="https://searchlogovector.com/wp-content/uploads/2018/05/stanley-cup-playoffs-logo-vector.png" width="120" style="opacity:0.5">
        <div style="margin-top:20px; font-weight:800; color:#38bdf8;">FINAL ROUND</div>
        <div style="font-size:10px; margin-top:5px;">2026 PROJECTION</div>
    </div>

    <div class="conference">
        {get_matchup_html(west.iloc[0], west.iloc[7], "west", 1, 8)}
        {get_matchup_html(west.iloc[3], west.iloc[4], "west", 4, 5)}
        {get_matchup_html(west.iloc[2], west.iloc[5], "west", 3, 6)}
        {get_matchup_html(west.iloc[1], west.iloc[6], "west", 2, 7)}
    </div>
</div>
"""

st.markdown(bracket_html, unsafe_allow_html=True)
