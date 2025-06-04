import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from pybaseball import statcast_batter
from get_lineups import get_players_and_pitchers
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
    "New York Yankees": "NYY", "Oakland Athletics": "OAK", "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT", "San Diego Padres": "SDP", "Seattle Mariners": "SEA",
    "San Francisco Giants": "SFG", "St. Louis Cardinals": "STL", "Tampa Bay Rays": "TBR",
    "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH"
}

# --- LOAD PLAYER ID MAP ---
id_map = pd.read_csv("player_id_map.csv")

def lookup_player_id(name):
    try:
        row = id_map.loc[(id_map['name_first'] + ' ' + id_map['name_last']).str.lower() == name.lower()]
        if not row.empty:
            return int(row['key_mlbam'].values[0])
    except Exception as e:
        return None
    return None

# --- GET TODAY'S MATCHUPS ---
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

# --- UI ---
tab1, tab2 = st.tabs(["Season Stats", "7-Day Stats"])

with tab1:
    with st.expander("ℹ️ How to Use", expanded=False):
        st.markdown("""
        1. Select a matchup from today's schedule.
        2. Choose how many stats you want to weight (1–4).
        3. Select the stat types and set your weights.
        4. Click **Run Model + Rank** to view the top hitters.
        """)

    matchups = get_today_matchups()
    selected_matchup = st.selectbox("Select Today's Matchup", matchups if matchups else ["No matchups available"])
    team1, team2 = selected_matchup.split(" @ ")

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

    if st.button("⚡Calculate + Rank (Season Stats)"):
        with st.spinner("Running season model..."):
            from scrape_stats import run_scrape
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
            st.markdown("### 🏆 Ranked Hitters (Season)")
            st.dataframe(df, use_container_width=True)

with tab2:
    with st.expander("ℹ️ 7-Day Stats How to Use", expanded=False):
        st.markdown("""
        1. Select a matchup.
        2. 7-day filter will automatically pull.
        3. Only 3 stat fields: EV, Barrel %, FB %.
        """)

    matchups = get_today_matchups()
    selected_matchup_7d = st.selectbox("Select Today's Matchup (7-Day)", matchups if matchups else ["No matchups available"], key="7d_matchup")
    team1_7d, team2_7d = selected_matchup_7d.split(" @ ")

    available_7d_stats = ["EV", "Barrel %", "FB %"]
    default_weights_7d = [0.33, 0.33, 0.34]

    st.markdown("### 🎯 7-Day Stat Weights")
    weight_inputs_7d = []
    for i, stat in enumerate(available_7d_stats):
        cols = st.columns([2, 1])
        cols[0].markdown(f"**{stat}**")
        weight = cols[1].number_input(f"Weight {stat}", min_value=0.0, max_value=1.0, value=default_weights_7d[i], step=0.01, key=f"7d_weight_{i}")
        weight_inputs_7d.append(weight)

    if st.button("⚡Calculate + Rank (7-Day Stats)"):
        with st.spinner("Running 7-day model..."):
            batters, _ = get_players_and_pitchers(team1_7d, team2_7d)

            today = datetime.now().strftime('%Y-%m-%d')
            seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

            all_stats = []
            for name in batters:
                player_id = lookup_player_id(name)
                if player_id is None:
                    continue
                try:
                    data = statcast_batter(seven_days_ago, today, player_id)
                    if data.empty:
                        continue
                    avg_ev = data['launch_speed'].mean(skipna=True)
                    barrel_events = data[data['launch_speed'] > 95]  # Rough barrel proxy
                    barrel_pct = len(barrel_events) / len(data) if len(data) > 0 else 0
                    fb_pct = len(data[data['launch_angle'] >= 25]) / len(data) if len(data) > 0 else 0
                    all_stats.append((name, avg_ev, barrel_pct, fb_pct))
                except Exception as e:
                    continue

            if not all_stats:
                st.error("No data found for selected players.")
            else:
                results = []
                for name, ev, barrel, fb in all_stats:
                    values = [ev, barrel * 100, fb * 100]  # Scale barrel and FB % to percentages
                    score = sum(w * v for w, v in zip(weight_inputs_7d, values))
                    results.append((name, score))

                results.sort(key=lambda x: x[1], reverse=True)
                df_7d = pd.DataFrame(results, columns=["Player", "Score"])
                st.markdown("### 🏆 Ranked Hitters (7-Day)")
                st.dataframe(df_7d, use_container_width=True)
