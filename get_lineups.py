import requests
import datetime

def get_players_and_pitchers(team1, team2):
    team1 = team1.upper()
    team2 = team2.upper()
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    schedule_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}"
    schedule = requests.get(schedule_url).json()

    game_pk = None
    for date in schedule["dates"]:
        for game in date["games"]:
            teams = game["teams"]
            t1 = teams["away"]["team"]["abbreviation"]
            t2 = teams["home"]["team"]["abbreviation"]
            if {t1, t2} == {team1, team2}:
                game_pk = game["gamePk"]
                break

    if not game_pk:
        return None

    box_url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
    box = requests.get(box_url).json()

    team_data = box["teams"]
    away_team = team_data["away"]
    home_team = team_data["home"]

    def extract_lineup(team_players):
        lineup = []
        for player in team_players.values():
            name = player["person"]["fullName"]
            if "battingOrder" in player:
                lineup.append((int(player["battingOrder"]), name))
            elif "stats" in player or "position" in player:
                lineup.append((999, name))  # Add to end if order unknown
        sorted_names = [name for _, name in sorted(lineup)]
        return sorted_names

    away_lineup = extract_lineup(away_team["players"])
    home_lineup = extract_lineup(home_team["players"])

    away_pitcher = next((p["person"]["fullName"] for p in away_team["players"].values()
                         if p.get("position", {}).get("code") == "1"), "TBD")
    home_pitcher = next((p["person"]["fullName"] for p in home_team["players"].values()
                         if p.get("position", {}).get("code") == "1"), "TBD")

    batters = away_lineup if away_team["team"]["abbreviation"] == team1 else home_lineup
    pitchers = [away_pitcher, home_pitcher]

    return batters, pitchers
