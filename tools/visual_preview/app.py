"""Optionales Streamlit-Skeleton für die lokale Visual Preview (LQ-019 Phase 2).

WICHTIG: Dieses Modul ist **ohne Streamlit importierbar** — der Streamlit-Import
erfolgt ausschließlich innerhalb von ``main()`` (try/except). Es gibt keine
Pflicht-Dependency, keine Netzwerk-Calls, keine Dateischreiboperationen, keine
Echtdaten. Rein lokale, technische Anzeige — keine Profitabilitätsbewertung,
keine Handelsempfehlung.

Start (nach optionaler Streamlit-Installation):
    streamlit run tools/visual_preview/app.py
"""

from __future__ import annotations

from .preview_logic import (
    SAFETY_NOTES,
    build_preview_datasets,
    generate_preview_summary,
)

_TITLE = "Liquent — understand liquidity"

_STREAMLIT_MISSING = (
    "Streamlit is not installed. Install the optional visual extra before "
    "running this preview."
)


def main() -> None:
    """Startet das Streamlit-Skeleton, falls Streamlit verfügbar ist.

    Ohne Streamlit wird eine klare Meldung ausgegeben (kein Traceback, keine
    automatische Installation, keine Netzwerk-Calls).
    """
    try:
        import streamlit as st
    except ImportError:
        print(_STREAMLIT_MISSING)
        return

    st.title(_TITLE)
    for note in SAFETY_NOTES:
        st.caption(note)

    datasets = build_preview_datasets()
    dataset_key = st.sidebar.selectbox("Dataset", list(datasets.keys()))
    strategy_key = st.sidebar.selectbox("Strategy", ["v0", "v1"])

    params: dict[str, object] = {
        "lookback_bars": st.sidebar.number_input("lookback_bars", value=12, step=1),
        "stop_distance_pct": st.sidebar.number_input("stop_distance_pct", value=0.01),
        "allow_short": st.sidebar.checkbox("allow_short", value=True),
        "min_strength": st.sidebar.number_input("min_strength", value=0.0),
    }
    if strategy_key == "v1":
        params["breakout_threshold_pct"] = st.sidebar.number_input(
            "breakout_threshold_pct", value=0.0
        )
        params["cooldown_bars"] = st.sidebar.number_input("cooldown_bars", value=0, step=1)
        use_limit = st.sidebar.checkbox("max_signals_per_day enabled", value=False)
        if use_limit:
            params["max_signals_per_day"] = st.sidebar.number_input(
                "max_signals_per_day", value=1, step=1
            )

    summary = generate_preview_summary(dataset_key, strategy_key, params)
    st.metric("signals_total", summary["signals_total"])
    st.subheader("Strategy")
    st.json(summary["strategy"])
    st.subheader("Signals")
    st.table(summary["signals"])


if __name__ == "__main__":
    main()
