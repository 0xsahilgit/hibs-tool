import streamlit as st
import pandas as pd
from scrape_stats import run_scrape
from get_lineups import get_players_and_pitchers
import requests
from datetime import datetime, timedelta
import time
from pybaseball import playerid_lookup, statcast_batter

# --- CONFIG ---
st.set_page_config(page_title="Hib's Tool", layout="wide")
st.title("⚾ Hib's Batter Data Tool")

# --- HOW TO USE ---
with st.expander("ℹ️ How to Use", expanded=False):
    st.markdown("""
    **Welcome to Hib's Tool!**
    Disclaimer: Only will display full data for games in which lineups are currently out.

    1. Select a matchup from today's schedule.
    2. Choose how many stats you want to weight (1–4).
    3. Select the stat types and set your weights.
    4. Click **Run Model + Rank** to view the top hitters.

    Optional: Click **Show All Batter Stats** to see raw data (including `n/a`s).

    **New!** Switch to the **7-Day** tab to run fresh Statcast data.
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

# --- TAB SETUP ---
tab1, tab2 = st.tabs(["Season Mode (CSV)", "7-Day Statcast Mode"])

with tab1:
    if matchups:
        selected_matchup = st.selectbox("Select Today's Matchup", matchups)
        team1, team2 = selected_matchup.split(" @ ")
    else:
        st.error("No matchups available today.")
        st.stop()

    st.markdown("### 🎯 Stat Weights")
    num_stats = st.slider("How many stats do you want to weight?", 1, 4, 2)

    available_stats = ["EV", "Barrel %", "xSLG", "FB %", "RightFly", "LeftFly"]

    weight_defaults = {
        1: [1.0],
        2: [0.5, 0.5],
        3: [0.33, 0.33, 0.34],
        4: [0.25, 0.25, 0.25, 0.25]
    }.get(num_stats, [1.]()_
