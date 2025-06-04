import streamlit as st
import pandas as pd
from scrape_stats import run_scrape
from get_lineups import get_players_and_pitchers
from pybaseball import playerid_lookup, statcast_batter_game_logs
import requests
from datetime import datetime
import time

# --- CONFIG ---
st.set_page_config(page_title="Hib's Tool", layout="wide")
st.title("⚾ Hib's Batter Data Tool")

with st.expander("ℹ️ How to Use", expanded=False):
    st.markdown("""
    **Welcome to Hib's Tool!**
    Disclaimer: Only will display full data for games in which lineups are currently out.

    1. Select a matchup from today's schedule or use the 7-Day tab.
    2. Choose how many stats you want to weight (1–4) for season tab (always 3 for 7-Day).
    3. Select the stat types and set your weights.
    4. Click **Run Model + Rank** to view the top hitters.
    """)

# --- GET TODAY'S MATCHUPS ---

TEAM_NAME_MAP_REV = {
    "Arizona Diamondbacks": "ARI", "Atlanta Braves": "ATL", "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS", "Chicago Cubs": "CHC", "Chicago White Sox": "CHW",
    "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE", "Colorado Rockies": "COL",
    "Detroit Tigers": "DET", "Houston Astros": "HOU", "Kansas City Royals": "KCR",
    "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD", "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL", "Minnesota Twins": "MIN", "New York Mets": "NYM",
    "New York Yankees": "NYY", "Oakland Athletics": "OAK", "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT", "San Diego Padres": "SDP", "Seattle Mariners": "SEA",
    "San Francisco Giants": "SFG", "St. Louis Cardinals": "STL", "Tampa Bay Rays": "TBR",
    "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH"
}

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

matchups = get_today_matchups()

# --- TABS ---
tab1, tab2 = st.tabs(["Season Stats", "7-Day Stats"])

with tab1:
    if matchups:
        selected_matchup = st.selectbox("Select Today's Matchup", matchups)
        team1, team2 = selected_matchup.split(" @ ")
    else:
        st.warning("No matchups available today.")

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
        default_stat = available_stats[i % len(available_stats)]
        stat = cols[0].selectbox(f"Stat {i+1}", available_stats, index=available_stats.index(default_stat), key=f"stat_{i}")
        weight = cols[1].number_input(f"Weight {i+1}", min_value=0.0, max_value=1.0, value=weight_defaults[i], step=0.01, key=f"w_{i}")
        stat_selections.append(stat)
        weight_inputs.append(weight)

    if st.button("⚡Calculate + Rank", key="season"):
        if matchups:
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
        else:
            st.error("No matchup selected — cannot run model.")

with tab2:
    st.markdown("### 🗓️ 7-Day Stats Mode")
    player_names = st.text_area("Enter player names (comma-separated)").strip()

    available_7day_stats = ["EV", "Barrel %", "xSLG"]

    st.markdown("### 🎯 Stat Weights (3 Stats)")
    weight_inputs_7day = []
    stat_selections_7day = []

    for i in range(3):
        cols = st.columns([2, 1])
        default_stat = available_7day_stats[i]
        stat = cols[0].selectbox(f"Stat {i+1}", available_7day_stats, index=available_7day_stats.index(default_stat), key=f"7d_stat_{i}")
        weight = cols[1].number_input(f"Weight {i+1}", min_value=0.0, max_value=1.0, value=1/3, step=0.01, key=f"7d_w_{i}")
        stat_selections_7day.append(stat)
        weight_inputs_7day.append(weight)

    if st.button("⚡Calculate 7-Day + Rank", key="7day"):
        if player_names:
            with st.spinner("Fetching 7-day stats..."):
                try:
                    players = [p.strip() for p in player_names.split(",")]
                    today = datetime.today()
                    last_week = today - pd.Timedelta(days=7)

                    results = []
                    for player in players:
                        try:
                            first, last = player.split(" ", 1)
                            lookup = playerid_lookup(last, first)
                            if lookup.empty:
                                st.warning(f"Could not find player: {player}")
                                continue
                            player_id = lookup.iloc[0]['key_mlbam']
                            logs = statcast_batter_game_logs(player_id, last_week.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"))
                            avg_ev = logs['launch_speed'].mean()
                            avg_barrel = logs['barrel'].mean()
                            avg_xslg = logs['estimated_slg'].mean()

                            stat_map = {
                                "EV": avg_ev,
                                "Barrel %": avg_barrel,
                                "xSLG": avg_xslg
                            }
                            values = [stat_map.get(stat) for stat in stat_selections_7day]
                            if None not in values:
                                score = sum(w * v for w, v in zip(weight_inputs_7day, values))
                                results.append((player, score))
                        except Exception as e:
                            st.warning(f"Error fetching data for {player}: {e}")

                    results.sort(key=lambda x: x[1], reverse=True)
                    df = pd.DataFrame(results, columns=["Player", "Score"])
                    st.markdown("### 🏆 7-Day Ranked Hitters")
                    st.dataframe(df, use_container_width=True)
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Please enter player names.")
