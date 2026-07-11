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
END_YEAR = date.today().year
PAUSE_SECONDS = 1.0


def main():
    # matchup_data, finish_data = fetch_historical_matchup_data(
    #     start_year=START_YEAR,
    #     end_year=END_YEAR,
    #     pause_seconds=PAUSE_SECONDS,
    # )
    #
    # if matchup_data.empty:
    #     print('No completed yearly matchup data found.')
    #     return
    #
    # OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    #
    # all_time_summary = create_all_time_summary(matchup_data, finish_data)
    # head_to_head = create_head_to_head_records(matchup_data)
    # projected_actual_weekly = fetch_projected_actual_data(matchup_data, pause_seconds=PAUSE_SECONDS)
    # projected_actual_summary = summarize_projected_vs_actual(projected_actual_weekly)
    #
    # matchup_data.to_csv(OUTPUT_DIR / f'yearly_matchup_data_{START_YEAR}-{END_YEAR}.csv', index=False)
    # finish_data.to_csv(OUTPUT_DIR / f'yearly_finish_data_{START_YEAR}-{END_YEAR}.csv', index=False)
    # all_time_summary.to_csv(OUTPUT_DIR / f'all_time_summary_{START_YEAR}-{END_YEAR}.csv', index=False)
    # head_to_head.to_csv(OUTPUT_DIR / f'all_time_head_to_head_{START_YEAR}-{END_YEAR}.csv', index=False)
    # projected_actual_weekly.to_csv(
    #     OUTPUT_DIR / f'all_time_projected_vs_actual_weekly_{START_YEAR}-{END_YEAR}.csv',
    #     index=False,
    # )
    # projected_actual_summary.to_csv(
    #     OUTPUT_DIR / f'all_time_projected_vs_actual_summary_{START_YEAR}-{END_YEAR}.csv',
    #     index=False,
    # )

    all_time_summary = pd.read_csv(OUTPUT_DIR / f'all_time_summary_{START_YEAR}-{END_YEAR}.csv')
    head_to_head = pd.read_csv(OUTPUT_DIR / f'all_time_head_to_head_{START_YEAR}-{END_YEAR}.csv')
    projected_actual_summary = pd.read_csv(OUTPUT_DIR / f'all_time_projected_vs_actual_summary_{START_YEAR}-{END_YEAR}.csv')

    print_and_save_yearly_charts(
        summary=all_time_summary,
        head_to_head=head_to_head,
        projected_actual=projected_actual_summary,
        output_dir=OUTPUT_DIR,
        start_year=START_YEAR,
        end_year=END_YEAR,
    )


if __name__ == '__main__':
    main()
