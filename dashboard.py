from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


FREQUENCIES_PATH = Path("data") / "word_frequencies.csv"
YEARLY_FREQUENCIES_PATH = Path("data") / "word_frequencies_by_year.csv"

PUZZLE_TYPES = {
    "Daily": "daily",
    "Mini": "mini",
    "Midi": "midi",
}


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    frequencies = pd.read_csv(FREQUENCIES_PATH)
    yearly_frequencies = pd.read_csv(YEARLY_FREQUENCIES_PATH)
    return frequencies, yearly_frequencies


def selected_columns(selected_types: list[str], prefix: str, suffix: str = "") -> list[str]:
    return [
        f"{prefix}{PUZZLE_TYPES[label]}{suffix}"
        for label in selected_types
    ]


def available_years(yearly_frequencies: pd.DataFrame, selected_types: list[str]) -> list[int]:
    if not selected_types:
        return []

    count_columns = selected_columns(selected_types, "", "_count")
    has_selected_type_data = yearly_frequencies[count_columns].sum(axis=1) > 0
    return sorted(yearly_frequencies.loc[has_selected_type_data, "year"].unique())


def add_metric_column(
    data: pd.DataFrame,
    selected_types: list[str],
    normalized: bool,
) -> pd.DataFrame:
    result = data.copy()
    if normalized:
        rate_columns = selected_columns(selected_types, "avg_per_100_")
        result["selected_frequency"] = result[rate_columns].mean(axis=1)
    else:
        count_columns = selected_columns(selected_types, "", "_count")
        result["selected_frequency"] = result[count_columns].sum(axis=1)
    return result


def format_metric_label(normalized: bool) -> str:
    return "Average appearances per 100 puzzles" if normalized else "Raw appearances"


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def frequency_rank(source: pd.DataFrame, column: str, value: float) -> int:
    """Competition rank (1 = most frequent) of ``value`` within ``column``.

    Tied counts share the same rank.
    """
    return int((source[column] > value).sum()) + 1


