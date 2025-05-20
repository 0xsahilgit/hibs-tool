#!/usr/bin/env python3
import statsapi

TEAM_NAMES = {
    "ARI": "Arizona Diamondbacks", "ATL": "Atlanta Braves", "BAL": "Baltimore Orioles",
    "BOS": "Boston Red Sox", "CHC": "Chicago Cubs", "CHW": "Chicago White Sox",
    "CIN": "Cincinnati Reds", "CLE": "Cleveland Guardians", "COL": "Colorado Rockies",
    "DET": "Detroit Tigers", "HOU": "Houston Astros", "KC": "Kansas City Royals",
    "KCR": "Kansas City Royals", "LAA": "Los Angeles Angels", "LAD": "Los Angeles Dodgers",
    "MIA": "Miami Marlins", "MIL": "Milwaukee Brewers", "MIN": "Minnesota Twins",
    "NYM": "New York Mets", "NYY": "New York Yankees", "OAK": "Oakland Athletics","ATH": "Oakland Athletics",
    "PHI": "Philadelphia Phillies", "PIT": "Pittsburgh Pirates", "SDP": "San Diego Padres",
    "SEA": "Seattle Mariners", "SFG": "San Francisco Giants", "SF": "San Francisco Giants",
    "STL": "St. Louis Cardinals", "TB": "Tampa Bay Rays", "TBR": "Tampa Bay Rays",
    "TEX": "Texas Rangers", "TOR": "Toronto Blue Jays", "WSH": "Washington Nationals",
    "WAS": "Washington Nationals"
}

def fetch_today_matchups():
    return statsapi.schedule(date=None)

def get_players_and_pitchers(team1, team2):
    matchups = fetch_today_matchups()
    for game in matchups:
        if {game['home_name'], game['away_name']} != {TEAM_NAMES[team1.upper()], TEAM_NAMES[team2.upper()]}:
            continue
        boxscore = statsapi.boxscore_data(game['game_id'])
        away_players = [p['person']['fullName'] for p in boxscore['away']['players'].values() if p.get('battingOrder')]
        home_players = [p['person']['fullName'] for p in boxscore['home']['players'].values() if p.get('battingOrder')]

        away_pitcher = game.get('away_probable_pitcher', 'Unknown')
        home_pitcher = game.get('home_probable_pitcher', 'Unknown')

        return away_players, home_players, away_pitcher, home_pitcher, game['away_name'], game['home_name']
    return None
