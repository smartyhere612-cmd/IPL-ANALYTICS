# =============================================================================
# IPL Data Analytics — Flask Application Entry Point
# Landing page metrics are computed from deliveries.csv (Pandas).
# Run: python app.py
# =============================================================================

from functools import wraps
from pathlib import Path

import pandas as pd
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

# -----------------------------------------------------------------------------
# Static credentials (demo only — not for production)
# -----------------------------------------------------------------------------
USERNAME = "admin"
PASSWORD = "admin123"

# CSV path: project root (same folder as this file)
DELIVERIES_CSV = Path(__file__).resolve().parent / "deliveries.csv"

# Columns required for analytics (subset speeds up read on large files)
USECOLS = [
    "match_id",
    "inning",
    "batting_team",
    "bowling_team",
    "over",
    "ball",
    "batter",
    "bowler",
    "batsman_runs",
    "extra_runs",
    "total_runs",
    "extras_type",
    "is_wicket",
    "dismissal_kind",
]

app = Flask(__name__)
app.secret_key = "ipl-analytics-demo-secret-key-change-in-production"

# Module-level cache: compute once per process (reload app to refresh CSV)
_analytics_cache = None


def _empty_payload(error_message=None):
    """Fallback structure when CSV is missing or unreadable."""
    return {
        "ok": False,
        "error": error_message or "Could not load deliveries data.",
        "summary": {
            "total_deliveries": 0,
            "unique_matches": 0,
            "total_runs": 0,
            "total_wickets": 0,
            "unique_batters": 0,
            "unique_teams": 0,
            "total_sixes": 0,
            "total_fours": 0,
            "highest_innings_runs": 0,
            "most_sixes_batter": "—",
        },
        "chart_team_runs": {"labels": [], "data": []},
        "chart_batter_runs": {"labels": [], "data": []},
        "chart_bowler_wickets": {"labels": [], "data": []},
        "chart_runs_by_over": {"labels": [], "data": []},
        "chart_extras": {"labels": [], "data": []},
        "chart_dismissals": {"labels": [], "data": []},
        "chart_bowling_conceded": {"labels": [], "data": []},
        "chart_top_matches": {"labels": [], "data": []},
        "chart_innings_hist": {"labels": [], "data": []},
        "table_top_batters": [],
        "table_top_bowlers": [],
        "table_top_innings": [],
        "table_top_six_hitters": [],
    }