def seed_filter_defaults(max_answer_length: int) -> None:
    defaults = {
        "flt_types": list(PUZZLE_TYPES.keys()),
        "flt_year": "All years",
        "flt_normalized": False,
        "flt_count": 20,
        "flt_length": (3, min(21, max_answer_length)),
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _push_to_canonical(canonical_key: str, widget_key: str) -> None:
    st.session_state[canonical_key] = st.session_state[widget_key]


def render_filters(
    container,
    suffix: str,
    yearly_frequencies: pd.DataFrame,
    max_answer_length: int,
) -> None:
    """Render the full set of filter controls into the given container.

    Both the desktop sidebar and the mobile in-page expander call this with a
    distinct ``suffix``. Each widget mirrors a single canonical session-state
    value (``flt_*``) and writes back through ``on_change`` so the two copies
    stay in sync and the rest of the app reads one source of truth.
    """
    types_key = f"types_{suffix}"
    st.session_state[types_key] = st.session_state["flt_types"]
    container.multiselect(
        "Puzzle types",
        options=list(PUZZLE_TYPES.keys()),
        key=types_key,
        on_change=_push_to_canonical,
        args=("flt_types", types_key),
    )

    valid_years = available_years(yearly_frequencies, st.session_state["flt_types"])
    year_options = ["All years", *[str(year) for year in valid_years]]
    if st.session_state["flt_year"] not in year_options:
        st.session_state["flt_year"] = "All years"
    year_key = f"year_{suffix}"
    st.session_state[year_key] = st.session_state["flt_year"]
    container.selectbox(
        "Year",
        options=year_options,
        key=year_key,
        on_change=_push_to_canonical,
        args=("flt_year", year_key),
    )

    normalized_key = f"normalized_{suffix}"
    st.session_state[normalized_key] = st.session_state["flt_normalized"]
    container.toggle(
        "Use per-100 puzzle rates",
        key=normalized_key,
        on_change=_push_to_canonical,
        args=("flt_normalized", normalized_key),
    )

    count_key = f"count_{suffix}"
    st.session_state[count_key] = st.session_state["flt_count"]
    container.slider(
        "Number of answers to show",
        min_value=10,
        max_value=100,
        step=5,
        key=count_key,
        on_change=_push_to_canonical,
        args=("flt_count", count_key),
    )

    length_key = f"length_{suffix}"
    st.session_state[length_key] = st.session_state["flt_length"]
    container.slider(
        "Answer length range",
        min_value=1,
        max_value=max_answer_length,
        key=length_key,
        on_change=_push_to_canonical,
        args=("flt_length", length_key),
    )


def main() -> None:
    st.set_page_config(
        page_title="New York Times Crossword Answer Frequencies",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        [data-testid="stToolbar"] {
            visibility: hidden;
            height: 0;
            position: fixed;
        }
        [data-testid="stHeaderActionElements"] {
            display: none;
        }
        section[data-testid="stSidebar"] > div:first-child {
            padding-top: 2.75rem;
        }
        div[data-baseweb="popover"] {
            z-index: 10000;
        }
        .block-container {
            padding-top: 2.25rem;
        }

        /* Desktop and tablets (incl. iPad portrait): keep the native Filters
           sidebar permanent and non-collapsible, and hide the in-page filters. */
        @media (min-width: 768px) {
            [data-testid="stSidebarCollapseButton"] {
                display: none !important;
            }
            .st-key-mobile_filters {
                display: none !important;
            }
        }

        /* Phones: hide the native sidebar; filters live in-page below the
           data-coverage note as an expander. */
        @media (max-width: 767.98px) {
            section[data-testid="stSidebar"],
            [data-testid="stExpandSidebarButton"] {
                display: none !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    frequencies, yearly_frequencies = load_data()

    max_answer_length = int(frequencies["answer"].str.len().max())

    st.title("New York Times Crossword Answer Frequencies")
    st.info(
        """
        Data coverage:
        - Daily: 1993-11-21 to 2026-06-28
        - Mini: 2014-08-21 to 2026-06-28
        - Midi: 2026-02-25 to 2026-06-28

        Normalized rates (per 100 puzzles) are recommended for cross-type comparisons.
        """
    )

    seed_filter_defaults(max_answer_length)

    # Phones: filters live in-page, directly below the data-coverage note
    # (hidden on desktop/tablet via CSS).
    mobile_filters = st.container(key="mobile_filters")
    with mobile_filters.expander("Filters", expanded=False):
        render_filters(st, "mobile", yearly_frequencies, max_answer_length)

    # Desktop / tablet: the native, always-visible sidebar
    # (hidden on phones via CSS).
    st.sidebar.header("Filters")
    render_filters(st.sidebar, "desktop", yearly_frequencies, max_answer_length)

    selected_types = st.session_state["flt_types"]
    selected_year = st.session_state["flt_year"]
    normalized = st.session_state["flt_normalized"]
    word_count = st.session_state["flt_count"]
    min_answer_length, max_selected_answer_length = st.session_state["flt_length"]

    if not selected_types:
        st.warning("Select at least one puzzle type to display frequencies.")
        return

    data = (
        frequencies
        if selected_year == "All years"
        else yearly_frequencies[yearly_frequencies["year"] == int(selected_year)]
    )
    data = add_metric_column(data, selected_types, normalized)
    answer_lengths = data["answer"].str.len()
    data = data[
        answer_lengths.between(min_answer_length, max_selected_answer_length)
    ]
    data = data[data["selected_frequency"] > 0]

    metric_label = format_metric_label(normalized)
    chart_data = (
        data.sort_values(
            ["selected_frequency", "answer"],
            ascending=[False, True],
        )
        .head(word_count)
        .sort_values("selected_frequency", ascending=True)
    )

    chart_title_year = selected_year if selected_year != "All years" else "All Years"
    st.subheader(
        f"Most Frequent Answers - {chart_title_year}"
    )

    if chart_data.empty:
        st.warning("No words match the current filters.")
    else:
        chart_data = chart_data.copy()
        chart_data["display_frequency"] = chart_data["selected_frequency"].round(2)
        fig = px.bar(
            chart_data,
            x="selected_frequency",
            y="answer",
            orientation="h",
            labels={
                "selected_frequency": metric_label,
                "answer": "Answer",
                "display_frequency": metric_label,
            },
            hover_data={"display_frequency": True, "selected_frequency": False},
            color_discrete_sequence=["#1f77b4"],
        )
        fig.update_layout(
            height=max(450, word_count * 24),
            yaxis_title="",
            xaxis_title=metric_label,
            margin=dict(l=40, r=40, t=40, b=80),
        )
        fig.update_yaxes(automargin=True)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Search An Answer")
    query = st.text_input("Answer", placeholder="OREO").strip().upper()

    if query:
        source = frequencies if selected_year == "All years" else yearly_frequencies[
            yearly_frequencies["year"] == int(selected_year)
        ]
        match = source[source["answer"] == query]

        if match.empty:
            st.warning(f"No results found for {query}.")
        else:
            row = match.iloc[0]

            type_phrases = []
            for label, puzzle_type in PUZZLE_TYPES.items():
                count = int(row[f"{puzzle_type}_count"])
                if count > 0:
                    rank = frequency_rank(source, f"{puzzle_type}_count", count)
                    type_phrases.append(
                        f"the {ordinal(rank)} most common **{label}** answer"
                    )

            overall_rank = frequency_rank(source, "total", int(row["total"]))
            scope_suffix = "" if selected_year == "All years" else f" in {selected_year}"
            summary = (
                f"**{query}** is the {ordinal(overall_rank)} most common answer "
                f"overall{scope_suffix}."
            )

            if type_phrases:
                if len(type_phrases) == 1:
                    types_joined = type_phrases[0]
                else:
                    types_joined = (
                        ", ".join(type_phrases[:-1]) + f", and {type_phrases[-1]}"
                    )
                lead_in = (
                    "It is also"
                    if selected_year == "All years"
                    else "That year it was also"
                )
                summary += f" {lead_in} {types_joined}."

            st.markdown(summary)

            search_rows = []
            for label, puzzle_type in PUZZLE_TYPES.items():
                search_rows.append(
                    {
                        "Puzzle type": label,
                        "Raw count": int(row[f"{puzzle_type}_count"]),
                        "Per 100 puzzles": round(
                            float(row[f"avg_per_100_{puzzle_type}"]),
                            2,
                        ),
                    }
                )

            search_data = pd.DataFrame(search_rows)
            year_label = "All Years" if selected_year == "All years" else selected_year
            raw_fig = px.bar(
                search_data,
                x="Puzzle type",
                y="Raw count",
                title=f"{query} Raw Counts ({year_label})",
                text="Raw count",
                color_discrete_sequence=["#1f77b4"],
            )
            rate_fig = px.bar(
                search_data,
                x="Puzzle type",
                y="Per 100 puzzles",
                title=f"{query} Per 100 Puzzles ({year_label})",
                text="Per 100 puzzles",
                color_discrete_sequence=["#1f77b4"],
            )
            raw_fig.update_traces(textposition="outside")
            rate_fig.update_traces(textposition="outside")
            raw_fig.update_layout(margin=dict(t=60, b=60))
            rate_fig.update_layout(margin=dict(t=60, b=60))

            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(raw_fig, use_container_width=True)
            with col2:
                st.plotly_chart(rate_fig, use_container_width=True)

            st.dataframe(search_data, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
