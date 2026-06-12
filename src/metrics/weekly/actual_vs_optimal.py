import os
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv
from matplotlib.lines import Line2D

from espn.constants import SLOT_CODES
from metrics.weekly.chart_utils import save_chart, set_chart_theme

load_dotenv()
SWID = os.getenv("SWID")
ESPN_S2 = os.getenv("ESPN_S2")
LEAGUE_ID = os.getenv("LEAGUE_ID")


def create_team_slates(data, week_num) -> dict[Any, Any]:
    """
    Constructs week team slates with slotted position,
    position, and points (actual and ESPN projected),
    given full matchup info (`get_matchups`)
    Args:
        data: `dict` of `DataFrames`
        week_num: `int`
    Return:
        dict containing team id: dataframe with slot (position, bench, or ir)
    """

    slates = {}

    for team in data['teams']:
        slate = []
        for p in team['roster']['entries']:
            # get name
            name = p['playerPoolEntry']['player']['fullName']

            # get actual lineup slot
            slotid = p['lineupSlotId']
            slot = SLOT_CODES[slotid]

            # get projected and actual scores
            act, proj = 0, 0
            for stat in p['playerPoolEntry']['player']['stats']:
                if stat['scoringPeriodId'] != week_num:
                    continue
                if stat['statSourceId'] == 0:
                    act = stat['appliedTotal']
                elif stat['statSourceId'] == 1:
                    proj = stat['appliedTotal']
                else:
                    print('Error')

            # get type of player
            pos = 'Unk'
            ess = p['playerPoolEntry']['player']['eligibleSlots']
            if 0 in ess:
                pos = 'QB'
            elif 2 in ess:
                pos = 'RB'
            elif 4 in ess:
                pos = 'WR'
            elif 6 in ess:
                pos = 'TE'
            elif 16 in ess:
                pos = 'D/ST'
            elif 17 in ess:
                pos = 'K'

            slate.append([name, slotid, slot, pos, act, proj])
        slate = pd.DataFrame(slate, columns=['Name', 'SlotID', 'Slot', 'Pos', 'Actual', 'Proj'])
        slates[team['id']] = slate
    return slates


def calculate_lineup_points(slates, posns, struc):
    """
    Given slates (`get_slates`), compute total roster pts:
    actual, optimal, and using ESPN projections

    Parameters
    --------------
    slates : `dict` of `DataFrames`
        (from `get_slates`)
    posns : `list`
        roster positions, e.g. ['QB','RB', 'WR', 'TE']
    struc : `list`
        slots per position, e.g. [1,2,2,1]

    * This is not flexible enough to handle "weird" leagues
    like 6 Flex slots with constraints on # total RB/WR

    Returns
    --------------
    `dict` of `dict`s with actual, ESPN, optimal points
    """

    data = {}
    for tmid, slate in slates.items():
        # Set dict and assign actual starters
        pts = {
            'opts': 0,
            'epts': 0,
            'apts': slate.loc[~slate['Slot'].isin(['Bench', 'IR']),'Actual',].sum()}

        # optimal and espn-proj starters
        for method, cat in [('Actual', 'opts'), ('Proj', 'epts')]:
            actflex = -100  # actual pts scored by flex
            proflex = -100  # "proj" pts scored by flex
            for pos, num in zip(posns, struc, strict=False):
                # actual points, sorted by either actual or proj outcome
                t = (
                    slate.loc[slate['Pos'] == pos]
                    .sort_values(by=method, ascending=False)['Actual']
                    .to_numpy()
                )

                # projected points, sorted by either actual or proj outcome
                t2 = (
                    slate.loc[slate['Pos'] == pos]
                    .sort_values(by=method, ascending=False)['Proj']
                    .to_numpy()
                )

                # sum up points
                pts[cat] += t[:num].sum()

                # set the next best as flex
                if pos in ['RB', 'WR', 'TE'] and len(t) > num:
                    fn = t[num] if method == 'Actual' else t2[num]
                    if fn > proflex:
                        actflex = t[num]
                        proflex = fn

            pts[cat] += actflex

        data[tmid] = pts

    return data


def create_lineup_efficiency(data, team):
    """
    get data and teams, merge and prepare data for use later
    """
    point_df = pd.DataFrame(data).transpose()
    point_df['TeamID'] = range(1, 1 + len(point_df))
    point_df = point_df.merge(team[['id', 'team_name']], left_on='TeamID', right_on='id', how='left')
    point_df = point_df.rename(columns={'opts': 'optimal_pts',
                                        'apts': 'actual_pts',
                                        'epts': 'espn_proj',
                                        'TeamID': 'team_id'}).drop(columns='id')
    point_df['missed_pts'] = round(point_df['optimal_pts'] - point_df['actual_pts'], 2)
    point_df['efficiency'] = (round(point_df['actual_pts'] / point_df['optimal_pts'], 3) * 100)

    return point_df