def load_deliveries_analytics():
    """
    Read deliveries.csv with Pandas and build summary stats + chart/table payloads.
    Results are cached in memory for fast repeat requests.
    """
    global _analytics_cache
    if _analytics_cache is not None:
        return _analytics_cache

    if not DELIVERIES_CSV.is_file():
        _analytics_cache = _empty_payload("deliveries.csv not found next to app.py.")
        return _analytics_cache

    try:
        df = pd.read_csv(
            DELIVERIES_CSV,
            usecols=USECOLS,
            low_memory=False,
            na_values=["NA"],
        )
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        _analytics_cache = _empty_payload(f"CSV read error: {exc}")
        return _analytics_cache

    # Normalize numeric columns
    for col in ("total_runs", "batsman_runs", "extra_runs", "is_wicket", "over", "ball"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    total_deliveries = int(len(df))
    unique_matches = int(df["match_id"].nunique())
    total_runs = int(df["total_runs"].sum())
    total_wickets = int(df["is_wicket"].sum())
    unique_batters = int(df["batter"].nunique())
    all_teams = pd.concat([df["batting_team"], df["bowling_team"]], ignore_index=True)
    unique_teams = int(all_teams.nunique())
    total_sixes = int((df["batsman_runs"] == 6).sum())
    total_fours = int((df["batsman_runs"] == 4).sum())

    # Highest single-innings total (match_id + inning + batting_team)
    inn = (
        df.groupby(["match_id", "inning", "batting_team"], as_index=False)["total_runs"]
        .sum()
        .sort_values("total_runs", ascending=False)
    )
    highest_innings_runs = int(inn["total_runs"].iloc[0]) if len(inn) else 0

    team_runs = (
        df.groupby("batting_team", as_index=False)["total_runs"]
        .sum()
        .sort_values("total_runs", ascending=False)
        .head(10)
    )
    batter_runs = (
        df.groupby("batter", as_index=False)["batsman_runs"]
        .sum()
        .sort_values("batsman_runs", ascending=False)
        .head(12)
    )

    wk = df[df["is_wicket"] == 1]
    bowler_wk = (
        wk.groupby("bowler", as_index=False)
        .size()
        .rename(columns={"size": "wickets"})
        .sort_values("wickets", ascending=False)
        .head(12)
    )

    runs_by_over = (
        df.groupby("over", as_index=False)["total_runs"]
        .sum()
        .sort_values("over")
    )

    et = df[df["extra_runs"] > 0].copy()
    et["extras_type"] = et["extras_type"].fillna("").replace("", "unspecified")
    extras_grp = et.groupby("extras_type", as_index=False)["extra_runs"].sum().sort_values(
        "extra_runs", ascending=False
    )

    dk = wk["dismissal_kind"].fillna("unknown")
    dismiss = dk.value_counts().head(8)

    top_innings = inn.head(8)

    six_lead = (
        df[df["batsman_runs"] == 6]
        .groupby("batter", as_index=False)
        .size()
        .rename(columns={"size": "sixes"})
        .sort_values("sixes", ascending=False)
    )
    most_sixes_batter = str(six_lead["batter"].iloc[0]) if len(six_lead) else "—"

    bowl_def = (
        df.groupby("bowling_team", as_index=False)["total_runs"]
        .sum()
        .sort_values("total_runs", ascending=False)
        .head(10)
    )
    match_tot = (
        df.groupby("match_id", as_index=False)["total_runs"]
        .sum()
        .sort_values("total_runs", ascending=False)
        .head(18)
    )
    chart_top_matches = {
        "labels": [str(int(x)) for x in match_tot["match_id"]],
        "data": [int(x) for x in match_tot["total_runs"]],
    }
    chart_bowling_conceded = {
        "labels": bowl_def["bowling_team"].tolist(),
        "data": [int(x) for x in bowl_def["total_runs"].tolist()],
    }
    chart_innings_hist = {"labels": [], "data": []}
    if len(inn) >= 3:
        hist_bins = pd.cut(inn["total_runs"], bins=12, duplicates="drop")
        hist_counts = hist_bins.value_counts().sort_index()
        chart_innings_hist = {
            "labels": [str(i) for i in hist_counts.index],
            "data": [int(x) for x in hist_counts.values],
        }

    _analytics_cache = {
        "ok": True,
        "error": None,
        "summary": {
            "total_deliveries": total_deliveries,
            "unique_matches": unique_matches,
            "total_runs": total_runs,
            "total_wickets": total_wickets,
            "unique_batters": unique_batters,
            "unique_teams": unique_teams,
            "total_sixes": total_sixes,
            "total_fours": total_fours,
            "highest_innings_runs": highest_innings_runs,
            "most_sixes_batter": most_sixes_batter,
        },
        "chart_team_runs": {
            "labels": team_runs["batting_team"].tolist(),
            "data": [int(x) for x in team_runs["total_runs"].tolist()],
        },
        "chart_batter_runs": {
            "labels": batter_runs["batter"].tolist(),
            "data": [int(x) for x in batter_runs["batsman_runs"].tolist()],
        },
        "chart_bowler_wickets": {
            "labels": bowler_wk["bowler"].tolist(),
            "data": [int(x) for x in bowler_wk["wickets"].tolist()],
        },
        "chart_runs_by_over": {
            "labels": [str(int(x)) for x in runs_by_over["over"].tolist()],
            "data": [int(x) for x in runs_by_over["total_runs"].tolist()],
        },
        "chart_extras": {
            "labels": extras_grp["extras_type"].tolist(),
            "data": [int(x) for x in extras_grp["extra_runs"].tolist()],
        },
        "chart_dismissals": {
            "labels": dismiss.index.tolist(),
            "data": [int(x) for x in dismiss.values.tolist()],
        },
        "chart_bowling_conceded": chart_bowling_conceded,
        "chart_top_matches": chart_top_matches,
        "chart_innings_hist": chart_innings_hist,
        "table_top_batters": batter_runs.head(10)[["batter", "batsman_runs"]]
        .rename(columns={"batsman_runs": "runs"})
        .to_dict("records"),
        "table_top_bowlers": bowler_wk.head(10).to_dict("records"),
        "table_top_innings": top_innings.assign(
            runs=lambda x: x["total_runs"].astype(int)
        )[["match_id", "inning", "batting_team", "runs"]].to_dict("records"),
        "table_top_six_hitters": six_lead.head(10).to_dict("records"),
    }
    return _analytics_cache


def build_stats(landing):
    """KPI dict for dashboard-style pages from cached analytics."""
    s = landing["summary"]
    return {
        "total_matches": s["unique_matches"],
        "total_runs": s["total_runs"],
        "highest_score": s["highest_innings_runs"],
        "total_deliveries": s["total_deliveries"],
        "strike_rate": round(
            (s["total_runs"] / max(s["total_deliveries"] - s["total_wickets"], 1)) * 100, 1
        ),
        "orange_cap": landing["table_top_batters"][0]["batter"]
        if landing["table_top_batters"]
        else "—",
        "purple_cap": landing["table_top_bowlers"][0]["bowler"]
        if landing["table_top_bowlers"]
        else "—",
        "most_sixes": s.get("most_sixes_batter", "—"),
        "total_wickets": s["total_wickets"],
        "total_sixes": s["total_sixes"],
        "total_fours": s["total_fours"],
    }


def build_charts(landing):
    """Chart.js payloads derived from deliveries aggregates."""
    return {
        "team": landing["chart_team_runs"],
        "batter": landing["chart_batter_runs"],
        "bowler": landing["chart_bowler_wickets"],
        "over": landing["chart_runs_by_over"],
        "extras": landing["chart_extras"],
        "dismissals": landing["chart_dismissals"],
        "bowling": landing["chart_bowling_conceded"],
        "top_matches": landing["chart_top_matches"],
        "innings_hist": landing["chart_innings_hist"],
    }


def login_required(view_func):
    """Decorator: dashboard routes require an authenticated session."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if session.get("logged_in"):
            return view_func(*args, **kwargs)
        flash("Please log in to access the dashboard.", "warning")
        return redirect(url_for("login"))

    return wrapped


@app.route("/")
def index():
    """
    Landing page: hero + analytics driven by deliveries.csv (via Pandas).
    """
    landing = load_deliveries_analytics()
    charts = {
        "team": landing["chart_team_runs"],
        "batter": landing["chart_batter_runs"],
        "bowler": landing["chart_bowler_wickets"],
        "over": landing["chart_runs_by_over"],
        "extras": landing["chart_extras"],
        "dismissals": landing["chart_dismissals"],
    }
    return render_template("index.html", landing=landing, charts=charts)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Session-based login; only admin / admin123 accepted."""
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        user = request.form.get("username", "").strip()
        pwd = request.form.get("password", "")

        if user == USERNAME and pwd == PASSWORD:
            session["logged_in"] = True
            session["username"] = user
            return redirect(url_for("dashboard"))

        # Clean, consistent denial message for invalid attempts
        flash("Invalid Credentials", "danger")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Registration UI only (no backend persistence)."""
    return render_template("signup.html")


@app.route("/dashboard")
@login_required
def dashboard():
    """Overview KPIs and charts (requires login)."""
    landing = load_deliveries_analytics()
    return render_template(
        "dashboard.html",
        active_nav="overview",
        stats=build_stats(landing),
        landing=landing,
        charts=build_charts(landing),
    )


@app.route("/teams")
@login_required
def teams():
    """Team batting and bowling conceded from deliveries.csv."""
    landing = load_deliveries_analytics()
    return render_template(
        "teams.html",
        active_nav="teams",
        stats=build_stats(landing),
        landing=landing,
        charts=build_charts(landing),
    )


@app.route("/players")
@login_required
def players():
    """Batter and bowler leaderboards."""
    landing = load_deliveries_analytics()
    return render_template(
        "players.html",
        active_nav="players",
        stats=build_stats(landing),
        landing=landing,
        charts=build_charts(landing),
    )


@app.route("/matches")
@login_required
def matches():
    """Match-level patterns: overs, extras, dismissals."""
    landing = load_deliveries_analytics()
    return render_template(
        "matches.html",
        active_nav="matches",
        stats=build_stats(landing),
        landing=landing,
        charts=build_charts(landing),
    )


@app.route("/season")
@login_required
def season():
    """Season-style summaries: score distributions and top matches."""
    landing = load_deliveries_analytics()
    return render_template(
        "season.html",
        active_nav="season",
        stats=build_stats(landing),
        landing=landing,
        charts=build_charts(landing),
    )


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
