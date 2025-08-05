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

# --- LOAD PLAYER ID MAP ---
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
tab1, tab2, tab3 = st.tabs(["Season Stats", "11-Day Stats", "Weather"])

# --- SEASON TAB ---
with tab1:
    st.markdown("Season logic here")

# --- 11-DAY TAB ---
with tab2:
    st.markdown("11-Day logic here")

# --- WEATHER TAB (with DEBUG) ---
with tab3:
    st.markdown("### 🌬️ Weather Conditions (via RotoGrinders)")
    matchups = get_today_matchups()
    selected_weather_game = st.selectbox("Select Today's Matchup (Weather)", matchups if matchups else ["No matchups available"], key="weather_matchup")

    if selected_weather_game and selected_weather_game != "No matchups available":
        TEAM_CITY_MAP = {
            "ARI": "Arizona", "ATL": "Atlanta", "BAL": "Baltimore", "BOS": "Boston",
            "CHC": "Chicago", "CHW": "Chicago", "CIN": "Cincinnati", "CLE": "Cleveland",
            "COL": "Colorado", "DET": "Detroit", "HOU": "Houston", "KCR": "Kansas City",
            "LAA": "Los Angeles", "LAD": "Los Angeles", "MIA": "Miami", "MIL": "Milwaukee",
            "MIN": "Minnesota", "NYM": "New York", "NYY": "New York", "OAK": "Oakland",
            "PHI": "Philadelphia", "PIT": "Pittsburgh", "SDP": "San Diego", "SEA": "Seattle",
            "SFG": "San Francisco", "STL": "St. Louis", "TBR": "Tampa Bay", "TEX": "Texas",
            "TOR": "Toronto", "WSH": "Washington"
        }

        team1, team2 = selected_weather_game.split(" @ ")
        cities = [TEAM_CITY_MAP.get(team1, ""), TEAM_CITY_MAP.get(team2, "")]

        st.markdown(f"**🧪 Debug: Matching Cities →** `{cities}`")

        try:
            rg_url = "https://rotogrinders.com/weather/mlb"
            response = requests.get(rg_url)
            soup = BeautifulSoup(response.text, "html.parser")
            game_blocks = soup.find_all("div", class_="weather-graphic")

            found = False
            for i, block in enumerate(game_blocks):
                location_div = block.find("div", class_="weather-graphic__location")
                arrow_div = block.find("div", class_="weather-graphic__arrow")
                speed_div = block.find("div", class_="weather-graphic__speed")

                if location_div and arrow_div and speed_div:
                    location_text = location_div.text.strip().lower()
                    st.markdown(f"**Block {i} → Location:** `{location_text}`")

                    if any(city.lower() in location_text for city in cities):
                        rotation_style = arrow_div.get("style", "")
                        wind_rotation = rotation_style.split("rotate(")[-1].split("deg")[0].strip()
                        wind_speed = speed_div.text.strip()

                        try:
                            angle = int(wind_rotation)
                            if 45 <= angle < 135:
                                arrow_emoji = "⬇️"
                            elif 135 <= angle < 225:
                                arrow_emoji = "⬅️"
                            elif 225 <= angle < 315:
                                arrow_emoji = "⬆️"
                            else:
                                arrow_emoji = "➡️"
                        except:
                            arrow_emoji = "❓"

                        st.markdown(f"### 💨 Wind Conditions for `{selected_weather_game}`")
                        st.markdown(f"**Location:** {location_div.text.strip()}")
                        st.markdown(f"**Wind Speed:** {wind_speed}")
                        st.markdown(f"**Wind Direction:** {arrow_emoji} ({wind_rotation}°)")
                        found = True
                        break

            if not found:
                st.warning("⚠️ No wind data found for this matchup on RotoGrinders.")
        except Exception as e:
            st.error(f"Error fetching weather data: {str(e)}")
