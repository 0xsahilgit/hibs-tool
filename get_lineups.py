
import requests
from datetime import datetime

TEAM_NAME_MAP = {
    "ARI": "Arizona Diamondbacks", "ATL": "Atlanta Braves", "BAL": "Baltimore Orioles",
    "BOS": "Boston Red Sox", "CHC": "Chicago Cubs", "CHW": "Chicago White Sox",
    "CIN": "Cincinnati Reds", "CLE": "Cleveland Guardians", "COL": "Colorado Rockies",
    "DET": "Detroit Tigers", "HOU": "Houston Astros", "KCR": "Kansas City Royals",
    "LAA": "Los Angeles Angels", "LAD": "Los Angeles Dodgers", "MIA": "Miami Marlins",
    "MIL": "Milwaukee Brewers", "MIN": "Minnesota Twins", "NYM": "New York Mets",
    "NYY": "New York Yankees", "OAK": "Oakland Athletics", "PHI": "Philadelphia Phillies",
    "PIT": "Pittsburgh Pirates", "SDP": "San Diego Padres", "SEA": "Seattle Mariners",
    "SFG": "San Francisco Giants", "STL": "St. Louis Cardinals", "TBR": "Tampa Bay Rays",
    "TEX": "Texas Rangers", "TOR": "Toronto Blue Jays", "WSH": "Washington Nationals"
}

def get_players_and_pitchers(team1_abbr, team2_abbr):
    today = datetime.now().strftime("%Y-%m-%d")
    schedule_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}"
    schedule = requests.get(schedule_url).json()

    team1_name = TEAM_NAME_MAP[team1_abbr.upper()]
    team2_name = TEAM_NAME_MAP[team2_abbr.upper()]

    for date in schedule.get("dates", []):
        for game in date.get("games", []):
            away = game["teams"]["away"]["team"]["name"]
            home = game["teams"]["home"]["team"]["name"]
            if {away, home} == {team1_name, team2_name}:
                game_id = game["gamePk"]
                box_url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"
                box = requests.get(box_url).json()

                batters = []
                for team_key in ["home", "away"]:
                    if team_key not in box["teams"]:
                        continue
                    team_players = box["teams"][team_key].get("players", {})
                    lineup = []
                    for player in team_players.values():
                        if "battingOrder" in player:
                            lineup.append((int(player["battingOrder"]), player["person"]["fullName"]))
                    sorted_names = [name for _, name in sorted(lineup)]
                    batters.extend(sorted_names)

                # Fallback to game-level probable pitcher data
                away_pitcher = game["teams"]["away"].get("probablePitcher", {}).get("fullName", "TBD")
                home_pitcher = game["teams"]["home"].get("probablePitcher", {}).get("fullName", "TBD")

                return batters, [away_pitcher, home_pitcher]

    return [], ["TBD", "TBD"]

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python3 get_lineups2.py TEAM1 TEAM2")
    else:
        batters, pitchers = get_players_and_pitchers(sys.argv[1], sys.argv[2])
        print("Batters:")
        for b in batters:
            print("-", b)
        print("\nPitchers:")
        for p in pitchers:
            print("-", p)
