import duckdb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

import dataloader

# ---------------------------------------------------------
# CJK Font Configuration for Matplotlib
# ---------------------------------------------------------
plt.rcParams["font.sans-serif"] = [
    "PingFang SC",  # macOS Chinese
    "Hiragino Sans GB",  # macOS Chinese fallback
    "Microsoft YaHei",  # Windows Chinese
    "SimHei",  # Windows Chinese fallback
    "Noto Sans CJK SC",  # Linux Chinese
    "WenQuanYi Micro Hei",  # Linux Chinese fallback
    "sans-serif",  # Global fallback
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
    # Threshold for statistical relevance
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

    # Extract Data (Including meta_tags, filtered for Anime type=2)
    query = """
        SELECT 
            id,
            name,
            score_details,
            meta_tags
        FROM subjects
        WHERE type = 2
          AND score_details IS NOT NULL
          AND meta_tags IS NOT NULL
    """
    df = duckdb.sql(query).df()
    print(f"Loaded {len(df)} initial Anime records with tags.")

    print("Calculating precise metrics...")
    metrics = df["score_details"].apply(compute_precise_metrics)
    df[["precise_score", "std_dev", "total_votes"]] = pd.DataFrame(
        metrics.tolist(), index=df.index
    )

    for col in ["precise_score", "std_dev", "total_votes"]:
        df[col] = df[col].astype(float)
    df = df.dropna(subset=["precise_score"]).copy()

    df["meta_tags"] = df["meta_tags"].apply(
        lambda x: x if isinstance(x, (list, np.ndarray)) and len(x) > 0 else np.nan
    )
    df = df.dropna(subset=["meta_tags"])

    print(f"Exploding {len(df)} valid Anime subjects into per-tag rows...")
    exploded_df = df.explode("meta_tags")

    exploded_df["meta_tags"] = (
        exploded_df["meta_tags"].astype(str).str.strip().str.upper()
    )
    exploded_df = exploded_df[exploded_df["meta_tags"] != ""]

    # ---------------------------------------------------------
    # 2. Tag Aggregation & Statistical Analysis
    # ---------------------------------------------------------
    print("Aggregating statistics per Anime meta tag...")
    tag_stats = (
        exploded_df.groupby("meta_tags")
        .agg(
            subject_count=("id", "count"),
            avg_score=("precise_score", "mean"),
            median_score=("precise_score", "median"),
            avg_stdev=("std_dev", "mean"),
            median_votes=("total_votes", "median"),
            total_votes_sum=("total_votes", "sum"),
        )
        .reset_index()
    )

    # Filter out rare tags to remove statistical noise
    # For Anime, 100 subjects is a good threshold for established formats like TV, OVA, Movie
    MIN_SUBJECTS_PER_TAG = 100
    tag_stats = tag_stats[tag_stats["subject_count"] >= MIN_SUBJECTS_PER_TAG]

    if tag_stats.empty:
        print(f"No Anime tags found with at least {MIN_SUBJECTS_PER_TAG} subjects.")
        return

    print(
        f"\nAnalyzed {len(tag_stats)} distinct Anime meta tags (Filtered >= {MIN_SUBJECTS_PER_TAG} subjects)."
    )

    # Console Reports
    print("\n--- TOP 10 HIGHEST RATED ANIME TAGS (By Average Score) ---")
    top_score = tag_stats.sort_values("avg_score", ascending=False).head(10)
    for _, row in top_score.iterrows():
        print(
            f"{row['meta_tags']:<20} | Score: {row['avg_score']:>5.2f} | Subjects: {row['subject_count']:>5.0f} | Median Votes: {row['median_votes']:>6.0f}"
        )

    print("\n--- TOP 10 MOST POLARIZED ANIME TAGS (By Average Standard Deviation) ---")
    top_polarized = tag_stats.sort_values("avg_stdev", ascending=False).head(10)
    for _, row in top_polarized.iterrows():
        print(
            f"{row['meta_tags']:<20} | StDev: {row['avg_stdev']:>5.2f} | Score: {row['avg_score']:>5.2f} | Subjects: {row['subject_count']:>5.0f}"
        )

    print("\n--- TOP 10 MOST POPULAR ANIME TAGS (By Median Votes per Subject) ---")
    top_popular = tag_stats.sort_values("median_votes", ascending=False).head(10)
    for _, row in top_popular.iterrows():
        print(
            f"{row['meta_tags']:<20} | Median Votes: {row['median_votes']:>6.0f} | Score: {row['avg_score']:>5.2f} | Subjects: {row['subject_count']:>5.0f}"
        )

    # ---------------------------------------------------------
    # 3. Visualizations
    # ---------------------------------------------------------
    print("\nGenerating Anime meta tag visualizations...")
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

    fig, axes = plt.subplots(2, 2, figsize=(20, 14))
    fig.suptitle(
        "Impact of Anime Meta Tags (Format/Type) on Subject Performance",
        fontsize=22,
        fontweight="600",
        y=0.98,
    )

    # Plot 1: Tag Ecosystem - Score vs Popularity
    ax1 = axes[0, 0]
    sns.scatterplot(
        data=tag_stats,
        x="median_votes",
        y="avg_score",
        size="subject_count",
        sizes=(20, 1000),
        alpha=0.6,
        color="#3498db",
        ax=ax1,
        legend=False,
    )
    ax1.set_xscale("log")
    ax1.set_title("Anime Meta Tag Ecosystem: Popularity vs Average Score", fontsize=15)
    ax1.set_xlabel("Median Votes per Subject (Log Scale)")
    ax1.set_ylabel("Average Precise Score")

    notable_tags = pd.concat([top_score, top_popular]).drop_duplicates()
    for _, row in notable_tags.iterrows():
        ax1.text(
            row["median_votes"],
            row["avg_score"] + 0.02,
            row["meta_tags"],
            fontsize=10,
            ha="center",
            va="bottom",
            color="black",
            alpha=0.8,
        )

    # Plot 2: Top 15 Highest Rated Anime Tags
    ax2 = axes[0, 1]
    top15_score = tag_stats.sort_values("avg_score", ascending=False).head(15)
    sns.barplot(
        data=top15_score,
        x="avg_score",
        y="meta_tags",
        hue="meta_tags",
        palette="viridis",
        ax=ax2,
        legend=False,
    )
    ax2.set_title("Top 15 Highest Rated Anime Tags", fontsize=15)
    ax2.set_xlabel("Average Precise Score")
    ax2.set_ylabel("Anime Meta Tag")
    ax2.set_xlim(
        top15_score["avg_score"].min() - 0.2, top15_score["avg_score"].max() + 0.1
    )

    # Plot 3: Top 15 Most Polarizing Anime Tags
    ax3 = axes[1, 0]
    top15_polar = tag_stats.sort_values("avg_stdev", ascending=False).head(15)
    sns.barplot(
        data=top15_polar,
        x="avg_stdev",
        y="meta_tags",
        hue="meta_tags",
        palette="magma",
        ax=ax3,
        legend=False,
    )
    ax3.set_title("Top 15 Most Polarizing Anime Tags (Highest Std Dev)", fontsize=15)
    ax3.set_xlabel("Average Standard Deviation")
    ax3.set_ylabel("Anime Meta Tag")
    ax3.set_xlim(
        top15_polar["avg_stdev"].min() - 0.05, top15_polar["avg_stdev"].max() + 0.05
    )

    # Plot 4: Top 15 Most Popular Anime Tags
    ax4 = axes[1, 1]
    top15_pop = tag_stats.sort_values("median_votes", ascending=False).head(15)
    sns.barplot(
        data=top15_pop,
        x="median_votes",
        y="meta_tags",
        hue="meta_tags",
        palette="crest",
        ax=ax4,
        legend=False,
    )
    ax4.set_title("Top 15 Most Popular Anime Tags (By Median Votes)", fontsize=15)
    ax4.set_xlabel("Median Votes per Subject")
    ax4.set_ylabel("Anime Meta Tag")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    output_filename = "results/anime_metatags_analysis.png"
    plt.savefig(output_filename, dpi=300)
    print(f"\nVisualizations successfully saved to '{output_filename}'.")
    plt.show()


if __name__ == "__main__":
    main()