def get_matchup_team_order(weekly_data, week: int, winner_first: bool = True) -> list[str]:
    """
    Create y-axis team order grouped by weekly matchup
    """

    df = weekly_data.loc[weekly_data["matchup_period"] == week].copy()

    # one shared key per matchup, regardless of team/opponent direction
    df["matchup_key"] = df.apply(
        lambda row: tuple(sorted([row["team_id"], row["opp_id"]])),
        axis=1,
    )

    # order matchups by highest score in each matchup
    matchup_order = (
        df.groupby("matchup_key")["team_points"]
        .max()
        .reset_index(name="winner_points")
        .sort_values("winner_points", ascending=False)
    )

    team_order = []

    for matchup_key in matchup_order["matchup_key"]:
        matchup = df.loc[df["matchup_key"] == matchup_key].copy()

        if winner_first:
            matchup = matchup.sort_values("team_points", ascending=False)

        team_order.extend(matchup["team_name"].to_list())

    return team_order


def chart_actual_vs_optimal(data_input, curr_week=1, team_order=None, path=None):
    set_chart_theme(style="white")

    data = data_input.copy()

    actual_pt_color = "teal"
    optimal_pt_color = "gray"
    espn_proj_color = "purple"
    matchup_band_color = "#f0f0f0"

    if team_order is None:
        data = data.sort_values(by="actual_pts", ascending=False)
        team_order = data["team_name"].to_list()
        y_map = {team: idx for idx, team in enumerate(team_order)}
    else:
        data["team_name"] = pd.Categorical(
            data["team_name"],
            categories=team_order,
            ordered=True,
        )
        data = data.sort_values("team_name")

        # add a gap after every pair
        y_map = {
            team: idx + (idx // 2)
            for idx, team in enumerate(team_order)
        }

    data["plot_y"] = data["team_name"].astype(str).map(y_map)

    fig, ax = plt.subplots(figsize=(11, 8))

    #----------------------#
    # shaded matchup bands #
    #----------------------#
    for i in range(0, len(team_order), 2):
        pair = team_order[i:i + 2]
        pair_y = [y_map[t] for t in pair if t in y_map]

        if pair_y:
            ax.axhspan(
                min(pair_y) - 0.5,
                max(pair_y) + 0.5,
                facecolor=matchup_band_color,
                zorder=0
            )

    # x-grid only
    ax.grid(axis="x", color="#d9d9d9", linewidth=0.8)
    ax.grid(axis="y", visible=False)

    # dumbbell lines
    ax.hlines(
        y=data["plot_y"],
        xmin=data["actual_pts"],
        xmax=data["optimal_pts"],
        color=optimal_pt_color,
        linewidth=3.5,
        zorder=2
    )

    # optimal marker
    ax.scatter(
        data["optimal_pts"],
        data["plot_y"],
        color=optimal_pt_color,
        marker="|",
        s=160,
        zorder=3
    )

    # actual marker
    ax.scatter(
        data["actual_pts"],
        data["plot_y"],
        color=actual_pt_color,
        marker="o",
        s=120,
        zorder=4
    )

    # ESPN projection marker
    ax.scatter(
        data["espn_proj"],
        data["plot_y"],
        color=espn_proj_color,
        marker="|",
        s=90,
        zorder=3
    )

    # value labels
    for _, row in data.iterrows():
        ax.annotate(
            f'{row["actual_pts"]:.2f}',
            xy=(row["actual_pts"], row["plot_y"]),
            xytext=(-8, 0),
            textcoords="offset points",
            color=actual_pt_color,
            fontsize=8,
            ha="right",
            va="center",
        )

        ax.annotate(
            f'{row["optimal_pts"]:.2f}',
            xy=(row["optimal_pts"], row["plot_y"]),
            xytext=(6, 0),
            textcoords="offset points",
            color=optimal_pt_color,
            fontsize=8,
            ha="left",
            va="center",
        )

    # y-axis labels
    ax.set_yticks([y_map[team] for team in team_order])
    ax.set_yticklabels(team_order)

    x_min = data[["actual_pts", "optimal_pts", "espn_proj"]].min().min() - 10
    x_max = data[["actual_pts", "optimal_pts", "espn_proj"]].max().max() + 10
    ax.set_xlim(x_min, x_max)

    ax.set_xlabel("Points", fontsize=9)
    ax.set_ylabel("")
    ax.set_title(f"Actual vs Optimal Points by Matchup - Week {curr_week}", fontsize=11)

    # clean spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.tick_params(axis="x", labelsize=9, colors="#555555")
    ax.tick_params(axis="y", labelsize=9, colors="#555555", length=0)

    # first item on top
    ax.invert_yaxis()

    # custom legend
    legend_handles = [
        Line2D([0], [0], color=optimal_pt_color, lw=3, label="Actual to optimal range"),
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor=actual_pt_color, markeredgecolor=actual_pt_color,
               markersize=10, label="Actual points"),
        Line2D([0], [0], marker="|", color=optimal_pt_color,
               linestyle="None", markersize=12, label="Optimal points"),
        Line2D([0], [0], marker="|", color=espn_proj_color,
               linestyle="None", markersize=10, label="ESPN projection"),
    ]
    # ax.legend(handles=legend_handles, loc="upper left", frameon=True)

    ax.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.00),
        ncol=4,
        frameon=False,
        columnspacing=1.4,
        handletextpad=0.6,
        fontsize=9
    )

    if path is None:
        path = f"../outputs/10-week{curr_week}_actual_vs_optimal.png"

    save_chart(path, fig=fig)
