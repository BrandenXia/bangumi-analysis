import duckdb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LogNorm
import itertools

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

    # Extract Data (Filtered for Anime type=2)
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
    print(f"Loaded {len(df)} initial Anime records.")

    print("Calculating precise metrics...")
    metrics = df["score_details"].apply(compute_precise_metrics)
    df[["precise_score", "std_dev", "total_votes"]] = pd.DataFrame(
        metrics.tolist(), index=df.index
    )

    for col in ["precise_score", "std_dev", "total_votes"]:
        df[col] = df[col].astype(float)
    df = df.dropna(subset=["precise_score"]).copy()

    # Clean tags: Ensure they are lists of uppercase strings, stripped of whitespace
    df["meta_tags"] = df["meta_tags"].apply(
        lambda x: (
            list(set([str(t).strip().upper() for t in x if str(t).strip()]))
            if isinstance(x, (list, np.ndarray))
            else []
        )
    )
    df = df[
        df["meta_tags"].map(len) > 1
    ]  # Only keep subjects with at least 2 tags (so we can form pairs)

    # ---------------------------------------------------------
    # 2. Tag Pair Extraction
    # ---------------------------------------------------------
    print(f"Analyzing {len(df)} Anime subjects with multiple tags for synergies...")

    # To prevent combinatoric explosion and noise, we only look at tags that appear at least 50 times overall
    all_tags = df["meta_tags"].explode()
    tag_counts = all_tags.value_counts()
    valid_tags = set(tag_counts[tag_counts >= 50].index)

    # Function to generate unique, alphabetically sorted pairs for each subject
    def get_tag_pairs(tags):
        valid_t = sorted([t for t in tags if t in valid_tags])
        return list(itertools.combinations(valid_t, 2))

    df["tag_pairs"] = df["meta_tags"].apply(get_tag_pairs)
    pairs_df = df.explode("tag_pairs").dropna(subset=["tag_pairs"])

    # Create string representation for plotting (e.g. "TV + ACTION")
    pairs_df["pair_name"] = pairs_df["tag_pairs"].apply(lambda x: f"{x[0]} + {x[1]}")

    # ---------------------------------------------------------
    # 3. Pair Aggregation & Statistical Analysis
    # ---------------------------------------------------------
    print("Aggregating statistics per tag combination...")
    pair_stats = (
        pairs_df.groupby("pair_name")
        .agg(
            subject_count=("id", "count"),
            avg_score=("precise_score", "mean"),
            avg_stdev=("std_dev", "mean"),
        )
        .reset_index()
    )

    # We only care about combinations that occur frequently enough to be statistically relevant
    MIN_CO_OCCURRENCE = 30
    pair_stats = pair_stats[pair_stats["subject_count"] >= MIN_CO_OCCURRENCE]

    if pair_stats.empty:
        print(
            f"No Tag pairs met the minimum co-occurrence threshold of {MIN_CO_OCCURRENCE}."
        )
        return

    print(
        f"Analyzed {len(pair_stats)} valid tag combinations (Filtered >= {MIN_CO_OCCURRENCE} subjects)."
    )

    # ---------------------------------------------------------
    # 4. Mutual Exclusivity (Co-occurrence Matrix)
    # ---------------------------------------------------------
    # We will build a matrix for the Top 15 most common tags to see what NEVER mixes
    top_15_tags = tag_counts.head(15).index.tolist()
    matrix_df = pd.DataFrame(index=top_15_tags, columns=top_15_tags, data=0)

    # Calculate actual pairwise counts for the heatmap
    for (t1, t2), count in pairs_df.groupby("tag_pairs").size().items():
        if t1 in top_15_tags and t2 in top_15_tags:
            matrix_df.at[t1, t2] = count
            matrix_df.at[t2, t1] = count

    # Diagonal represents the total occurrences of the tag itself
    for t in top_15_tags:
        matrix_df.at[t, t] = tag_counts[t]

    # ---------------------------------------------------------
    # 5. Visualizations
    # ---------------------------------------------------------
    print("\nGenerating Tag Synergy and Exclusivity visualizations...")
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
        "Anime Tag Interactions: Synergies, Penalties, and Mutual Exclusivity",
        fontsize=24,
        fontweight="600",
        y=0.98,
    )

    # PLOT 1: Mutual Exclusivity Heatmap (Top 15 Tags)
    ax1 = axes[0, 0]
    # We use LogNorm because the diagonal (total count) dwarfs the co-occurrences
    sns.heatmap(
        matrix_df,
        annot=True,
        fmt="d",
        cmap="YlOrRd",
        norm=LogNorm(vmin=1, vmax=matrix_df.max().max()),
        ax=ax1,
        cbar_kws={"label": "Co-occurrences (Log Scale)"},
    )
    ax1.set_title(
        "Co-occurrence Matrix of Top 15 Tags (Zero / Black = Mutually Exclusive)",
        fontsize=15,
    )
    ax1.tick_params(axis="x", rotation=45)
    ax1.tick_params(axis="y", rotation=0)

    # PLOT 2: Best Combinations (Synergy)
    ax2 = axes[0, 1]
    top_synergy = pair_stats.sort_values("avg_score", ascending=False).head(15)
    sns.barplot(
        data=top_synergy,
        x="avg_score",
        y="pair_name",
        hue="pair_name",
        palette="viridis",
        ax=ax2,
        legend=False,
    )
    ax2.set_title("Top 15 Highest Rated Tag Combinations (Synergy)", fontsize=15)
    ax2.set_xlabel("Average Precise Score")
    ax2.set_ylabel("Tag Combination")
    ax2.set_xlim(
        top_synergy["avg_score"].min() - 0.2, top_synergy["avg_score"].max() + 0.1
    )

    # PLOT 3: Worst Combinations (Penalty / Clashing)
    ax3 = axes[1, 0]
    worst_synergy = pair_stats.sort_values("avg_score", ascending=True).head(15)
    sns.barplot(
        data=worst_synergy,
        x="avg_score",
        y="pair_name",
        hue="pair_name",
        palette="flare",
        ax=ax3,
        legend=False,
    )
    ax3.set_title(
        "Top 15 Lowest Rated Tag Combinations (Penalties / Clashing)", fontsize=15
    )
    ax3.set_xlabel("Average Precise Score")
    ax3.set_ylabel("Tag Combination")
    ax3.set_xlim(
        worst_synergy["avg_score"].min() - 0.2, worst_synergy["avg_score"].max() + 0.1
    )

    # PLOT 4: Most Polarizing Combinations (Haters vs Fanboys)
    ax4 = axes[1, 1]
    top_polar = pair_stats.sort_values("avg_stdev", ascending=False).head(15)
    sns.barplot(
        data=top_polar,
        x="avg_stdev",
        y="pair_name",
        hue="pair_name",
        palette="magma",
        ax=ax4,
        legend=False,
    )
    ax4.set_title("Most Polarizing Tag Combinations (Highest Std Dev)", fontsize=15)
    ax4.set_xlabel("Average Standard Deviation")
    ax4.set_ylabel("Tag Combination")
    ax4.set_xlim(
        top_polar["avg_stdev"].min() - 0.05, top_polar["avg_stdev"].max() + 0.05
    )

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    output_filename = "results/anime_tag_synergy.png"
    plt.savefig(output_filename, dpi=300)
    print(f"\nVisualizations successfully saved to '{output_filename}'.")
    plt.show()


if __name__ == "__main__":
    main()
