# ESPN Fantasy Football Metrics

A personal analytics project that pulls raw ESPN Fantasy Football data from the public ESPN 
API into analysis ready data, and generates weekly performance metrics and visualizations.

This project includes Python analytics including API extraction, nested JSON parsing, data 
cleansing, metric design, and reproducible scripts.

## Overview
Fantasy football data is a useful analytics sandbox because it combines structured data, 
time-series performance, ranking logic, edge cases, and subjective business rules.

The project analyzes league performance across several dimensions:

* **Weekly scoring trends:** team scores, league averages, opponent points, and week-over-week 
performance.
* **Actual vs optimal efficiency:** compares submitted lineups against best possible decisions.
* **All-play performance:** estimates how each team performs against every other team.
* **Power rankings:** creates custom ranking using scoring consistency, win percentage, and 
year-to-date performance.
* **Draft position vs rank:** compares preseason draft order against final standings.
* **Injury impact analysis:** joins ESPN roster data with NFL injury reports to estimate 
weekly roster disruption.

The approach here uses similar techniques to professional BI and analytics work:
* API data extraction
* Data normalization from nested JSON
* Metric definition and documentation
* Repeatable reporting workflows
* Data quality checks and exception handling
* Visual storytelling with charts

## Setup & Execution
This project requires ESPN authentication for private fantasy leagues. These values should be 
stored locally in a .env file, or set as Windows enrivonment variables.

To find your cookie values, log in to ESPN Fantasy Football in your browser and open
the browser tools. In Firefox, go to the Storage tab and look for cookies named **espn_s2** 
and **SWID**.

To find your league ID, open your ESPN Fantasy league homepage and check the page URL. Look
for a parameter similar to "leagueId=999999". Use the numeric value as ESPN_LEAGUE_ID.

| Variable       | Description            | Example                             |
|----------------|------------------------|-------------------------------------|
| ESPN_LEAGUE_ID | ESPN fantasy league ID | 543987                              |
| ESPN_SWID      | ESPN SWID cookie       | {123A51D-89AB-1234-Z987-1234GH5132} |
| ESPN_S2        | ESPN_S2 cookie         | 'BAVKFxw89230f ... sSKMFasld29Sd'   |


### Running Weekly Report
This creates weekly datasets and chart outputs in the outputs/ folder

`python scripts/run_weekly.py --season 2025 --week 17 --output-dir outputs`

#### Example Metrics
| Metric            | Description                                                          |
|-------------------|----------------------------------------------------------------------|
| Actual points     | Points scored by the submitted starting lineup                       |
| Optimal points    | Maximum points available from the roster using eligible starts       |
| Missed points     | Difference between optimal and actual points                         |
| Lineup efficiency | Actual points divided by optimal points                              |
| All-play ratio    | Percentage of possible weekly head-to-head matchups won              |
| Power rank        | Custom score based on average points, high score, and win percentage |

## Limitations
* ESPN does not provide documentation for the public API, so response structure may change.
* Private leagues require valid ESPN cookies.
* Injury analysis is approximate because historical injury status and player availability can be 
incomplete and inconsistent.
* Optimal lineup logic assumes a standard roster structure and may need adjustment for 
unusual league rules.