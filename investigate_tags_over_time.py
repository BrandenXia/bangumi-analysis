import duckdb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

import dataloader

# ---------------------------------------------------------
# CJK Font Configuration for Matplotlib
# ---------------------------------------------------------
plt.rcParams["font.sans-serif"] = [
    "PingFang SC",
    "Hiragino Sans GB",
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "WenQuanYi Micro Hei",
    "sans-serif",
]
plt.rcParams["axes.unicode_minus"] = False


# ---------------------------------------------------------
# 1. Metric Calculation Helper (Robust Version)
# ---------------------------------------------------------
def compute_precise_metrics(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None, None, None

    keys, values = [], []
    if isinstance(val, dict):
        if (
            "key" in val
            and "value" in val
            and isinstance(val["key"], (list, np.ndarray))
        ):
            keys, values = val["key"], val["value"]
        else:
            keys, values = list(val.keys()), list(val.values())
    elif isinstance(val, list) and len(val) > 0:
        if isinstance(val[0], dict):
            keys, values = [x.get("key") for x in val], [x.get("value") for x in val]
        elif isinstance(val[0], (tuple, list)):
            keys, values = [x[0] for x in val], [x[1] for x in val]

    if not keys or not values or len(keys) != len(values):
        return None, None, None

    try:
        keys = [float(k) for k in keys]
        values = [int(v) for v in values]
    except (ValueError, TypeError):
        return None, None, None

    total_votes = sum(values)
    if total_votes < 50:
        return None, None, None

    precise_score = sum(k * v for k, v in zip(keys, values)) / total_votes
    variance = (
        sum(v * ((k - precise_score) ** 2) for k, v in zip(keys, values)) / total_votes
    )
    std_dev = variance**0.5

    return precise_score, std_dev, total_votes


def main():
    print("Loading ANIME data from DuckDB...")
    subjects = dataloader.load_subjects()

    # Analyze data from the year 2000 to current year
    current_year = datetime.now().year
    START_YEAR = 2000

    query = f"""
        SELECT 
            id,
            name,
            year(date) AS release_year,
            score_details,
            meta_tags
        FROM subjects
        WHERE type = 2
          AND score_details IS NOT NULL
          AND meta_tags IS NOT NULL
          AND year(date) BETWEEN {START_YEAR} AND {current_year}
    """
    df = duckdb.sql(query).df()
    print(f"Loaded {len(df)} initial Anime records ({START_YEAR}-{current_year}).")

    print("Calculating precise metrics...")
    metrics = df["score_details"].apply(compute_precise_metrics)
    df[["precise_score", "std_dev", "total_votes"]] = pd.DataFrame(
        metrics.tolist(), index=df.index
    )

    for col in ["precise_score", "std_dev", "total_votes"]:
        df[col] = df[col].astype(float)
    df = df.dropna(subset=["precise_score"]).copy()

    # Clean and explode tags
    df["meta_tags"] = df["meta_tags"].apply(
        lambda x: (
            [str(t).strip().upper() for t in x if str(t).strip()]
            if isinstance(x, (list, np.ndarray))
            else []
        )
    )
    exploded_df = df.explode("meta_tags")
    exploded_df = exploded_df[exploded_df["meta_tags"] != ""]

    # ---------------------------------------------------------
    # 2. Temporal Aggregation
    # ---------------------------------------------------------
    # Identify the top 8 most common tags to track over time
    top_tags = exploded_df["meta_tags"].value_counts().head(8).index.tolist()
    print(f"\nTracking Top 8 Tags over time: {', '.join(top_tags)}")

    # Filter dataset to only include the top tags
    temporal_df = exploded_df[exploded_df["meta_tags"].isin(top_tags)]

    # Group by Tag and Year
    yearly_stats = (
        temporal_df.groupby(["meta_tags", "release_year"])
        .agg(
            subject_count=("id", "count"),
            avg_score=("precise_score", "mean"),
            median_votes=("total_votes", "median"),
        )
        .reset_index()
    )

    # Create a Pivot Table for the Heatmap (Tag vs Year -> Avg Score)
    score_pivot = yearly_stats.pivot(
        index="meta_tags", columns="release_year", values="avg_score"
    )

    # ---------------------------------------------------------
    # 3. Visualizations
    # ---------------------------------------------------------
    print("\nGenerating temporal tag visualizations...")
    sns.set_theme(style="whitegrid")

    plt.rcParams["font.sans-serif"] = [
        "PingFang SC",
        "Hiragino Sans GB",
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "WenQuanYi Micro Hei",
        "sans-serif",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(2, 2, figsize=(22, 16))
    fig.suptitle(
        "Evolution of Top Anime Meta Tags Over Time (2000 - Present)",
        fontsize=24,
        fontweight="600",
        y=0.98,
    )

    palette = sns.color_palette("tab10", len(top_tags))

    # PLOT 1: Score Trends Over Time (Line Chart)
    ax1 = axes[0, 0]
    sns.lineplot(
        data=yearly_stats,
        x="release_year",
        y="avg_score",
        hue="meta_tags",
        marker="o",
        linewidth=2.5,
        palette=palette,
        ax=ax1,
    )
    ax1.set_title("Average Score Trends by Tag Over Time", fontsize=15)
    ax1.set_xlabel("Release Year")
    ax1.set_ylabel("Average Precise Score")
    ax1.set_xticks(range(START_YEAR, current_year + 1, 2))

    # PLOT 2: The Score Heatmap (Golden Eras)
    ax2 = axes[0, 1]
    sns.heatmap(
        score_pivot, cmap="YlGnBu", annot=False, ax=ax2, cbar_kws={"label": "Avg Score"}
    )
    ax2.set_title('Score Heatmap: Identifying "Golden Eras" for Tags', fontsize=15)
    ax2.set_xlabel("Release Year")
    ax2.set_ylabel("Meta Tag")

    # PLOT 3: Subject Volume Over Time (Are certain formats dying/rising?)
    ax3 = axes[1, 0]
    sns.lineplot(
        data=yearly_stats,
        x="release_year",
        y="subject_count",
        hue="meta_tags",
        marker="s",
        linewidth=2.5,
        palette=palette,
        ax=ax3,
    )
    ax3.set_title(
        "Production Volume: Number of Subjects Released per Year", fontsize=15
    )
    ax3.set_xlabel("Release Year")
    ax3.set_ylabel("Number of Rated Subjects")
    ax3.set_xticks(range(START_YEAR, current_year + 1, 2))

    # PLOT 4: Popularity Shifts (Median Votes per Year)
    ax4 = axes[1, 1]
    sns.lineplot(
        data=yearly_stats,
        x="release_year",
        y="median_votes",
        hue="meta_tags",
        marker="^",
        linewidth=2.5,
        palette=palette,
        ax=ax4,
    )
    ax4.set_yscale("log")
    ax4.set_title(
        "Popularity Trends: Median Votes per Subject (Log Scale)", fontsize=15
    )
    ax4.set_xlabel("Release Year")
    ax4.set_ylabel("Median Votes")
    ax4.set_xticks(range(START_YEAR, current_year + 1, 2))

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    output_filename = "results/anime_tags_over_time.png"
    plt.savefig(output_filename, dpi=300)
    print(f"\nVisualizations successfully saved to '{output_filename}'.")
    plt.show()


if __name__ == "__main__":
    main()
