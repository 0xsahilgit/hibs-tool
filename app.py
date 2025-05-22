import streamlit as st
import pandas as pd
from scrape_stats import run_scrape
from get_lineups import get_players_and_pitchers

# --- CONFIG ---

st.set_page_config(page_title="Hib's Tool", layout="wide")
st.title("⚾ Hib's Batter Data Tool")

with st.expander("ℹ️ How to Use", expanded=True):
    st.markdown("""
    **Welcome to Hib's Tool!**
    Disclaimer: Only will display full data for games in which lineups are currently out.

    1. Enter team abbreviations for both teams in a matchup. (ex. PHI COL)
    2. Choose how many stats you want to weight (1–4).
    3. Select the stat types and set your weights.
    4. Click **Run Model + Rank** to view the top hitters.

    Optional: Click **Show All Batter Stats** to see raw data (including `n/a`s).
    """)

# --- TEAM INPUTS ---

col1, col2 = st.columns(2)
with col1:
    team1 = st.text_input("Team 1 Abbreviation", value="PHI").strip().upper()
with col2:
    team2 = st.text_input("Team 2 Abbreviation", value="COL").strip().upper()

# --- STAT SELECTION ---

st.markdown("### 🎯 Stat Weights")
num_stats = st.slider("How many stats do you want to weight?", 1, 4, 2)

available_stats = ["EV", "Barrel %", "xSLG", "FB %", "RightFly", "LeftFly"]

weight_defaults = {
    1: [1.0],
    2: [0.5, 0.5],
    3: [0.33, 0.33, 0.34],
    4: [0.25, 0.25, 0.25, 0.25]
}.get(num_stats, [1.0])

stat_selections = []
weight_inputs = []

for i in range(num_stats):
    cols = st.columns([2, 1])
    stat = cols[0].selectbox(f"Stat {i+1}", available_stats, key=f"stat_{i}")
    weight = cols[1].number_input(f"Weight {i+1}", min_value=0.0, max_value=1.0, value=weight_defaults[i], step=0.01, key=f"w_{i}")
    stat_selections.append(stat)
    weight_inputs.append(weight)

# --- RUN MODEL ---

if st.button("⚡Calculate + Rank"):
    with st.spinner("Running model..."):
        try:
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

            # DEBUG: Show parsed batter lines
            st.subheader("🧪 DEBUG: Parsed Batter Lines")
            st.write(batter_lines)

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

                # DEBUG: Show each parsed stat dict
                st.subheader(f"🧪 Stats for {stat_dict['Name']}")
                st.write(stat_dict)

                values = [get_stat_value(stat_dict["Name"], stat_dict, s) for s in stat_selections]

                # DEBUG: Show selected values for scoring
                st.write(f"Selected values: {values}")

                if None not in values:
                    score = sum(w * v for w, v in zip(weight_inputs, values))
                    results.append((stat_dict["Name"], score))

            # DEBUG: Show final results before sorting
            st.subheader("🧪 Raw Scoring Results")
            st.write(results)

            results.sort(key=lambda x: x[1], reverse=True)
            df = pd.DataFrame(results, columns=["Player", "Score"])

            # DEBUG: Final DataFrame
            st.subheader("📊 Final Ranked Hitters DataFrame")
            st.write(df)

            st.markdown("### 🏆 Ranked Hitters")
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")

# --- SHOW RAW BATTER STATS ---

if st.button("📋 Show All Batter Stats"):
    try:
        raw_output = run_scrape(team1, team2)
        batter_lines = []
        lines = raw_output.split("\n")
        reading = False
        for line in lines:
            if "Batter Stats:" in line:
                reading = True
                continue
            if "Pitcher Stats:" in line:
                break
            if reading and line.strip():
                batter_lines.append(line)

        st.markdown("### 📊 All Batter Stats")
        for line in batter_lines:
            parts = [x.strip() for x in line.split("|")]
            name = parts[0]
            st.markdown(f"**🔹 {name}**")
            for p in parts[1:]:
                if ": " in p:
                    k, v = p.split(": ")
                    st.markdown(f"`{k.strip():<12}: {v.strip()}`")
            st.markdown("---")
    except Exception as e:
        st.error(f"Error: {e}")
