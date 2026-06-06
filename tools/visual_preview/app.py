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
    CSV_REQUIRED_COLUMNS,
    SAFETY_NOTES,
    SAMPLE_CSV_TEMPLATE,
    SAMPLE_OHLCV_CSV_TEMPLATE,
    build_dataset_from_csv_text,
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

    # Header.
    st.title(_TITLE)
    st.caption("Local visual preview for synthetic signal inspection")
    # Safety-Banner (alle Hinweise sichtbar).
    st.info("  •  ".join(SAFETY_NOTES))

    # --- Sidebar: Dataset mode / Strategy / Parameter ---
    datasets = build_preview_datasets()
    st.sidebar.header("Dataset")
    dataset_mode = st.sidebar.radio(
        "Dataset mode", ["Synthetic dataset", "Local CSV upload"]
    )
    # `dataset_arg` ist entweder ein synthetischer Key oder ein PreviewDataset.
    dataset_arg: object | None = None
    if dataset_mode == "Synthetic dataset":
        dataset_arg = st.sidebar.selectbox("Dataset", list(datasets.keys()))
    else:
        # CSV-Format-Hinweis + kopierbare Beispiele (kein Download-Button).
        st.subheader("CSV upload")
        st.markdown(
            "Two schemas are accepted (auto-detected from the header):  \n"
            "**bid/ask** (default): `" + "`, `".join(CSV_REQUIRED_COLUMNS) + "` "
            "(+ optional `volume`).  \n"
            "**OHLCV**: `timestamp,open,high,low,close` (+ optional `volume`) — "
            "mapped to `bid = ask = close` (so `mid = close`).  \n"
            "**timestamp** must be ISO-8601 with timezone, e.g. `+00:00`; prices "
            "must be valid (`ask >= bid`; `low <= open/close <= high`); `volume` "
            "defaults to 1.0 if omitted/empty.  \n"
            "Upload is local/in-memory only. Liquent does not save uploaded CSV files."
        )
        st.caption("bid/ask example")
        st.code(SAMPLE_CSV_TEMPLATE, language="csv")
        st.caption("OHLCV example")
        st.code(SAMPLE_OHLCV_CSV_TEMPLATE, language="csv")
        uploaded = st.sidebar.file_uploader("Upload local CSV", type=["csv"])
        if uploaded is None:
            st.info(
                "Upload a local CSV (timestamp,bid,ask[,volume]) to preview. "
                "The file is read in memory only — nothing is stored, downloaded "
                "or sent anywhere."
            )
            return
        try:
            csv_text = uploaded.getvalue().decode("utf-8")
            dataset_arg = build_dataset_from_csv_text(uploaded.name, csv_text)
        except (ValueError, UnicodeDecodeError) as exc:
            st.error(f"Invalid CSV: {exc}")
            return

    st.sidebar.header("Strategy")
    strategy_key = st.sidebar.selectbox("Strategy", ["v0", "v1"])

    st.sidebar.header("Shared parameters")
    params: dict[str, object] = {
        "lookback_bars": st.sidebar.number_input("lookback_bars", value=12, step=1),
        "stop_distance_pct": st.sidebar.number_input("stop_distance_pct", value=0.01),
        "allow_short": st.sidebar.checkbox("allow_short", value=True),
        "min_strength": st.sidebar.number_input("min_strength", value=0.0),
    }
    if strategy_key == "v1":
        st.sidebar.header("v1 parameters")
        params["breakout_threshold_pct"] = st.sidebar.number_input(
            "breakout_threshold_pct", value=0.0
        )
        params["cooldown_bars"] = st.sidebar.number_input("cooldown_bars", value=0, step=1)
        if st.sidebar.checkbox("max_signals_per_day enabled", value=False):
            params["max_signals_per_day"] = st.sidebar.number_input(
                "max_signals_per_day", value=1, step=1
            )
    st.sidebar.header("Cost parameters")
    st.sidebar.caption("not used in signal-only preview")

    summary = generate_preview_summary(dataset_arg, strategy_key, params)
    tech = summary["technical_summary"]

    # --- Technical Summary ---
    st.subheader("Technical summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("dataset", tech["dataset_name"])
    c2.metric("strategy", tech["strategy_key"])
    c3.metric("bars", tech["bars"])
    c4, c5 = st.columns(2)
    c4.metric("signals_total", tech["signals_total"])
    c5.caption(f"{tech['first_timestamp']} → {tech['last_timestamp']}")

    # --- Mid-price chart (mit Long/Short-Markern als separate Serien) ---
    st.subheader("Mid-price chart")
    st.line_chart(
        summary["chart_rows"],
        x="timestamp",
        y=["mid", "long_signal_price", "short_signal_price"],
    )

    # --- Signal table ---
    st.subheader("Signal table")
    st.dataframe(summary["signals"])

    # --- Strategy metadata ---
    st.subheader("Strategy metadata")
    st.table([{"parameter": k, "value": v} for k, v in summary["strategy"]["params"].items()])

    # --- Safety notes ---
    st.subheader("Safety notes")
    for note in summary["safety_notes"]:
        st.caption(note)


if __name__ == "__main__":
    main()
