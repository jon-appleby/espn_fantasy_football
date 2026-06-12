from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns
from typing import Literal

CHART_FONTS = {
    "title": 12,
    "label": 9,
    "data_label": 9,
    "tick": 9,
    "legend": 9,
}

def set_chart_theme(
        style: Literal["white", "dark", "whitegrid", "darkgrid", "ticks"] = "darkgrid",
        palette=None
) -> None:
    """Set chart theme used across project visuals"""
    sns.set_theme(style=style, palette=palette)


def get_output_path(output_dir: str | Path, filename: str) -> Path:
    """Build output path and create folder if needed"""
    output_path = Path(output_dir) / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def save_chart(
        path: str | Path = None,
        fig=None,
        show: bool = True,
        close: bool = True,
        bbox_inches: str = 'tight'
) -> None:
    """
    Optionally save chart, show the chart, close the chart, and set layout.
    Args:
        path: path to save chart
        fig: matplotlib figure
        show: whether to show chart
        close: whether to close chart after showing
        bbox_inches: matplotlib savefig bbox setting
    """
    if fig is None:
        fig = plt.gcf()

    fig.tight_layout()

    if path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, bbox_inches=bbox_inches)

    if show:
        plt.show()

    if close:
        plt.close()