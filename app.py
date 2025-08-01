# (unchanged imports and setup code)
handedness_df = pd.read_csv("handedness.csv")
handedness_dict = dict(zip(handedness_df["Name"].str.lower().str.strip(), handedness_df["Side"]))

...

with tab2:
    with st.expander("ℹ️ 11-Day Stats How to Use", expanded=False):
        st.markdown("""
        1. Select a matchup.
        2. 11-day filter will automatically pull.
        3. Only 3 stat fields: EV, Barrel %, FB %.
        """)

    matchups = get_today_matchups()
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
                    all_stats.append((name, avg_ev, barrel_pct, fb_pct))
                except:
                    continue

            if not all_stats:
                st.error("No data found for selected players.")
            else:
                results = []
                for name, ev, barrel, fb in all_stats:
                    values = [ev, barrel * 100, fb * 100]
                    score = sum(w * v for w, v in zip(weight_inputs_7d, values))
                    handed = handedness_dict.get(name.lower().strip(), "R")
                    name_with_side = f"{name} ({handed})"
                    results.append((name_with_side, score))

                results.sort(key=lambda x: x[1], reverse=True)
                df_7d = pd.DataFrame(results, columns=["Player", "Score"])
                st.markdown("### 🏆 Ranked Hitters (11-Day)")
                st.dataframe(df_7d, use_container_width=True)
