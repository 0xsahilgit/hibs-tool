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
    "New York Yankees": "NYY", "Athletics": "OAK", "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT", "San Diego Padres": "SDP", "Seattle Mariners": "SEA",
    "San Francisco Giants": "SFG", "St. Louis Cardinals": "STL", "Tampa Bay Rays": "TBR",
    "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH"
}

# --- LOAD PLAYER ID MAP ---
id_map = pd.read_csv("player_id_map.csv")
handedness_df = pd.read_csv("handedness.csv")
handedness_dict = dict(zip(handedness_df["Name"].str.lower().str.strip(), handedness_df["Side"]))

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

# --- GET WIND DATA FROM ROTOGRINDERS ---
def get_rotogrinders_wind():
    url = "https://rotogrinders.com/weather/mlb"
    headers = {'User-Agent': 'Mozilla/5.0'}
    page = requests.get(url, headers=headers)
    soup = BeautifulSoup(page.text, "html.parser")
    forecasts = soup.find_all("div", class_="weather-forecast")
    wind_data = {}
    for forecast in forecasts:
        title = forecast.find("h3", class_="location").text.strip()
        arrow = forecast.find("i", class_="wi")
        mph_tag = forecast.find("div", class_="weather-icon")
        if not title or not arrow or not mph_tag:
            continue
        stadium = title.split(" Weather")[0]
        rotation = arrow.get("style", "")
        mph = mph_tag.text.strip()
        wind_data[stadium] = (rotation, mph)
    return wind_data

wind_lookup = get_rotogrinders_wind()

# --- UI ---
tab1, tab2 = st.tabs(["Season Stats", "11-Day Stats"])

# -- TAB 1 OMITTED TO FOCUS ON TAB 2 CHANGES --

with tab2:
    with st.expander("ℹ️ 11-Day Stats How to Use", expanded=False):
        st.markdown("""
        1. Select a matchup.
        2. 11-day filter will automatically pull.
        3. Only 3 stat fields: EV, Barrel %, FB %.
        4. Now includes wind direction + MPH from Rotogrinders!
        """)

    matchups = get_today_matchups()
    selected_matchup_7d = st.selectbox("Select Today's Matchup (11-Day)", matchups if matchups else ["No matchups available"], key="7d_matchup")
    team1_7d, team2_7d = selected_matchup_7d.split(" @ ")

    # Display wind data
    for stadium, (rotation, mph) in wind_lookup.items():
        if team1_7d in stadium or team2_7d in stadium:
            st.markdown(f"### 🌬️ Wind for **{stadium}**:")
            st.markdown(
                f'<div style="display: flex; align-items: center;">'
                f'<i class="wi wi-strong-wind" style="transform: {rotation}; font-size: 32px; margin-right: 10px;"></i>'
                f'<span style="font-size: 18px;">{mph}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
            break

    available_7d_stats = ["EV", "Barrel %", "FB %"]
    default_weights_7d = [0.33, 0.33, 0.34]

    st.markdown("### 🎯 11-Day Stat Weights")
    weight_inputs_7d = []
    for i, stat in enumerate(available_7d_stats):
        col1, col2 = st.columns(2)
        col1.markdown(f"**{stat}**")
        weight = col2.number_input(f"Weight {stat}", min_value=0.0, max_value=1.0, value=default_weights_7d[i], step=0.01, key=f"7d_weight_{i}")
        weight_inputs_7d.append(weight)

    if st.button("⚡ Run Model + Rank (11-Day Stats)"):
        with st.spinner("📈 Fetching 11-day player data... please wait!"):
            batters, _ = get_players_and_pitchers(team1_7d, team2_7d)

            today = datetime.now().strftime('%Y-%m-%d')
            eleven_days_ago = (datetime.now() - timedelta(days=11)).strftime('%Y-%m-%d')

            all_stats = []
            for name in batters:
                player_id = lookup_player_id(name)
                if player_id is None:
                    continue
                try:
                    data = statcast_batter(eleven_days_ago, today, player_id)
                    if data.empty:
                        continue
                    avg_ev = data['launch_speed'].mean(skipna=True)
                    barrel_events = data[data['launch_speed'] > 95]
                    barrel_pct = len(barrel_events) / len(data) if len(data) > 0 else 0
                    fb_pct = len(data[data['launch_angle'] >= 25]) / len(data) if len(data) > 0 else 0
                    all_stats.append((name, avg_ev, barrel_pct, fb_pct))
                except:
                    continue

            if not all_stats:
                st.error("No data found for selected players.")
            else:
                results = []
                for name, ev, barrel, fb in all_stats:
                    side = handedness_dict.get(name.lower().strip(), "R")
                    values = [ev, barrel * 100, fb * 100]
                    score = sum(w * v for w, v in zip(weight_inputs_7d, values))
                    results.append((f"{name} ({side})", score))

                results.sort(key=lambda x: x[1], reverse=True)
                df_7d = pd.DataFrame(results, columns=["Player", "Score"])
                st.markdown("### 🏆 Ranked Hitters (11-Day)")
                st.dataframe(df_7d, use_container_width=True)
