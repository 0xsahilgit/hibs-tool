import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from pybaseball import statcast_batter
from get_lineups import get_players_and_pitchers
from bs4 import BeautifulSoup
import re

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
    "New York Yankees": "NYY",
    # Handle Athletics in both forms; schedule can show either.
    "Oakland Athletics": "OAK", "Athletics": "OAK",
    "Philadelphia Phillies": "PHI", "Pittsburgh Pirates": "PIT", "San Diego Padres": "SDP",
    "Seattle Mariners": "SEA", "San Francisco Giants": "SFG", "St. Louis Cardinals": "STL",
    "Tampa Bay Rays": "TBR", "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR",
    "Washington Nationals": "WSH"
}

# Build reverse lookup abbr -> list of full names (so OAK matches both forms)
ABBR_TO_FULL = {}
for full, abbr in TEAM_NAME_MAP_REV.items():
    ABBR_TO_FULL.setdefault(abbr, []).append(full)

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
    with st.expander("ℹ️ How to Use", expanded=False):
        st.markdown("""
        1. Select a matchup from today's schedule.
        2. Choose how many stats you want to weight (1–4).
        3. Select the stat types and set your weights.
        4. Click **Run Model + Rank** to view the top hitters.
        """)

    matchups = get_today_matchups()
    selected_matchup = st.selectbox("Select Today's Matchup", matchups if matchups else ["No matchups available"])
    team1, team2 = selected_matchup.split(" @ ")

    st.markdown("### 🎯 Stat Weights")
    num_stats = st.slider("How many stats do you want to weight?", 1, 4, 2)

    available_stats = ["EV", "Barrel %", "xSLG", "FB %", "RightFly", "LeftFly"]
    weight_defaults = {1:[1.0], 2:[0.5,0.5], 3:[0.33,0.33,0.34], 4:[0.25,0.25,0.25,0.25]}.get(num_stats, [1.0])

    stat_selections, weight_inputs = [], []
    for i in range(num_stats):
        col1, col2 = st.columns(2)
        default_stat = available_stats[i % len(available_stats)]
        stat = col1.selectbox(f"Stat {i+1}", available_stats, index=available_stats.index(default_stat), key=f"stat_{i}")
        weight = col2.number_input(f"Weight {i+1}", min_value=0.0, max_value=1.0, value=weight_defaults[i], step=0.01, key=f"w_{i}")
        stat_selections.append(stat); weight_inputs.append(weight)

    if st.button("⚡ Run Model + Rank (Season Stats)"):
        with st.spinner("🧮 Crunching season stats... please wait!"):
            from scrape_stats import run_scrape
            raw_output = run_scrape(team1, team2)
            lines = raw_output.split("\n")
            batter_lines, reading = [], False
            for line in lines:
                if "Batter Stats:" in line: reading = True; continue
                if "Pitcher Stats:" in line: break
                if reading and line.strip(): batter_lines.append(line)

            handedness_df = pd.read_csv("handedness.csv")
            handedness_dict = dict(zip(handedness_df["Name"].str.lower().str.strip(), handedness_df["Side"]))

            def get_stat_value(name, stats, stat_key):
                handed = handedness_dict.get(name.lower().strip(), "R")
                if stat_key == "RightFly":
                    return stats.get("PullAir %") if handed == "R" else stats.get("OppoAir %")
                elif stat_key == "LeftFly":
                    return stats.get("PullAir %") if handed == "L" else stats.get("OppoAir %")
                else:
                    return stats.get(stat_key)

            results = []
            for line in batter_lines:
                parts = [x.strip() for x in line.split("|")]
                stat_dict = {}
                for p in parts[1:]:
                    if ": " in p:
                        k, v = p.split(": ")
                        try: stat_dict[k.strip()] = float(v)
                        except: stat_dict[k.strip()] = None
                stat_dict["Name"] = parts[0]
                values = [get_stat_value(stat_dict["Name"], stat_dict, s) for s in stat_selections]
                if None not in values:
                    score = sum(w * v for w, v in zip(weight_inputs, values))
                    results.append((stat_dict["Name"], score))

            results.sort(key=lambda x: x[1], reverse=True)
            df = pd.DataFrame(results, columns=["Player", "Score"])
            st.markdown("### 🏆 Ranked Hitters (Season)")
            st.dataframe(df, use_container_width=True)

