"""Shared helpers for publishing weekly/yearly fantasy football reports to jonm_site.

Used by both scripts/publish_to_site.py (weekly) and
scripts/publish_yearly_to_site.py (yearly) so the ff/ landing page - and the
Fantasy Football nav branch embedded in jonm_site's hand-authored static
pages (About, Experience, Projects, ...) - always reflect whatever has
actually been published, regardless of which script ran most recently.
"""
import re
from pathlib import Path

from jinja2 import Environment

FF_NAV_MARKER_RE = re.compile(
    r"(<!-- ff-nav:start -->)(.*?)(<!-- ff-nav:end -->)",
    re.DOTALL,
)


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


def render_ff_nav_fragment(env: Environment, ff_dir: Path) -> str:
    """Render just the Weekly/Yearly Reports nav subtree (no wrapping page)."""
    weekly_seasons = discover_weeks(ff_dir)
    yearly_seasons = discover_years(ff_dir)
    return env.get_template("_ff_nav_children.html.j2").render(
        weekly_seasons=weekly_seasons, yearly_seasons=yearly_seasons,
        current_season=None, current_week=None, current_year=None,
    )


def sync_static_pages(env: Environment, site_repo: Path) -> None:
    """Refresh the Fantasy Football nav subtree embedded in jonm_site's
    hand-authored static pages (About, Experience, Projects, ...), which
    have no build step of their own. Any .html file under public/ (EXCLUDING
    public/ff/ itself) containing <!-- ff-nav:start --> ... <!-- ff-nav:end -->
    markers gets the content between them replaced with the current
    weekly/yearly report list. public/ff/ pages are skipped here because
    they're rendered directly with their own page-specific context (e.g. the
    current week/year auto-expanded and marked active) - overwriting them
    with this generic, context-less fragment would clobber that.
    """
    ff_dir = site_repo / "public" / "ff"
    fragment = render_ff_nav_fragment(env, ff_dir)
    updated = 0
    for html_file in (site_repo / "public").rglob("*.html"):
        if ff_dir in html_file.parents:
            continue
        text = html_file.read_text(encoding="utf-8")
        if "<!-- ff-nav:start -->" not in text:
            continue
        new_text = FF_NAV_MARKER_RE.sub(
            lambda m: f"{m.group(1)}\n{fragment}{m.group(3)}", text,
        )
        if new_text != text:
            html_file.write_text(new_text, encoding="utf-8")
            updated += 1
            print(f"  synced nav: {html_file.relative_to(site_repo)}")
    if updated:
        print(f"  ({updated} static page(s) had their Fantasy Football nav refreshed)")
