"""
Publish the current contents of ../outputs/weekly/ (from a run_weekly.py run)
into the sibling jonm_site static repo as /ff/<season>/week-<num>/.

This script only writes files inside the site working tree. It does NOT
run any git commands - review the diff and commit/push manually.
"""
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, for `src.*` imports

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.common.ff_site import discover_weeks, discover_years, render_ff_index, sync_static_pages
from src.common.paths import (
    TEMPLATES_DIR,
    WEEKLY_OUTPUTS_DIR,
)

load_dotenv()

SITE_REPO_PATH = os.getenv("SITE_REPO_PATH")
if not SITE_REPO_PATH:
    raise SystemExit("SITE_REPO_PATH not set - add it to your .env file.")


@dataclass(frozen=True)
class FantasySection:
    key: str
    title: str
    description: str
    image_template: str  # gets .format(season=..., week=...)


FANTASY_SECTIONS: list[FantasySection] = [
    FantasySection(
        key="matchup_matrix",
        title="Matchup Matrix",
        description=(
            "This is the result of each matchup over/under the league average for the week.\n\n"
            "- Right of the vertical line = scored above average\n"
            "- Above the horizontal line = opponent scored above average\n\n"
            "Top right = unlucky losses or tough wins. Bottom left = lucky wins or missed opportunities."
        ),
        image_template="9-{season}_{week}_matchup_chart.png",
    ),
    FantasySection(
        key="all_play",
        title="All-Play Win/Loss",
        description=(
            "This shows each team's record if they played every team each week. "
            "It helps reduce schedule luck and shows how each team is actually performing."
        ),
        image_template="4-all_play_wins_{season}_{week}.png",
    ),
    FantasySection(
        key="team_scores",
        title="Team Scores",
        description="These are the box plots for each team using total scores YTD.",
        image_template="5-median_scores_{season}_max{week}.png",
    ),
    FantasySection(
        key="power_rank",
        title="Power Rank by Week",
        description="This shows weekly power ranking movement based on expected team strength.",
        image_template="7-power_ranking_by_week_{season}_max{week}.png",
    ),
    FantasySection(
        key="current_vs_power",
        title="Current Rank vs Power Rank",
        description="This compares actual standings against power ranking.",
        image_template="8-{season}_{week}_power_ranking.png",
    ),
    FantasySection(
        key="draft_vs_final_movement",
        title="Draft vs Final Rank Movement",
        description="Shows how far each team has moved up or down from their preseason draft position, season to date.",
        image_template="2-diff_draft_to_final_{season}_max{week}.png",
    ),
    FantasySection(
        key="actual_vs_optimal",
        title="Actual vs Optimal Lineup",
        description="This shows actual and optimal scores for the week.",
        image_template="10-{season}_{week}_actual_vs_optimal.png",
    ),
    FantasySection(
        key="opponent_difficulty_heatmap",
        title="Opponent Difficulty Heatmap",
        description=(
            "This shows each team's opponent score above or below their cumulative average.\n"
            "Red = opponent scored above their average, green = opponent scored below their average."
        ),
        image_template="12-{season}_{week}_opp_difficulty_heatmap.png",
    ),
    FantasySection(
        key="opponent_difficulty_summary",
        title="Opponent Difficulty Summary",
        description="This summarizes opponent scoring difficulty across all weeks.",
        image_template="14-{season}_{week}_opp_difficulty_summary.png",
    ),
]


@dataclass(frozen=True)
class ChartSpec:
    filename: str
    title: str
    description: str


def build_manifest(season: int, week: int) -> list[ChartSpec]:
    """Resolve FANTASY_SECTIONS' filename templates for a specific (season, week).

    Anything not found in outputs/weekly/ is skipped with a warning rather than
    failing the whole run.
    """
    return [
        ChartSpec(
            filename=section.image_template.format(season=season, week=week),
            title=section.title,
            description=section.description,
        )
        for section in FANTASY_SECTIONS
    ]


def copy_charts(outputs_dir: Path, dest_charts_dir: Path, manifest: list[ChartSpec]) -> list[ChartSpec]:
    dest_charts_dir.mkdir(parents=True, exist_ok=True)
    published: list[ChartSpec] = []
    for chart in manifest:
        src = outputs_dir / chart.filename
        if not src.exists():
            print(f"  [skip] {chart.filename} (not found in outputs/)")
            continue
        shutil.copy2(src, dest_charts_dir / chart.filename)
        print(f"  [ok]   {chart.filename}")
        published.append(chart)
    return published


def main(season: int, week: int) -> None:

    outputs_dir = Path(WEEKLY_OUTPUTS_DIR).resolve()
    site_repo = Path(SITE_REPO_PATH)
    ff_dir = site_repo / "public" / "ff"

    if not outputs_dir.is_dir():
        raise SystemExit(f"outputs dir not found: {outputs_dir}")
    if not (site_repo / ".git").is_dir():
        raise SystemExit(f"jonm_site repo not found at: {site_repo}")

    week_padded = f"{week:02d}"
    week_dir = ff_dir / str(season) / f"week-{week_padded}"

    print(f"Publishing season={season} week={week}")
    print(f"  outputs:   {outputs_dir}")
    print(f"  site repo: {site_repo}")
    print(f"  target:    {week_dir}")

    manifest = build_manifest(season, week)
    published = copy_charts(outputs_dir, week_dir / "charts", manifest)

    if not published:
        raise SystemExit(
            "No chart files found for this season/week - check outputs/ contents "
            "and confirm run_weekly.py's SEASON/WEEK match."
        )

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # week_dir/charts already has this week's files on disk at this point,
    # so these directory scans pick it up automatically.
    weekly_seasons = discover_weeks(ff_dir)
    yearly_seasons = discover_years(ff_dir)

    week_html = env.get_template("week_index.html.j2").render(
        season=season, week=week, week_padded=week_padded, charts=published,
        weekly_seasons=weekly_seasons, yearly_seasons=yearly_seasons,
        current_season=str(season), current_week=week,
    )
    (week_dir / "index.html").write_text(week_html, encoding="utf-8")
    print(f"  wrote:     {week_dir / 'index.html'}")

    render_ff_index(env, ff_dir)
    sync_static_pages(env, site_repo)

    print("\nDone. Review the diff in jonm_site, then commit/push.")


if __name__ == "__main__":
    s = int(input('Season: '))
    w = int(input('Week: '))

    main(s, w)