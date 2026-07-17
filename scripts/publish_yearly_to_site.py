"""
Publish the current contents of ../outputs/yearly/ (from a run_yearly.py run)
into the sibling jonm_site static repo as /ff/yearly/<end_year>/.

This script only writes files inside the site working tree. It does NOT
run any git commands - review the diff and commit/push manually.

The (start_year, end_year) range is detected automatically from the
all_time_summary_<start>-<end>.csv file already in outputs/yearly/ - no
season/week-style input needed, since there's only ever one "current"
all-time report to publish.
"""
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, for `src.*` imports

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.common.ff_site import render_ff_index
from src.common.paths import (
    TEMPLATES_DIR,
    YEARLY_OUTPUTS_DIR,
)

load_dotenv()

SITE_REPO_PATH = os.getenv("SITE_REPO_PATH")
if not SITE_REPO_PATH:
    raise SystemExit("SITE_REPO_PATH not set - add it to your .env file.")


@dataclass(frozen=True)
class YearlySection:
    key: str
    title: str
    description: str
    image_template: str  # gets .format(start_year=..., end_year=...)


YEARLY_SECTIONS: list[YearlySection] = [
    YearlySection(
        key="overall_ranking",
        title="All-Time Overall Ranking",
        description="Each manager's actual win rate plotted against their all-play win rate across every season. Bubble size shows championships won.",
        image_template="all_time_overall_ranking_{start_year}-{end_year}.png",
    ),
    YearlySection(
        key="head_to_head",
        title="Head-to-Head Records",
        description="All-time head-to-head win/loss record between every pair of managers.",
        image_template="all_time_head_to_head_{start_year}-{end_year}.png",
    ),
    YearlySection(
        key="scoring_overview",
        title="Scoring Overview",
        description="Each manager's scoring compared against their projected totals, all-time.",
        image_template="all_time_scoring_overview_{start_year}-{end_year}.png",
    ),
]


@dataclass(frozen=True)
class ChartSpec:
    filename: str
    title: str
    description: str


YEAR_RANGE_RE = re.compile(r"^all_time_summary_(\d{4})-(\d{4})\.csv$")


def detect_year_range(outputs_dir: Path) -> tuple[int, int]:
    """Find the (start_year, end_year) of the most recent run_yearly.py output."""
    matches = [YEAR_RANGE_RE.match(p.name) for p in outputs_dir.glob("all_time_summary_*.csv")]
    matches = [m for m in matches if m]
    if not matches:
        raise SystemExit(
            f"No all_time_summary_<start>-<end>.csv found in {outputs_dir} - run run_yearly.py first."
        )
    if len(matches) > 1:
        found = ", ".join(m.group(0) for m in matches)
        raise SystemExit(
            f"Multiple all_time_summary_*.csv files found in {outputs_dir} ({found}) - "
            "remove the stale one(s) so it's unambiguous which to publish."
        )
    start_year, end_year = matches[0].groups()
    return int(start_year), int(end_year)


def build_manifest(start_year: int, end_year: int) -> list[ChartSpec]:
    return [
        ChartSpec(
            filename=section.image_template.format(start_year=start_year, end_year=end_year),
            title=section.title,
            description=section.description,
        )
        for section in YEARLY_SECTIONS
    ]


def copy_charts(outputs_dir: Path, dest_charts_dir: Path, manifest: list[ChartSpec]) -> list[ChartSpec]:
    dest_charts_dir.mkdir(parents=True, exist_ok=True)
    published: list[ChartSpec] = []
    for chart in manifest:
        src = outputs_dir / chart.filename
        if not src.exists():
            print(f"  [skip] {chart.filename} (not found in outputs/yearly/)")
            continue
        shutil.copy2(src, dest_charts_dir / chart.filename)
        print(f"  [ok]   {chart.filename}")
        published.append(chart)
    return published


def main() -> None:
    outputs_dir = Path(YEARLY_OUTPUTS_DIR).resolve()
    site_repo = Path(SITE_REPO_PATH)
    ff_dir = site_repo / "public" / "ff"

    if not outputs_dir.is_dir():
        raise SystemExit(f"outputs dir not found: {outputs_dir}")
    if not (site_repo / ".git").is_dir():
        raise SystemExit(f"jonm_site repo not found at: {site_repo}")

    start_year, end_year = detect_year_range(outputs_dir)
    year_dir = ff_dir / "yearly" / str(end_year)

    print(f"Publishing all-time stats {start_year}-{end_year}")
    print(f"  outputs:   {outputs_dir}")
    print(f"  site repo: {site_repo}")
    print(f"  target:    {year_dir}")

    manifest = build_manifest(start_year, end_year)
    published = copy_charts(outputs_dir, year_dir / "charts", manifest)

    if not published:
        raise SystemExit(
            "No chart files found for this year range - check outputs/yearly/ contents."
        )

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    yearly_html = env.get_template("yearly_index.html.j2").render(
        start_year=start_year, end_year=end_year, charts=published,
    )
    (year_dir / "index.html").write_text(yearly_html, encoding="utf-8")
    print(f"  wrote:     {year_dir / 'index.html'}")

    render_ff_index(env, ff_dir)

    print("\nDone. Review the diff in jonm_site, then commit/push.")


if __name__ == "__main__":
    main()
