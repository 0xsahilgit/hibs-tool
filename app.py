import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from pybaseball import statcast_batter, playerid_lookup  # added playerid_lookup
from get_lineups import get_players_and_pitchers
from bs4 import BeautifulSoup
from PIL import Image

# --- CONFIG ---
st.set_page_config(page_title="Hib's Batter Data Tool", layout="wide")
st.title("⚾ Hib's Batter Data Tool")

# --- TEAM & STADIUM MAPS ---
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

STADIUM_KEYWORDS = {
    "ARI": "chase field", "ATL": "truist park", "BAL": "camden yards",
    "BOS": "fenway park", "CHC": "wrigley field", "CHW": "guaranteed rate field",
    "CIN": "great american ball park", "CLE": "progressive field", "COL": "coors field",
    "DET": "comerica park", "HOU": "minute maid park", "KCR": "kauffman stadium",
    "LAA": "angel stadium", "LAD": "dodger stadium", "MIA": "loandepot park",
    "MIL": "american family field", "MIN": "target field", "NYM": "citi field",
    "NYY": "yankee stadium", "OAK": "sutter health park", "PHI": "citizens bank park",
    "PIT": "pnc park", "SDP": "petco park", "SEA": "t-mobile park", "SFG": "oracle park",
    "STL": "busch stadium", "TBR": "tropicana field", "TEX": "globe life field",
    "TOR": "rogers centre", "WSH": "nationals park"
}

# --- PLAYER ID MAP ---
id_map = pd.read_csv("player_id_map.csv")

def lookup_player_id(name: str):
    """
    First check your player_id_map.csv; if missing, try pybaseball.playerid_lookup
    (with light suffix cleanup for Jr., Sr., II, III, IV).
    """
    # Try CSV by full name
    try:
        row = id_map.loc[id_map['PLAYERNAME'].str.lower() == name.lower()]
        if not row.empty:
            return int(row['MLBID'].values[0])
        # Try CSV by FIRSTNAME + LASTNAME columns
        row = id_map.loc[(id_map['FIRSTNAME'].str.strip() + ' ' + id_map['LASTNAME'].str.strip()).str.lower() == name.lower()]
        if not row.empty:
            return int(row['MLBID'].values[0])
    except Exception:
        pass

    # Fallback: pybaseball lookup
    try:
        clean = name.replace(",", "")
        parts = clean.split()
        suffixes = {"jr", "sr", "ii", "iii", "iv"}
        parts_clean = [p for p in parts if p.lower().strip(".") not in suffixes]
        if len(parts_clean) >= 2:
            first = parts_clean[0]
            last = " ".join(parts_clean[1:])
            df = playerid_lookup(last, first)
            if df is not None and not df.empty:
                if 'mlb_played_last' in df.columns:
                    df = df.sort_values(by='mlb_played_last', ascending=False)
                return int(df.iloc[0]['key_mlbam'])
    except Exception:
        pass

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
matchups = get_today_matchups()
tab1, tab2, tab3 = st.tabs(["Season Stats", "11-Day Stats", "Weather"])

# === TAB 1 ===
with tab1:
    with st.expander("ℹ️ How to Use", expanded=False):
        st.markdown("""
        1. Select a matchup from today's schedule.
        2. Choose how many stats you want to weight (1–4).
        3. Select the stat types and set your weights.
        4. Click **Run Model + Rank** to view the top hitters.
        """)

    selected_matchup = st.selectbox("Select Today's Matchup", matchups if matchups else ["No matchups available"])
    team1, team2 = selected_matchup.split(" @ ")

    st.markdown("### 🎯 Stat Weights")
    num_stats = st.slider("How many stats do you want to weight?", 1, 4, 2)
    available_stats = ["EV", "Barrel %", "xSLG", "FB %", "RightFly", "LeftFly"]
    default_weights = {1: [1.0], 2: [0.5, 0.5], 3: [0.33, 0.33, 0.34], 4: [0.25, 0.25, 0.25, 0.25]}
    weight_defaults = default_weights.get(num_stats, [1.0])

    stat_selections = []
    weight_inputs = []
    for i in range(num_stats):
        col1, col2 = st.columns(2)
        stat = col1.selectbox(f"Stat {i+1}", available_stats, index=i % len(available_stats), key=f"stat_{i}")
        weight = col2.number_input(f"Weight {i+1}", min_value=0.0, max_value=1.0, value=weight_defaults[i], step=0.01, key=f"w_{i}")
        stat_selections.append(stat)
        weight_inputs.append(weight)

    if st.button("⚡ Run Model + Rank (Season Stats)"):
        with st.spinner("🧮 Crunching season stats... please wait!"):
            from scrape_stats import run_scrape
            raw_output = run_scrape(team1, team2)
            lines = raw_output.split("\n")
            batter_lines = []
            reading = False
            for line in lines:
                if "Batter Stats:" in line:
                    reading = True
                    continue
                if "Pitcher Stats:" in line:
                    break
                if reading and line.strip():
                    batter_lines.append(line)

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
                        try:
                            stat_dict[k.strip()] = float(v)
                        except:
                            stat_dict[k.strip()] = None
                stat_dict["Name"] = parts[0]
                values = [get_stat_value(stat_dict["Name"], stat_dict, s) for s in stat_selections]
                if None not in values:
                    score = sum(w * v for w, v in zip(weight_inputs, values))
                    results.append((stat_dict["Name"], score))

            results.sort(key=lambda x: x[1], reverse=True)
            df = pd.DataFrame(results, columns=["Player", "Score"])
            st.markdown("### 🏆 Ranked Hitters (Season)")
            st.dataframe(df, use_container_width=True)

