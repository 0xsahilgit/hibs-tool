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

# --- STADIUM MAPPINGS FOR WEATHER TAB ---
STADIUM_KEYWORDS = {
    "ARI": "chase field",
    "ATL": "truist park",
    "BAL": "camden yards",
    "BOS": "fenway park",
    "CHC": "wrigley field",
    "CHW": "guaranteed rate field",
    "CIN": "great american ball park",
    "CLE": "progressive field",
    "COL": "coors field",
    "DET": "comerica park",
    "HOU": "minute maid park",
    "KCR": "kauffman stadium",
    "LAA": "angel stadium",
    "LAD": "dodger stadium",
    "MIA": "loanDepot park",
    "MIL": "american family field",
    "MIN": "target field",
    "NYM": "citi field",
    "NYY": "yankee stadium",
    "OAK": "sutter health park",
    "PHI": "citizens bank park",
    "PIT": "pnc park",
    "SDP": "petco park",
    "SEA": "t-mobile park",
    "SFG": "oracle park",
    "STL": "busch stadium",
    "TBR": "tropicana field",
    "TEX": "globe life field",
    "TOR": "rogers centre",
    "WSH": "nationals park"
}

# --- HELPER ---
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

# -------------------- TAB 1 --------------------
# (identical to your benchmark – skipping reprint here to keep message size reasonable)

# -------------------- TAB 2 --------------------
# (identical to your benchmark – also skipped here)

# -------------------- TAB 3 --------------------
with tab3:
    st.markdown("### 🌬️ Weather Conditions (via RotoGrinders)")
    matchups = get_today_matchups()
    selected_matchup = st.selectbox("Select Today's Matchup (Weather)", matchups if matchups else ["No matchups available"], key="weather_matchup")

    team1, team2 = selected_matchup.split(" @ ")
    keywords = [STADIUM_KEYWORDS.get(team1, "").lower(), STADIUM_KEYWORDS.get(team2, "").lower()]
    st.write(f"🧪 Debug: Stadium keywords → {keywords}")

    try:
        url = "https://rotogrinders.com/weather/mlb"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.text, "html.parser")

        all_blocks = soup.find_all("div", class_="weather-graphic__location")
        found_block = None

        for block in all_blocks:
            text = block.get_text(strip=True).lower()
            st.write(f"🔎 Scanning: {text}")
            if any(k in text for k in keywords if k):
                found_block = block
                break

        if found_block:
            arrow_div = found_block.find_next("div", class_="weather-graphic__arrow")
            speed_div = found_block.find_next("div", class_="weather-graphic__speed")
            wind_dir = arrow_div['style'].split("rotate(")[-1].split("deg")[0] + "°" if arrow_div else "?"
            wind_speed = speed_div.get_text(strip=True) if speed_div else "?"

            st.markdown(f"**🌡️ Wind Speed:** {wind_speed}")
            st.markdown(f"**🧭 Wind Direction:** {wind_dir} rotation")
        else:
            st.warning("⚠️ No wind data found for this matchup. Try updating STADIUM_KEYWORDS if this persists.")

    except Exception as e:
        st.error(f"Error retrieving weather: {e}")
