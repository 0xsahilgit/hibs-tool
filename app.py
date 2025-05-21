
import streamlit as st
import pandas as pd
from scrape_stats import run_scrape
from get_lineups import get_players_and_pitchers
import requests

# --- CONFIG ---

st.set_page_config(page_title="Hib's Tool", layout="wide")
st.title("⚾ Hib's Home Run Model")

with st.expander("ℹ️ How to Use", expanded=True):
    st.markdown("""
    **Welcome to Hib's Tool!**

        2. Enter the two MLB team abbreviations (e.g., `PHI`, `COL`).
    3. Choose how many stats you want to weight (1–4).
    4. Select the stat types and set your weights.
    5. Click **Run Model + Rank** to view the top hitters.

    Optional: Click **Show All Batter Stats** to see raw data (including `n/a`s).
    """)

# --- Google Drive Auto-Downloader ---

        "expected_batters.csv": "1pwL50l7c_CkhsjQv3sWbZLFTrF71Cq8z",
        "expected_pitchers.csv": "1r89avc5FgKQN_-nm-E6lyfaK5ZceBrWW",
        "exit_batters.csv": "1IQxPNDp1iQcJuMIgi8jZAa-kWJeFqkcQ",
        "exit_pitchers.csv": "15ZVcJNsL6SiIAA2Q4QuTTLQLT7St01B4",
        "batted_ball.csv": "1V3Z0gNdmO9ZC7Ii0ECyd2K5U4mtDx-yO"
    }
    success = []
    for fname, fid in files.items():
        if download_csv(fid, fname):
            success.append(fname)
    if len(success) == len(files):
        st.success("✅ All CSVs updated successfully.")
    else:
        st.warning("⚠️ Some files failed to update.")

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

stat_selections = []
weight_inputs = []

for i in range(num_stats):
    cols = st.columns([2, 1])
    stat = cols[0].selectbox(f"Stat {i+1}", available_stats, key=f"stat_{i}")
    weight = cols[1].number_input(f"Weight {i+1}", min_value=0.0, max_value=1.0, value=0.25, step=0.01, key=f"w_{i}")
    stat_selections.append(stat)
    weight_inputs.append(weight)

# --- RUN MODEL ---

if st.button("⚡ Run Model + Rank"):
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
