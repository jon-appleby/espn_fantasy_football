from datetime import date
from pathlib import Path

import pandas as pd

from metrics.yearly.yearly_metrics import (
    create_all_time_summary,
    create_head_to_head_records,
    fetch_historical_matchup_data,
    fetch_projected_actual_data,
    print_and_save_yearly_charts,
    summarize_projected_vs_actual,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'yearly'

START_YEAR = 2018
REQUEST_THROUGH_YEAR = date.today().year  # upper bound to check; incomplete seasons are filtered out automatically
PAUSE_SECONDS = 1.0


def main():
    matchup_data, finish_data = fetch_historical_matchup_data(
        start_year=START_YEAR,
        end_year=REQUEST_THROUGH_YEAR,
        pause_seconds=PAUSE_SECONDS,
    )

    if matchup_data.empty:
        print('No completed yearly matchup data found.')
        return

    # Label output using the last season that actually finished - not
    # today's calendar year - so an upcoming/in-progress season never gets
    # included (e.g. running this in July 2026, before the 2026 season starts,
    # still correctly produces "...-2025" output).
    end_year = int(matchup_data['year'].max())
    if end_year != REQUEST_THROUGH_YEAR:
        print(f'{REQUEST_THROUGH_YEAR} season not complete yet - labeling output through {end_year}.')

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_time_summary = create_all_time_summary(matchup_data, finish_data)
    head_to_head = create_head_to_head_records(matchup_data)
    projected_actual_weekly = fetch_projected_actual_data(matchup_data, pause_seconds=PAUSE_SECONDS)
    projected_actual_summary = summarize_projected_vs_actual(projected_actual_weekly)

    matchup_data.to_csv(OUTPUT_DIR / f'yearly_matchup_data_{START_YEAR}-{end_year}.csv', index=False)
    finish_data.to_csv(OUTPUT_DIR / f'yearly_finish_data_{START_YEAR}-{end_year}.csv', index=False)
    all_time_summary.to_csv(OUTPUT_DIR / f'all_time_summary_{START_YEAR}-{end_year}.csv', index=False)
    head_to_head.to_csv(OUTPUT_DIR / f'all_time_head_to_head_{START_YEAR}-{end_year}.csv', index=False)
    projected_actual_weekly.to_csv(
        OUTPUT_DIR / f'all_time_projected_vs_actual_weekly_{START_YEAR}-{end_year}.csv',
        index=False,
    )
    projected_actual_summary.to_csv(
        OUTPUT_DIR / f'all_time_projected_vs_actual_summary_{START_YEAR}-{end_year}.csv',
        index=False,
    )

    print_and_save_yearly_charts(
        summary=all_time_summary,
        head_to_head=head_to_head,
        projected_actual=projected_actual_summary,
        output_dir=OUTPUT_DIR,
        start_year=START_YEAR,
        end_year=end_year,
    )


if __name__ == '__main__':
    main()
