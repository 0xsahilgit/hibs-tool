import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from pybaseball import statcast_batter
from get_lineups import get_players_and_pitchers
from bs4 import BeautifulSoup

# --- CONFIG ---
st.set_page_config(page_title="Hib's Batter Data Tool", layout="wide")
st.title("⚾ Hib's Batter Data Tool")

# --- TEAM MAPS ---
TEAM_NAME_MAP_REV = {
    "Arizona Diamondbacks": "ARI", "Atlanta Braves": "ATL", "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS", "Chicago Cubs": "CHC", "Chicago White Sox": "CHW",
    "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE", "Colorado Rockies": "COL",
    "Detroit Tigers": "DET", "Houston Astros": "HOU", "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD", "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL", "Minnesota Twins": "MIN", "New York Mets": "NYM",
    "New York Yankees": "NYY", "Oakland Athletics": "OAK", "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT", "San Diego Padres": "SD", "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA", "St. Louis Cardinals": "STL", "Tampa Bay Rays": "TB",
    "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH"
}

# --- MATCHUP GETTER ---
def get_today_matchups():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}"
    res = requests.get(url).json()
    matchups = []
    for date in res.get("dates", []):
        for game in date.get("games", []):
            teams = game["teams"]
            away = TEAM_NAME_MAP_REV.get(teams["away"]["team"]["name"])
            home = TEAM_NAME_MAP_REV.get(teams["home"]["team"]["name"])
            if away and home:
                matchups.append(f"{away} @ {home}")
    return sorted(matchups)

matchups = get_today_matchups()

# --- STADIUM KEYWORDS FOR WEATHER ---
STADIUM_KEYWORDS = {
    "ARI": ["Chase Field"],
    "ATL": ["Truist Park"],
    "BAL": ["Oriole Park"],
    "BOS": ["Fenway Park"],
    "CHC": ["Wrigley Field"],
    "CHW": ["Guaranteed Rate Field"],
    "CIN": ["Great American Ball Park"],
    "CLE": ["Progressive Field"],
    "COL": ["Coors Field"],
    "DET": ["Comerica Park"],
    "HOU": ["Minute Maid Park"],
    "KC": ["Kauffman Stadium"],
    "LAA": ["Angel Stadium"],
    "LAD": ["Dodger Stadium"],
    "MIA": ["loanDepot park"],
    "MIL": ["American Family Field"],
    "MIN": ["Target Field"],
    "NYM": ["Citi Field"],
    "NYY": ["Yankee Stadium"],
    "OAK": ["Oakland Coliseum", "Sutter Health Park"],
    "PHI": ["Citizens Bank Park"],
    "PIT": ["PNC Park"],
    "SD": ["Petco Park"],
    "SEA": ["T-Mobile Park"],
    "SF": ["Oracle Park"],
    "STL": ["Busch Stadium"],
    "TB": ["Tropicana Field"],
    "TEX": ["Globe Life Field"],
    "TOR": ["Rogers Centre"],
    "WSH": ["Nationals Park"]
}

# --- APP TABS ---
tab1, tab2, tab3 = st.tabs(["Season Stats", "11-Day Stats", "🌬️ Weather"])

# --- SEASON STATS TAB ---
with tab1:
    st.subheader("Season Stats")
    selected_matchup = st.selectbox("Select Matchup", matchups, key="season")
    if st.button("Run Season Model"):
        players, pitchers = get_players_and_pitchers(selected_matchup)
        from scrape_stats import run_scrape
        df = run_scrape(players, pitchers)
        st.dataframe(df)

# --- 11-DAY TAB ---
with tab2:
    st.subheader("11-Day Stats")
    selected_matchup = st.selectbox("Select Matchup", matchups, key="statcast")
    if st.button("Get 11-Day Data"):
        players, _ = get_players_and_pitchers(selected_matchup)
        end = datetime.today()
        start = end - timedelta(days=11)
        statcast_data = []
        for name in players:
            try:
                row = statcast_batter(name, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
                if not row.empty:
                    statcast_data.append(row)
            except Exception:
                continue
        if statcast_data:
            df = pd.concat(statcast_data)
            st.dataframe(df)
        else:
            st.warning("No 11-day statcast data found.")

# --- WEATHER TAB ---
with tab3:
    st.subheader("🌬️ Weather Conditions (via RotoGrinders)")
    selected_matchup = st.selectbox("Select Today's Matchup (Weather)", matchups, key="weather")

    team1, team2 = selected_matchup.split(" @ ")
    stadiums = STADIUM_KEYWORDS.get(team1, []) + STADIUM_KEYWORDS.get(team2, [])
    st.markdown(f"🧪 Debug: Matching Cities → {stadiums}")

    def get_weather_data():
        try:
            res = requests.get("https://rotogrinders.com/weather/mlb")
            soup = BeautifulSoup(res.text, "html.parser")
            blocks = soup.find_all("div", class_="weather-graphic")

            for block in blocks:
                loc = block.find("div", class_="weather-graphic__location")
                arrow = block.find("div", class_="weather-graphic__arrow")
                speed = block.find("div", class_="weather-graphic__speed")

                if not loc or not arrow or not speed:
                    continue

                loc_text = loc.text.strip().lower()
                for keyword in stadiums:
                    if keyword.lower() in loc_text:
                        wind_speed = speed.text.strip()
                        style = arrow.get("style", "")
                        rotation = None
                        if "rotate(" in style:
                            rotation = style.split("rotate(")[-1].split("deg")[0].strip()

                        return {
                            "stadium": loc.text.strip(),
                            "wind_speed": wind_speed,
                            "rotation": rotation
                        }
            return None
        except:
            return None

    weather = get_weather_data()

    if weather:
        st.markdown(f"📍 **Stadium:** {weather['stadium']}")
        st.markdown(f"💨 **Wind Speed:** {weather['wind_speed']}")
        if weather['rotation']:
            deg = float(weather['rotation'])
            arrows = ["⬆️", "↗️", "➡️", "↘️", "⬇️", "↙️", "⬅️", "↖️"]
            idx = int(((deg + 22.5) % 360) // 45)
            st.markdown(f"🧭 **Wind Direction:** {arrows[idx]} ({deg}°)")
    else:
        st.warning("⚠️ No wind data found for this matchup. Try updating STADIUM_KEYWORDS if this persists.")