# === TAB 2 ===
with tab2:
    with st.expander("ℹ️ 11-Day Stats How to Use", expanded=False):
        st.markdown("""
        1. Select a matchup.
        2. 11-day filter will automatically pull.
        3. Only 3 stat fields: EV, Barrel %, FB %.
        """)

    selected_matchup_7d = st.selectbox("Select Today's Matchup (11-Day)", matchups, key="7d_matchup")
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
            # Start with the 3-letter codes from the dropdown
            abbr1, abbr2 = team1_7d, team2_7d
            source_used = "ABBR (3-letter)"

            # Attempt #1
            batters, _ = None, None
            try:
                batters, _ = get_players_and_pitchers(abbr1, abbr2)
            except Exception:
                batters = None

            # If empty/thin, try alternates. Oakland is the main pain point, but include some other common variants too.
            def _thin(lst): 
                return (lst is None) or (len(lst) < 4)

            ALT_LISTS = {
                "TBR": ["TBR", "TB", "TAM"],
                "KCR": ["KCR", "KC"],
                "SDP": ["SDP", "SD"],
                "SFG": ["SFG", "SF"],
                "WSH": ["WSH", "WSN"],
                "CHW": ["CHW", "CWS"],
                # Oakland special:
                "OAK": ["OAK", "OAKLAND", "OAKL", "ATH", "ATHLETICS"],
            }

            def alternates(code):
                return ALT_LISTS.get(code, [code])

            if _thin(batters):
                tried = set()
                found_combo = None
                for a1 in alternates(abbr1):
                    for a2 in alternates(abbr2):
                        if (a1, a2) in tried:
                            continue
                        tried.add((a1, a2))
                        if (a1, a2) == (abbr1, abbr2):
                            continue
                        try:
                            b_alt, _ = get_players_and_pitchers(a1, a2)
                            if not _thin(b_alt):
                                batters = b_alt
                                found_combo = (a1, a2)
                                break
                        except Exception:
                            pass
                    if found_combo:
                        break
                if found_combo:
                    source_used = f"ABBR (alternate) → {found_combo[0]} @ {found_combo[1]}"
                    abbr1, abbr2 = found_combo

            today = datetime.now().strftime('%Y-%m-%d')
            eleven_days_ago = (datetime.now() - timedelta(days=11)).strftime('%Y-%m-%d')

            handedness_df = pd.read_csv("handedness.csv")
            handedness_dict = dict(zip(handedness_df["Name"].str.lower().str.strip(), handedness_df["Side"]))

            # Debug snapshot so we can quickly see what happened on OAK slates
            st.caption("🔎 Debug (11-Day Tab)")
            st.write({
                "input_matchup": selected_matchup_7d,
                "lineup_query_used": source_used,
                "team1_used": abbr1,
                "team2_used": abbr2,
                "num_batters": (len(batters) if batters else 0)
            })

            if not batters:
                st.error("Could not load batters from the lineup source for this matchup.")
                st.stop()

            all_stats = []
            debug_rows = []

            for name in batters:
                pid = lookup_player_id(name)
                note = "ok" if pid else "id_not_found_csv_or_lookup"
                if pid:
                    try:
                        data = statcast_batter(eleven_days_ago, today, pid)
                        if data is None or data.empty:
                            note = "no_statcast_rows"
                        else:
                            avg_ev = data['launch_speed'].mean(skipna=True)
                            barrel_events = data[data['launch_speed'] > 95]
                            barrel_pct = len(barrel_events) / len(data) if len(data) > 0 else 0
                            fb_pct = len(data[data['launch_angle'] >= 25]) / len(data) if len(data) > 0 else 0
                            side = handedness_dict.get(name.lower().strip(), "")
                            label = f"{name} ({side})" if side else name
                            all_stats.append((label, avg_ev, barrel_pct, fb_pct))
                    except Exception as e:
                        note = f"statcast_error: {e}"
                debug_rows.append((name, pid, note))

            st.dataframe(pd.DataFrame(debug_rows, columns=["Player", "MLBAM_ID", "Note"]), use_container_width=True)

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

