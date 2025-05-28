import streamlit as st
import pandas as pd
import requests
from scrape_stats import run_scrape
from get_lineups import get_players_and_pitchers

# --- CONFIG ---

st.set_page_config(page_title="Hib's Tool", layout="wide")
st.title("⚾ Hib's Batter Data Tool")

with st.expander("ℹ️ How to Use", expanded=True):
    st.markdown("""
    **Welcome to Hib's Tool!**
    Disclaimer: Only will display full data for games in which lineups are currently out.

    1. Choose a matchup from today's MLB games.
    2. Choose how many stats you want to weight (1–4).
    3. Select the stat types and set your weights.
    4. Click **Run Model + Rank** to view the top hitters.

    Optional: Click **Show All Batter Stats** to see raw data (including `n/a`s).
    """)

# --- MATCHUP DROPDOWN ---

TEAM_NAME_MAP = {
    "ARI": "Arizona Diamondbacks", "ATL": "Atlanta Braves", "BAL": "Baltimore Orioles",
    "BOS": "Boston Red Sox", "CHC": "Chicago Cubs", "CHW": "Chicago White Sox",
    "CIN": "Cincinnati Reds", "CLE": "Cleveland Guardians", "COL": "Colorado Rockies",
    "DET": "Detroit Tigers", "HOU": "Houston Astros", "KCR": "Kansas City Royals",
    "LAA": "Los Angeles Angels", "LAD": "Los Angeles Dodgers", "MIA": "Miami Marlins",
    "MIL": "Milwaukee Brewers", "MIN": "Minnesota Twins", "NYM": "New York Mets",
    "NYY": "New York Yankees", "OAK": "Oakland Athletics", "PHI": "Philadelphia Phillies",
    "PIT": "Pittsburgh Pirates", "SDP": "San Diego Padres", "SEA": "Seattle Mariners",
    "SFG": "San Francisco Giants", "STL": "St. Louis Cardinals", "TBR": "Tampa Bay Rays",
    "TEX": "Texas Rangers", "TOR": "Toronto Blue Jays", "WSH": "Washington Nationals"
}
REVERSE_MAP = {v: k for k, v in TEAM_NAME_MAP.items()}

def get_today_matchups():
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}"
    data = requests.get(url).json()
    matchups = []
    for date in data.get("dates", []):
        for game in date.get("games", []):
            away_name = game["teams"]["away"]["team"]["name"]
            home_name = game["teams"]["home"]["team"]["name"]
            if away_name in REVERSE_MAP and home_name in REVERSE_MAP:
                away_abbr = REVERSE_MAP[away_name]
                home_abbr = REVERSE_MAP[home_name]
                matchup_str = f"{away_abbr} @ {home_abbr}"
                matchups.append((matchup_str, away_abbr, home_abbr))
    return matchups

matchups = get_today_matchups()
if not matchups:
    st.error("No MLB matchups found for today.")
    st.stop()

matchup_strs = [m[0] for m in matchups]
selected_matchup = st.selectbox("Select Today's Matchup", matchup_strs)
team1, team2 = [(a, b) for m, a, b in matchups if m == selected_matchup][0]

# --- STAT SELECTION ---

st.markdown("### 🎯 Stat Weights")
num_stats = st.slider("How many stats do you want to weight?", 1, 4, 2)

available_stats = ["EV", "Barrel %", "xSLG", "FB %", "RightFly", "LeftFly"]

weight_defaults = {
    1: [1.0],
    2: [0.5, 0.5],
    3: [0.33, 0.33, 0.34],
    4: [0.25, 0.25, 0.25, 0.25]
}.get(num_stats, [1.0])

stat_selections = []
weight_inputs = []

for i in range(num_stats):
    cols = st.columns([2, 1])
    stat = cols[0].selectbox(f"Stat {i+1}", available_stats, key=f"stat_{i}")
    weight = cols[1].number_input(f"Weight {i+1}", min_value=0.0, max_value=1.0, value=weight_defaults[i], step=0.01, key=f"w_{i}")
    stat_selections.append(stat)
    weight_inputs.append(weight)

# --- RUN MODEL ---

if st.button("⚡Calculate + Rank"):
    with st.spinner("Running model..."):
        try:
            raw_output = run_scrape(team1, team2)
            lines = raw_output.split("\n")
            batter_lines = []
            reading = False
            for line in lines:
                if "Batter Stats:" in line:
                    reading = True
                    continue
                if "Pitcher Stats:" in line:
                    break
                if reading and line.strip():
                    batter_lines.append(line)

            handedness_df = pd.read_csv("handedness.csv")
            handedness_dict = dict(zip(handedness_df["Name"].str.lower().str.strip(), handedness_df["Side"]))

            def get_stat_value(name, stats, stat_key):
                handed = handedness_dict.get(name.lower().strip(), "R")
                if stat_key == "RightFly":
                    return stats.get("PullAir %") if handed == "R" else stats.get("OppoAir %")
                elif stat_key == "LeftFly":
                    return stats.get("PullAir %") if handed == "L" else stats.get("OppoAir %")
                else:
                    return stats.get(stat_key)

            results = []
            for line in batter_lines:
                parts = [x.strip() for x in line.split("|")]
                stat_dict = {}
                for p in parts[1:]:
                    if ": " in p:
                        k, v = p.split(": ")
                        try:
                            stat_dict[k.strip()] = float(v)
                        except:
                            stat_dict[k.strip()] = None
                stat_dict["Name"] = parts[0]
                values = [get_stat_value(stat_dict["Name"], stat_dict, s) for s in stat_selections]
                if None not in values:
                    score = sum(w * v for w, v in zip(weight_inputs, values))
                    results.append((stat_dict["Name"], score))

            results.sort(key=lambda x: x[1], reverse=True)
            df = pd.DataFrame(results, columns=["Player", "Score"])
            st.markdown("### 🏆 Ranked Hitters")
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")

# --- SHOW RAW BATTER STATS ---

if st.button("📋 Show All Batter Stats"):
    try:
        raw_output = run_scrape(team1, team2)
        batter_lines = []
        lines = raw_output.split("\n")
        reading = False
        for line in lines:
            if "Batter Stats:" in line:
                reading = True
                continue
            if "Pitcher Stats:" in line:
                break
            if reading and line.strip():
                batter_lines.append(line)

        st.markdown("### 📊 All Batter Stats")
        for line in batter_lines:
            parts = [x.strip() for x in line.split("|")]
            name = parts[0]
            st.markdown(f"**🔹 {name}**")
            for p in parts[1:]:
                if ": " in p:
                    k, v = p.split(": ")
                    st.markdown(f"`{k.strip():<12}: {v.strip()}`")
            st.markdown("---")
    except Exception as e:
        st.error(f"Error: {e}")
