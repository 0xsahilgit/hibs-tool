# 🧠 app.py - All 3 tabs: Season, 11-Day, and Weather

import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from pybaseball import statcast_batter
from get_lineups import get_players_and_pitchers
from bs4 import BeautifulSoup
import time

# --- CONFIG ---
st.set_page_config(page_title="Hib's Batter Data Tool", layout="wide")
st.title("⚾ Hib's Batter Data Tool")

# --- TEAM MAPS ---
TEAM_NAME_MAP_REV = {
    "Arizona Diamondbacks": "ARI", "Atlanta Braves": "ATL", "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS", "Chicago Cubs": "CHC", "Chicago White Sox": "CHW",
    "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE", "Colorado Rockies": "COL",
    "Detroit Tigers": "DET", "Houston Astros": "HOU", "Kansas City Royals": "KCR",
    "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD", "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL", "Minnesota Twins": "MIN", "New York Mets": "NYM",
    "New York Yankees": "NYY", "Oakland Athletics": "OAK", "Athletics": "OAK",
    "Philadelphia Phillies": "PHI", "Pittsburgh Pirates": "PIT", "San Diego Padres": "SDP",
    "Seattle Mariners": "SEA", "San Francisco Giants": "SFG", "St. Louis Cardinals": "STL",
    "Tampa Bay Rays": "TBR", "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR",
    "Washington Nationals": "WSH"
}

STADIUM_KEYWORDS = {
    "ARI": ["Chase Field"], "ATL": ["Truist Park"], "BAL": ["Oriole Park"],
    "BOS": ["Fenway Park"], "CHC": ["Wrigley Field"], "CHW": ["Guaranteed Rate Field"],
    "CIN": ["Great American Ball Park"], "CLE": ["Progressive Field"], "COL": ["Coors Field"],
    "DET": ["Comerica Park"], "HOU": ["Minute Maid Park"], "KCR": ["Kauffman Stadium"],
    "LAA": ["Angel Stadium", "Angel Stadium of Anaheim"], "LAD": ["Dodger Stadium"],
    "MIA": ["Marlins Park", "loanDepot park"], "MIL": ["American Family Field"],
    "MIN": ["Target Field"], "NYM": ["Citi Field"], "NYY": ["Yankee Stadium"],
    "OAK": ["Oakland Coliseum", "RingCentral Coliseum", "Sutter Health Park"],
    "PHI": ["Citizens Bank Park"], "PIT": ["PNC Park"], "SDP": ["Petco Park"],
    "SEA": ["T-Mobile Park"], "SFG": ["Oracle Park"], "STL": ["Busch Stadium"],
    "TBR": ["Tropicana Field"], "TEX": ["Globe Life Field"], "TOR": ["Rogers Centre"],
    "WSH": ["Nationals Park"]
}

# --- MATCHUPS ---
def get_today_matchups():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}"
    response = requests.get(url).json()
    matchups = []
    for date in response.get("dates", []):
        for game in date.get("games", []):
            away = game["teams"]["away"]["team"]["name"]
            home = game["teams"]["home"]["team"]["name"]
            if away in TEAM_NAME_MAP_REV and home in TEAM_NAME_MAP_REV:
                matchups.append(f"{TEAM_NAME_MAP_REV[away]} @ {TEAM_NAME_MAP_REV[home]}")
    return matchups

# --- PLAYER ID MAP ---
id_map = pd.read_csv("player_id_map.csv")
def lookup_player_id(name):
    try:
        row = id_map.loc[id_map['PLAYERNAME'].str.lower() == name.lower()]
        if not row.empty:
            return int(row['MLBID'].values[0])
        row = id_map.loc[(id_map['FIRSTNAME'].str.strip() + ' ' + id_map['LASTNAME'].str.strip()).str.lower() == name.lower()]
        if not row.empty:
            return int(row['MLBID'].values[0])
    except:
        return None
    return None

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["Season Stats", "11-Day Stats", "Weather"])

