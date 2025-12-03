import streamlit as st
import pandas as pd

# ---------- Helper functions ---------

def calculate_player_stats(pars, strokes):
    total_par = sum(pars)
    total_strokes = sum(strokes)
    diff = total_strokes - total_par
    if diff > 0:
        rel_text = "+{} (over par)".format(diff)
        rel_short = "+{}".format(diff)
    elif diff < 0:
        rel_text = "{} (under par)".format(diff)
        rel_short = str(diff)
    else:
        rel_text = "E (even par)"
        rel_short = "E"
    return total_par, total_strokes, diff, rel_text, rel_short


def build_sms_summary(course_name, players, pars, scores):
    """Build SMS summary with only totals + relative-to-par + winner."""
    stats_list = []
    for name in players:
        _, total_strokes, diff, _, rel_short = calculate_player_stats(pars, scores[name])
        stats_list.append((name, total_strokes, rel_short))

    # sort by total strokes (best first)
    stats_list.sort(key=lambda x: x[1])
    winner_name = stats_list[0][0]
    winner_score = stats_list[0][1]

    lines = []
    lines.append("Golf Results - {}\n".format(course_name))
    lines.append("{:<12}{:<8}{:<6}".format("Player", "Total", "Rel"))
    lines.append("-" * 28)
    for name, total, rel in stats_list:
        lines.append("{:<12}{:<8}{:<6}".format(name, total, rel))
    lines.append("")
    lines.append("Winner: {} ({})".format(winner_name, winner_score))

    return "\n".join(lines)


# ---------- Main Streamlit app ----------

def app():
    st.set_page_config(page_title="Golf Scorecard", page_icon="⛳", layout="centered")

    st.title("⛳ Golf Scorecard")
    st.write("Hole-by-hole scorecard with up to 4 players and Front / Back / 3rd Nine selection.")

    ss = st.session_state
    if "game_started" not in ss:
        ss.game_started = False
    if "current_hole_index" not in ss:
        ss.current_hole_index = 0

    # ---------- STEP 1: SETUP ----------
    if not ss.game_started:
        st.header("Step 1 – Game setup")

        # Course name
        course_name = st.text_input(
            "Golf course name",
            value=ss.get("course_name", "My Golf Course")
        )

        # Number of players (1–4)
        num_players = st.selectbox(
            "Number of players",
            options=[1, 2, 3, 4],
            index=ss.get("num_players_index", 1)
        )

        # Player names
        players = []
        st.subheader("Player names")
        for i in range(num_players):
            default_name = "Player{}".format(i + 1)
            key_name = "player_name_{}".format(i)
            name_val = ss.get(key_name, default_name)
            name = st.text_input(
                "Player {}".format(i + 1),
                value=name_val,
                key=key_name
            )
            if not name.strip():
                name = default_name
            players.append(name)

        # Which nines to play
        st.subheader("Which nines will be played?")
        options_labels = ["Front 9 (1–9)", "Back 9 (10–18)", "3rd Nine (19–27)"]
        nines_choice = st.multiselect(
            "Select one or more nines",
            options=options_labels,
            default=[options_labels[0]],
        )

        start_button = st.button("▶ Start round")

        if start_button:
            # Default to Front 9 if user cleared selection
            if not nines_choice:
                nines_choice = [options_labels[0]]

            # Build hole sequence in correct order
            hole_sequence = []
            mapping = [
                ("Front 9 (1–9)", 1, 9),
                ("Back 9 (10–18)", 10, 18),
                ("3rd Nine (19–27)", 19, 27),
            ]
            for label, start_h, end_h in mapping:
                if label in nines_choice:
                    hole_sequence.extend(list(range(start_h, end_h + 1)))

            # Store in session_state
            ss.course_name = course_name
            ss.players = players
            ss.holes = hole_sequence
            ss.pars = [None] * len(hole_sequence)
            ss.scores = {name: [None] * len(hole_sequence) for name in players}
            ss.current_hole_index = 0
            ss.game_started = True
            ss.num_players_index = [1, 2, 3, 4].index(num_players)

            st.experimental_rerun()

        return  # stop here if setup not complete

    # ---------- STEP 2: HOLE-BY-HOLE INPUT ----------
    course_name = ss.course_name
    players = ss.players
    holes = ss.holes
    num_holes = len(holes)

    st.header("Step 2 – Enter scores hole by hole")
    st.markdown("Course: **{}**".format(course_name))
    st.markdown("Players: **{}**".format(", ".join(players)))
    st.markdown("Total holes this round: **{}**".format(num_holes))

    idx = ss.current_hole_index

    if idx < num_holes:
        hole_num = holes[idx]
        st.subheader("Hole {} ({} of {})".format(hole_num, idx + 1, num_holes))

        # Par input for this hole
        par_key = "par_input_{}".format(hole_num)
        par_val = st.number_input(
            "Par for hole {}".format(hole_num),
            min_value=3,
            max_value=6,
            value=4,
            key=par_key
        )

        # Strokes for each player
        stroke_values = {}
        st.markdown("Enter strokes for each player:")
        for name in players:
            stroke_key = "stroke_{}_{}".format(name, hole_num)
            stroke_values[name] = st.number_input(
                "Strokes for {}".format(name),
                min_value=1,
                max_value=20,
                value=4,
                key=stroke_key
            )

        col1, col2 = st.columns(2)
        with col1:
            next_pressed = st.button("Save hole and next ▶")
        with col2:
            finish_pressed = st.button("Finish round now ⏹")

        if next_pressed or finish_pressed:
            # Save current hole data
            ss.pars[idx] = int(par_val)
            for name in players:
                ss.scores[name][idx] = int(stroke_values[name])

            if finish_pressed:
                # Truncate to current hole and go to summary
                ss.holes = holes[: idx + 1]
                ss.pars = ss.pars[: idx + 1]
                for name in players:
                    ss.scores[name] = ss.scores[name][: idx + 1]
                ss.current_hole_index = len(ss.holes)
            else:
                ss.current_hole_index = idx + 1

            st.experimental_rerun()

        st.info(
            "Fill par and strokes, then click **Save hole and next**. "
            "Use **Finish round now** to stop before all holes are played."
        )
        return

    # ---------- STEP 3: SUMMARY + SMS ----------
    st.header("Step 3 – Summary and SMS")

    pars = ss.pars
    scores = ss.scores
    holes = ss.holes
    num_holes = len(holes)

    # Scorecard table
    st.subheader("📋 Scorecard Summary")
    data = {"Hole (Par)": ["{} ({})".format(holes[i], pars[i]) for i in range(num_holes)]}
    for name in players:
        data[name] = scores[name]
    df = pd.DataFrame(data)

    # Totals + relative to par
    totals = {}
    rels = {}
    for name in players:
        _, total_strokes, diff, _, rel_short = calculate_player_stats(pars, scores[name])
        totals[name] = total_strokes
        rels[name] = rel_short

    total_row = {"Hole (Par)": "Total"}
    rel_row = {"Hole (Par)": "Rel to Par"}
    for name in players:
        total_row[name] = totals[name]
        rel_row[name] = rels[name]

    df_summary = pd.concat([df, pd.DataFrame([total_row, rel_row])], ignore_index=True)
    st.dataframe(df_summary, use_container_width=True)

    # SMS / WhatsApp summary (totals only)
    st.subheader("📱 SMS / WhatsApp Summary")
    sms_text = build_sms_summary(course_name, players, pars, scores)
    st.code(sms_text, language="text")

    # New round button
    if st.button("🔁 Start a new round"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.experimental_rerun()


if __name__ == "__main__":
    app()
