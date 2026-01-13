import streamlit as st
import pandas as pd
import requests

# Page Config
st.set_page_config(page_title="NHL 2026 Playoff Predictor", layout="wide")

# --- CUSTOM CSS (Modern UI) ---
st.markdown("""
<style>
    .matchup-card { background: #1e293b; border-radius: 10px; padding: 15px; border-left: 5px solid #38bdf8; margin-bottom: 15px; }
    .team-row { display: flex; justify-content: space-between; align-items: center; margin: 5px 0; }
    .pts { color: #38bdf8; font-weight: 900; font-size: 1.2rem; }
    .focus-team { color: #fbbf24 !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- DATA FETCHING ---
@st.cache_data(ttl=3600)
def get_data():
    # Fetching real-time 2026 NHL data
    url = "https://api-web.nhle.com/v1/standings/now"
    resp = requests.get(url).json()
    return pd.DataFrame([{
        'team': r['teamName']['default'], 'conf': r['conferenceName'], 
        'pts': r['points'], 'gp': r['gamesPlayed'],
        'w': r['wins'], 'l': r['losses'], 'ot': r['otLosses'],
        'logo': r['teamLogo']} for r in resp['standings']])

df_base = get_data()

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🏆 Predictor Settings")
# FIX: Set the default value (the 3rd number) to 0
sim_games = st.sidebar.slider("Simulate Next X Games", min_value=0, max_value=35, value=0)

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Focus Team")
target = st.sidebar.selectbox("Select Team", sorted(df_base['team'].tolist()), index=df_base['team'].tolist().index("Toronto Maple Leafs"))

# FIX: Set default Wins/OTL to 0 so the bracket is clean on load
f_wins = st.sidebar.slider(f"{target} Wins", 0, 35, 0)
f_otl = st.sidebar.slider(f"{target} OT Losses", 0, 10, 0)

# --- PREDICTIVE LOGIC ---
df = df_base.copy()
df['pace'] = df['pts'] / (df['gp'] * 2)

for i, row in df.iterrows():
    if row['team'] == target:
        # Prevent simulating more wins than games
        actual_sim = max(sim_games, f_wins + f_otl) 
        df.at[i, 'w'] += f_wins
        df.at[i, 'ot'] += f_otl
        df.at[i, 'l'] += max(0, sim_games - f_wins - f_otl)
        df.at[i, 'pts'] += (f_wins * 2) + f_otl
    else:
        # Predict others based on current season pace
        add_pts = round(row['pace'] * (sim_games * 2))
        df.at[i, 'pts'] += add_pts
        df.at[i, 'w'] += (add_pts // 2)
        df.at[i, 'ot'] += (add_pts % 2)
        df.at[i, 'l'] += max(0, sim_games - (add_pts // 2) - (add_pts % 2))

# --- RENDER BRACKET ---
st.title("🏒 2026 NHL Predictive Playoff Bracket")
if sim_games == 0:
    st.caption("Showing CURRENT NHL Playoff Bracket (as of Jan 13, 2026).")
else:
    st.caption(f"Projecting standings for {sim_games} games into the future.")

col1, col2 = st.columns(2)

def draw_conf(conf_name, column):
    # Seeding Logic: 1v8, 2v7, 3v6, 4v5
    sub = df[df['conf'] == conf_name].sort_values('pts', ascending=False).head(8).reset_index()
    with column:
        st.subheader(conf_name)
        for i in range(4):
            t1, t2 = sub.iloc[i], sub.iloc[7-i]
            c1 = "focus-team" if t1['team'] == target else ""
            c2 = "focus-team" if t2['team'] == target else ""
            
            st.markdown(f"""
            <div class="matchup-card">
                <div class="team-row">
                    <span class="{c1}"><img src="{t1['logo']}" width="25"> {t1['team']} ({t1['w']}-{t1['l']}-{t1['ot']})</span>
                    <span class="pts">{t1['pts']}</span>
                </div>
                <div style="text-align:center; color:#475569; font-size:10px;">VS</div>
                <div class="team-row">
                    <span class="{c2}"><img src="{t2['logo']}" width="25"> {t2['team']} ({t2['w']}-{t2['l']}-{t2['ot']})</span>
                    <span class="pts">{t2['pts']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

draw_conf("Eastern", col1)
draw_conf("Western", col2)