# ----------------------------------
# 📊 TAB 1 — SEASON STATS
# ----------------------------------
with tab1:
    with st.expander("ℹ️ How to Use", expanded=False):
        st.markdown("1. Select a matchup, then pick your stat weights to rank hitters.")

    matchups = get_today_matchups()
    selected_matchup = st.selectbox("Select Today's Matchup", matchups if matchups else ["No matchups available"])
    team1, team2 = selected_matchup.split(" @ ")

    st.markdown("### 🎯 Stat Weights")
    num_stats = st.slider("How many stats to weight?", 1, 4, 2)
    available_stats = ["EV", "Barrel %", "xSLG", "FB %", "RightFly", "LeftFly"]
    weight_defaults = {1: [1.0], 2: [0.5, 0.5], 3: [0.33, 0.33, 0.34], 4: [0.25]*4}.get(num_stats, [1.0])

    stat_selections, weight_inputs = [], []
    for i in range(num_stats):
        col1, col2 = st.columns(2)
        stat = col1.selectbox(f"Stat {i+1}", available_stats, key=f"stat_{i}")
        weight = col2.number_input(f"Weight {i+1}", 0.0, 1.0, weight_defaults[i], step=0.01, key=f"w_{i}")
        stat_selections.append(stat)
        weight_inputs.append(weight)

    if st.button("⚡ Run Model + Rank (Season Stats)"):
        from scrape_stats import run_scrape
        with st.spinner("🧮 Crunching numbers..."):
            output = run_scrape(team1, team2)
            lines = output.split("\n")
            batter_lines = [line for line in lines if "|" in line and not line.startswith("│ Pitcher")]
            handedness_df = pd.read_csv("handedness.csv")
            handedness_dict = dict(zip(handedness_df["Name"].str.lower().str.strip(), handedness_df["Side"]))

            def get_stat_value(name, stats, stat_key):
                handed = handedness_dict.get(name.lower().strip(), "R")
                if stat_key == "RightFly":
                    return stats.get("PullAir %") if handed == "R" else stats.get("OppoAir %")
                elif stat_key == "LeftFly":
                    return stats.get("PullAir %") if handed == "L" else stats.get("OppoAir %")
                return stats.get(stat_key)

            results = []
            for line in batter_lines:
                parts = [x.strip() for x in line.split("|")]
                name = parts[0]
                stats = {}
                for p in parts[1:]:
                    if ": " in p:
                        k, v = p.split(": ")
                        try: stats[k] = float(v)
                        except: stats[k] = None
                values = [get_stat_value(name, stats, s) for s in stat_selections]
                if None not in values:
                    score = sum(w * v for w, v in zip(weight_inputs, values))
                    results.append((name, score))

            df = pd.DataFrame(sorted(results, key=lambda x: x[1], reverse=True), columns=["Player", "Score"])
            st.dataframe(df, use_container_width=True)

# ----------------------------------
# 📈 TAB 2 — 11-DAY STATS
# ----------------------------------
with tab2:
    with st.expander("ℹ️ 11-Day Stats Help", expanded=False):
        st.markdown("Pulls Statcast data from the last 11 days via pybaseball.")

    selected_matchup_7d = st.selectbox("Select Matchup (11-Day)", matchups, key="7d_matchup")
    team1_7d, team2_7d = selected_matchup_7d.split(" @ ")

    st.markdown("### 🎯 11-Day Stat Weights")
    stats_11 = ["EV", "Barrel %", "FB %"]
    weight_inputs_7d = []
    for i, stat in enumerate(stats_11):
        col1, col2 = st.columns(2)
        col1.markdown(f"**{stat}**")
        weight = col2.number_input(f"Weight {stat}", 0.0, 1.0, [0.33, 0.33, 0.34][i], step=0.01, key=f"7d_weight_{i}")
        weight_inputs_7d.append(weight)

    if st.button("⚡ Run Model + Rank (11-Day Stats)"):
        with st.spinner("⏳ Fetching 11-day stats..."):
            batters, _ = get_players_and_pitchers(team1_7d, team2_7d)
            today = datetime.now().strftime('%Y-%m-%d')
            eleven_days_ago = (datetime.now() - timedelta(days=11)).strftime('%Y-%m-%d')
            handedness_df = pd.read_csv("handedness.csv")
            handedness_dict = dict(zip(handedness_df["Name"].str.lower().str.strip(), handedness_df["Side"]))

            results = []
            for name in batters:
                player_id = lookup_player_id(name)
                if not player_id: continue
                try:
                    data = statcast_batter(eleven_days_ago, today, player_id)
                    if data.empty: continue
                    ev = data['launch_speed'].mean(skipna=True)
                    barrel_pct = len(data[data['launch_speed'] > 95]) / len(data)
                    fb_pct = len(data[data['launch_angle'] >= 25]) / len(data)
                    label = f"{name} ({handedness_dict.get(name.lower(), '')})"
                    values = [ev, barrel_pct * 100, fb_pct * 100]
                    score = sum(w * v for w, v in zip(weight_inputs_7d, values))
                    results.append((label, score))
                except:
                    continue

            df_7d = pd.DataFrame(sorted(results, key=lambda x: x[1], reverse=True), columns=["Player", "Score"])
            st.dataframe(df_7d, use_container_width=True)

# ----------------------------------
# 🌬️ TAB 3 — WEATHER
# ----------------------------------
with tab3:
    st.subheader("🌬️ Weather Conditions (via RotoGrinders)")
    selected_weather_matchup = st.selectbox("Select Today's Matchup (Weather)", matchups, key="weather_matchup")
    away, home = selected_weather_matchup.split(" @ ")

    url = "https://rotogrinders.com/weather/mlb"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    blocks = soup.find_all("div", class_="weather-graphic")
    match = None
    for block in blocks:
        location = block.find("div", class_="weather-graphic__location")
        if not location: continue
        loc_text = location.text.lower()
        keywords = STADIUM_KEYWORDS.get(home, []) + STADIUM_KEYWORDS.get(away, [])
        if any(k.lower() in loc_text for k in keywords):
            match = block
            break

    if match:
        arrow = match.find("div", class_="weather-graphic__arrow")
        speed = match.find("div", class_="weather-graphic__speed")
        dir_text = arrow.get("style", "") if arrow else ""
        mph = speed.text.strip() if speed else "?"
        deg = "?"  # optional: extract from style later
        st.markdown(f"**Wind:** {mph} | {dir_text}")
    else:
        st.warning("⚠️ No wind data found for this matchup. Try updating `STADIUM_KEYWORDS` if this persists.")
