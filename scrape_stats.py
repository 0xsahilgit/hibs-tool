
import pandas as pd
from get_lineups import get_players_and_pitchers
import re

# Load CSVs
expected_batters = pd.read_csv("expected_batters.csv")
exit_batters = pd.read_csv("exit_batters.csv")
expected_pitchers = pd.read_csv("expected_pitchers.csv")
exit_pitchers = pd.read_csv("exit_pitchers.csv")
batted_ball = pd.read_csv("batted_ball.csv")

# Pre-clean batted_ball name column to lowercase "last, first" with no punctuation
def clean_name(name):
    return re.sub(r"[^\w\s]", "", name).lower().strip()

batted_ball['name_clean'] = batted_ball['name'].apply(clean_name)

def format_to_last_first(name):
    parts = name.strip().split()
    if len(parts) < 2:
        return None
    first = parts[0]
    last = " ".join(parts[1:])
    return f"{last}, {first}"

def get_batter_stats(name):
    last_first = format_to_last_first(name)
    if not last_first:
        return {
            "Name": name,
            "EV": "n/a",
            "Barrel %": "n/a",
            "xSLG": "n/a",
            "PullAir %": "n/a",
            "OppoAir %": "n/a",
            "FB %": "n/a"
        }

    ev_row = exit_batters[exit_batters['last_name, first_name'].str.lower() == last_first.lower()]
    exp_row = expected_batters[expected_batters['last_name, first_name'].str.lower() == last_first.lower()]

    # Standardize name to match cleaned batted_ball
    cleaned_last_first = clean_name(last_first)
    ball_row = batted_ball[batted_ball['name_clean'] == cleaned_last_first]

    ev = ev_row.iloc[0]['avg_hit_speed'] if not ev_row.empty else 87.0
    barrel = ev_row.iloc[0]['brl_percent'] if not ev_row.empty else 3.0
    xslg = exp_row.iloc[0]['est_slg'] if not exp_row.empty else 0.34
    pull_air = ball_row.iloc[0]['pull_air_rate'] if not ball_row.empty else "n/a"
    oppo_air = ball_row.iloc[0]['oppo_air_rate'] if not ball_row.empty else "n/a"
    fb_rate = ball_row.iloc[0]['fb_rate'] if not ball_row.empty else "n/a"

    return {
        "Name": name,
        "EV": ev,
        "Barrel %": barrel,
        "xSLG": xslg,
        "PullAir %": pull_air,
        "OppoAir %": oppo_air,
        "FB %": fb_rate
    }

def get_pitcher_stats(name):
    last_first = format_to_last_first(name)
    if not last_first:
        return {
            "Name": name,
            "Hard-Hit %": "n/a",
            "Barrel % Allowed": "n/a"
        }

    row = exit_pitchers[exit_pitchers['last_name, first_name'].str.lower() == last_first.lower()]
    hh = row.iloc[0]['ev95percent'] if not row.empty else 40.0
    brl_allowed = row.iloc[0]['brl_percent'] if not row.empty else 6.0
    return {
        "Name": name,
        "Hard-Hit %": hh,
        "Barrel % Allowed": brl_allowed
    }

def run_scrape(team1, team2):
    lineup_data = get_players_and_pitchers(team1, team2)
    if not lineup_data:
        return f"Error: Either no {team1.upper()} vs {team2.upper()} game today, or lineups not yet posted."

    away_players, home_players, away_pitcher, home_pitcher, team_away, team_home = lineup_data

    players = away_players + home_players
    pitchers = [away_pitcher, home_pitcher]

    output = "Batter Stats:\n"
    for player in players:
        stats = get_batter_stats(player)
        output += (
            f"{stats['Name']} | EV: {stats['EV']} | Barrel %: {stats['Barrel %']} | xSLG: {stats['xSLG']} | "
            f"PullAir %: {stats['PullAir %']} | OppoAir %: {stats['OppoAir %']} | FB %: {stats['FB %']}\n"
        )

    output += "\nPitcher Stats:\n"
    for pitcher in pitchers:
        stats = get_pitcher_stats(pitcher)
        output += f"{stats['Name']} | Hard-Hit %: {stats['Hard-Hit %']} | Barrel % Allowed: {stats['Barrel % Allowed']}\n"

    return output

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3:
        result = run_scrape(sys.argv[1], sys.argv[2])
        print(result)
    else:
        print("Usage: python3 scrape_stats.py TEAM1 TEAM2")