# === TAB 3 ===
with tab3:
    st.markdown("### 🌬️ Weather Conditions (via RotoGrinders)")
    selected_weather_matchup = st.selectbox("Select Today's Matchup (Weather)", matchups, key="weather_matchup")
    team1, team2 = selected_weather_matchup.split(" @ ")
    keywords = [STADIUM_KEYWORDS.get(team1, "").lower(), STADIUM_KEYWORDS.get(team2, "").lower()]
    # st.markdown(f"🧪 Debug: Matching Stadium Keywords → {keywords}")

    try:
        url = "https://rotogrinders.com/weather/mlb"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.text, "html.parser")
        blocks = soup.find_all("div", class_="module")

        found = False
        all_locations = []

        for block in blocks:
            location_div = block.find("span", class_="game-weather-stadium")
            if not location_div :
                continue

            location = location_div.get_text()[2:].strip().lower()
            all_locations.append(location)


            weather_data = block.find_all("div", class_="weather-gametime-set")

            if len(weather_data) == 0:
                if any(k in location or location in k for k in keywords if k):
                    st.success(f"✅ Location match: `{location}`")
                    st.markdown(f"Game is played inside a dome")
                    found = True
                continue

            temp = weather_data[0].find_all("span", recursive=False)[-2].find("span", class_="weather-gametime-value bold").get_text()
            precipitation = weather_data[0].find_all("span", recursive=False)[-1].find("span", class_="weather-gametime-value bold").get_text()
            wind_dir = weather_data[1].find_all("span", recursive=False)[-2].find("span", class_="weather-gametime-value bold").get_text()
            wind_speed = weather_data[1].find_all("span", recursive=False)[-1].find("span", class_="weather-gametime-value bold").get_text()

            # Find all <path> elements within the <svg>
            paths = block.find_all("span", class_="weather-gametime-icon")[-1].find('svg').find_all('path')

            # Target the third <path> (index 2, assuming you meant the one with rotate)
            target_path = paths[2]  # Second path would be paths[1], but it has no rotate

            # Get the style attribute
            style = target_path.get('style')

            # Parse the style attribute to extract the transform property
            style_dict = dict(item.strip().split(':') for item in style.split(';') if item)
            transform = style_dict.get('transform', '')

            # Extract the rotation angle from the transform property
            import re

            rotation_match = re.search(r'rotate\(([\d.]+)deg\)', transform)
            if rotation_match:
                rotation_angle = float(rotation_match.group(1))
            else:
                rotation_angle = 0.0


            if any(k in location or location in k for k in keywords if k):
                st.success(f"✅ Location match: `{location}`")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**💨 Wind Speed:**")
                    st.markdown(f"**🧭 Wind Direction:**")
                    st.markdown(f"**🌧️ Precipitation::**")
                    st.markdown(f"**🌡️Temperature::**")
                with col2:
                    st.markdown(f"`{wind_speed} MPH`")
                    img = Image.open("arrow.png")
                    img = img.rotate(360 - rotation_angle, expand=True)
                    st.image(img)
                    st.markdown(f"`{precipitation}`")
                    st.markdown(f"`{temp}`")
                found = True
                break

        if not found:
            st.warning("⚠️ No wind data found for this matchup.")
            st.markdown("### 🗺️ All Locations Found on RotoGrinders:")
            st.code("\n".join(all_locations))

    except Exception as e:
        st.error(f"Error loading weather data: {e}")