# --- 11-DAY TAB ---
with tab2:
    with st.expander("ℹ️ 11-Day Stats How to Use", expanded=False):
        st.markdown("""
        1. Select a matchup.
        2. 11-day filter will automatically pull.
        3. Only 3 stat fields: EV, Barrel %, FB %.
        """)

    selected_matchup_7d = st.selectbox("Select Today's Matchup (11-Day)", matchups if matchups else ["No matchups available"], key="7d_matchup")
    team1_7d, team2_7d = selected_matchup_7d.split(" @ ")

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

            handedness_df = pd.read_csv("handedness.csv")
            handedness_dict = dict(zip(handedness_df["Name"].str.lower().str.strip(), handedness_df["Side"]))

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
                    side = handedness_dict.get(name.lower().strip(), "")
                    label = f"{name} ({side})" if side else name
                    all_stats.append((label, avg_ev, barrel_pct, fb_pct))
                except:
                    continue

            if not all_stats:
                st.error("No data found for selected players.")
            else:
                results = []
                for name, ev, barrel, fb in all_stats:
                    values = [ev, barrel * 100, fb * 100]
                    score = sum(w * v for w, v in zip(weight_inputs_7d, values))
                    results.append((name, score))

                results.sort(key=lambda x: x[1], reverse=True)
                df_7d = pd.DataFrame(results, columns=["Player", "Score"])
                st.markdown("### 🏆 Ranked Hitters (11-Day)")
                st.dataframe(df_7d, use_container_width=True)

# --- WEATHER TAB ---
with tab3:
    st.markdown("### 🌬️ Weather Conditions (via RotoGrinders)")

    selected_weather_game = st.selectbox(
        "Select Today's Matchup (Weather)",
        matchups if matchups else ["No matchups available"],
        key="weather_matchup"
    )

    def _team_full_names_for_abbr(abbr):
        return [n.lower() for n in ABBR_TO_FULL.get(abbr.upper(), [])]

    if selected_weather_game and selected_weather_game != "No matchups available":
        t1_abbr, t2_abbr = selected_weather_game.split(" @ ")
        t1_names = _team_full_names_for_abbr(t1_abbr)
        t2_names = _team_full_names_for_abbr(t2_abbr)

        try:
            url = "https://rotogrinders.com/weather/mlb"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # RotoGrinders groups each game in a module block
            blocks = soup.find_all("div", class_="module")

            found = False
            for block in blocks:
                block_text = block.get_text(" ", strip=True).lower()

                # Heuristic: if either team full name appears anywhere in the block, we consider it a match
                if not (any(name in block_text for name in t1_names) and any(name in block_text for name in t2_names)):
                    continue

                # 1) Stadium label usually lives here
                stadium_el = block.find("span", class_="game-weather-stadium")
                stadium = stadium_el.get_text(strip=True) if stadium_el else "Unknown stadium"

                # 2) Collect "gametime" rows into a dict: {label: value}
                rows = {}
                for row in block.find_all("div", class_="weather-gametime-set"):
                    label_el = row.find("span", class_="weather-gametime-label")
                    value_el = row.find("span", class_="weather-gametime-value")
                    if label_el and value_el:
                        label = label_el.get_text(strip=True).lower()
                        value = value_el.get_text(strip=True)
                        rows[label] = value

                # 3) Wind speed text (e.g., "13 mph Out to RF")
                wind_text = rows.get("wind") or rows.get("wind (mph)") or rows.get("winds")
                mph_match = re.search(r"(\d+)\s*mph", wind_text or "", flags=re.I)
                mph = mph_match.group(1) + " mph" if mph_match else (wind_text or "N/A")

                # 4) Arrow rotation if present (older/newer layouts use this class)
                rotation_deg = None
                arrow_el = block.select_one(".weather-graphic__arrow")
                if arrow_el:
                    style = arrow_el.get("style", "")
                    if "rotate(" in style:
                        try:
                            rotation_deg = float(style.split("rotate(")[-1].split("deg")[0])
                        except Exception:
                            rotation_deg = None
                # (Some builds use data-angle/data-rotation attributes)
                if rotation_deg is None and arrow_el:
                    for attr in ("data-angle", "data-rotation", "data-deg"):
                        if arrow_el.get(attr):
                            try:
                                rotation_deg = float(arrow_el.get(attr))
                                break
                            except Exception:
                                pass

                st.markdown(f"**Stadium:** {stadium}")
                st.markdown(f"**Wind:** {mph}")

                if rotation_deg is not None:
                    st.markdown(
                        f'<div style="display:inline-block; transform: rotate({rotation_deg}deg); font-size: 48px; line-height: 1;">⬆️</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.caption("Wind arrow not available on RG page (showing speed only).")

                found = True
                break

            if not found:
                st.warning("No wind data found for this matchup on RotoGrinders.")

        except Exception as e:
            st.error(f"Error fetching weather data: {e}")
