
import pandas as pd
import numpy as np
import re

def clean_name(name):
    return re.sub(r"[^\w\s]", "", name).lower().strip()

def load_csvs():
    expected_batters = pd.read_csv("expected_batters.csv")
    exit_batters = pd.read_csv("exit_batters.csv")
    expected_pitchers = pd.read_csv("expected_pitchers.csv")
    exit_pitchers = pd.read_csv("exit_pitchers.csv")
    batted_ball = pd.read_csv("batted_ball.csv")

    batted_ball['name_clean'] = batted_ball['name'].apply(clean_name)
    return expected_batters, exit_batters, expected_pitchers, exit_pitchers, batted_ball

def run_scrape(team1, team2):
    expected_batters, exit_batters, expected_pitchers, exit_pitchers, batted_ball = load_csvs()

    team_names = [team1.strip().upper(), team2.strip().upper()]
    batter_rows = exit_batters[exit_batters["Team"].isin(team_names)]
    pitcher_rows = exit_pitchers[exit_pitchers["Team"].isin(team_names)]

    print("Batter Stats:")
    for _, row in batter_rows.iterrows():
        name = row["Name"]
        ev_row = expected_batters[expected_batters["Name"] == name]
        xSLG = float(ev_row["xSLG"]) if not ev_row.empty else "n/a"
        barrel = float(ev_row["Barrel %"]) if not ev_row.empty else "n/a"

        batted_row = batted_ball[batted_ball["name_clean"] == clean_name(name)]
        pull_air = float(batted_row["pull_air_rate"]) if not batted_row.empty else "n/a"
        oppo_air = float(batted_row["oppo_air_rate"]) if not batted_row.empty else "n/a"
        fb = float(batted_row["fb_rate"]) if not batted_row.empty else "n/a"

        EV = row["EV"]
        print(f"{name} | EV: {EV} | Barrel %: {barrel} | xSLG: {xSLG} | PullAir %: {pull_air} | OppoAir %: {oppo_air} | FB %: {fb}")

    print("\nPitcher Stats:")
    for _, row in pitcher_rows.iterrows():
        name = row["Name"]
        ev_row = expected_pitchers[expected_pitchers["Name"] == name]
        barrel_allowed = float(ev_row["Barrel %"]) if not ev_row.empty else "n/a"
        hh = float(ev_row["HardHit %"]) if not ev_row.empty else "n/a"
        print(f"{name} | Hard-Hit %: {hh} | Barrel % Allowed: {barrel_allowed}")
