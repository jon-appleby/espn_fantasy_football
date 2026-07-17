"""Shared helpers for publishing weekly/yearly fantasy football reports to jonm_site.

Used by both scripts/publish_to_site.py (weekly) and
scripts/publish_yearly_to_site.py (yearly) so the ff/ landing page always
reflects whatever has actually been published, regardless of which script
ran most recently.
"""
from pathlib import Path

from jinja2 import Environment


def discover_weeks(ff_dir: Path) -> dict[str, list[int]]:
    """Scan public/ff/<season>/week-<NN>/charts/ for non-empty weeks."""
    seasons: dict[str, list[int]] = {}
    for charts_dir in sorted(ff_dir.glob("*/week-*/charts")):
        if not charts_dir.is_dir() or not any(charts_dir.iterdir()):
            continue  # skips empty stub dirs
        week_dir = charts_dir.parent
        season = week_dir.parent.name
        try:
            week_num = int(week_dir.name.removeprefix("week-"))
        except ValueError:
            continue
        seasons.setdefault(season, []).append(week_num)
    return {s: sorted(seasons[s], reverse=True) for s in sorted(seasons, reverse=True)}


def discover_years(ff_dir: Path) -> list[int]:
    """Scan public/ff/yearly/<end_year>/charts/ for published all-time snapshots, newest first."""
    yearly_dir = ff_dir / "yearly"
    if not yearly_dir.is_dir():
        return []
    years = []
    for charts_dir in sorted(yearly_dir.glob("*/charts")):
        if not charts_dir.is_dir() or not any(charts_dir.iterdir()):
            continue
        try:
            years.append(int(charts_dir.parent.name))
        except ValueError:
            continue
    return sorted(years, reverse=True)


def render_ff_index(env: Environment, ff_dir: Path) -> None:
    """Regenerate public/ff/index.html from whatever weekly/yearly reports currently exist on disk."""
    weekly_seasons = discover_weeks(ff_dir)
    yearly_seasons = discover_years(ff_dir)
    html = env.get_template("ff_index.html.j2").render(
        weekly_seasons=weekly_seasons, yearly_seasons=yearly_seasons,
    )
    (ff_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"  wrote:     {ff_dir / 'index.html'}")
