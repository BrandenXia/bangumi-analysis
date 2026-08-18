import duckdb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from datetime import datetime

import dataloader


# ---------------------------------------------------------
# 1. Metric Calculation Helper
# ---------------------------------------------------------
def compute_precise_metrics(val):
    """
    Universally parses the DuckDB map object to calculate precise score,
    standard deviation, and total votes, regardless of how DuckDB/PyArrow serializes it.
    """
    # 1. Handle Nones and NaNs gracefully
    if val is None:
        return None, None, None
    if isinstance(val, float) and np.isnan(val):
        return None, None, None

    keys = []
    values = []

    # 2. Extract keys and values depending on serialization format
    if isinstance(val, dict):
        if (
            "key" in val
            and "value" in val
            and isinstance(val["key"], (list, np.ndarray))
        ):
            # Format: {'key': [1,2,3], 'value': [10,20,30]}
            keys = val["key"]
            values = val["value"]
        else:
            # Format: {1: 10, 2: 20, 3: 30}
            keys = list(val.keys())
            values = list(val.values())
    elif isinstance(val, list) and len(val) > 0:
        if isinstance(val[0], dict):
            # Format: [{'key': 1, 'value': 10}, ...]
            keys = [x.get("key") for x in val]
            values = [x.get("value") for x in val]
        elif isinstance(val[0], (tuple, list)):
            # Format: [(1,10), (2,20)]
            keys = [x[0] for x in val]
            values = [x[1] for x in val]

    # If we couldn't parse it or it's empty
    if not keys or not values or len(keys) != len(values):
        return None, None, None

    # 3. Ensure they are numbers (skip broken records)
    try:
        keys = [float(k) for k in keys]
        values = [int(v) for v in values]
    except (ValueError, TypeError):
        return None, None, None

    # 4. Statistical minimum threshold: Subjects with < 50 votes are too noisy
    total_votes = sum(values)
    if total_votes < 50:
        return None, None, None

    # 5. Calculate Precise Score (Weighted Average)
    sum_score = sum(k * v for k, v in zip(keys, values))
    precise_score = sum_score / total_votes

    # 6. Calculate Standard Deviation (Measures consensus vs. polarization/review bombing)
    variance = (
        sum(v * ((k - precise_score) ** 2) for k, v in zip(keys, values)) / total_votes
    )
    std_dev = variance**0.5

    return precise_score, std_dev, total_votes


def main():
    print("Loading data from DuckDB...")
    subjects = dataloader.load_subjects()
    current_year = datetime.now().year

    # Extract required raw columns
    query = f"""
        SELECT 
            id,
            name,
            type,
            year(date) AS release_year,
            score_details
        FROM subjects
        WHERE date IS NOT NULL 
          AND score_details IS NOT NULL
          AND year(date) BETWEEN 1970 AND {current_year}
    """
    df = duckdb.sql(query).df()
    print(f"Loaded {len(df)} initial records with valid dates (1970-{current_year}).")

    if len(df) > 0:
        sample_detail = df["score_details"].dropna().iloc[0]
        print(f"Debug: DuckDB mapped 'score_details' as: {type(sample_detail)}")

    print(
        "Calculating high-precision metrics (Score, Standard Deviation, Total Votes)..."
    )

    # Apply precise calculation
    metrics = df["score_details"].apply(compute_precise_metrics)
    df[["precise_score", "std_dev", "total_votes"]] = pd.DataFrame(
        metrics.tolist(), index=df.index
    )

    # EXPLICITLY CAST TO FLOAT (Fixes SciPy TypeError)
    df["precise_score"] = df["precise_score"].astype(float)
    df["std_dev"] = df["std_dev"].astype(float)
    df["total_votes"] = df["total_votes"].astype(float)

    # Drop subjects that didn't meet the vote threshold or had invalid data
    df = df.dropna(subset=["precise_score"]).copy()
    print(
        f"Retained {len(df)} records after applying minimum vote threshold (>= 50 votes).\n"
    )

    if df.empty:
        print("Dataframe is empty after filtering! Exiting script to prevent crash.")
        return

    # Feature Engineering
    df["age"] = current_year - df["release_year"]
    df["era"] = np.where(
        df["release_year"] < 2009,
        "Pre-2009 (Retroactive/Nostalgia)",
        "Post-2009 (Contemporary)",
    )

    # ---------------------------------------------------------
    # 2. Advanced Statistical Analysis
    # ---------------------------------------------------------
    print("=" * 50)
    print("STATISTICAL ANALYSIS RESULTS")
    print("=" * 50)

    pre_2009 = df[df["release_year"] < 2009]
    post_2009 = df[df["release_year"] >= 2009]

    print(
        f"Pre-2009 Subjects:  {len(pre_2009):,} (Mean Score: {pre_2009['precise_score'].mean():.3f}, Mean StdDev: {pre_2009['std_dev'].mean():.3f})"
    )
    print(
        f"Post-2009 Subjects: {len(post_2009):,} (Mean Score: {post_2009['precise_score'].mean():.3f}, Mean StdDev: {post_2009['std_dev'].mean():.3f})"
    )

    if len(pre_2009) > 0 and len(post_2009) > 0:
        # T-Test: Are pre-2009 scores significantly different from post-2009 scores?
        t_stat, p_val = stats.ttest_ind(
            pre_2009["precise_score"],
            post_2009["precise_score"],
            equal_var=False,
            nan_policy="omit",
        )
        print(f"\nT-Test (Pre vs Post 2009 Scores): p-value = {p_val:.4e}")
        if p_val < 0.05:
            print(
                ">> STATISTICAL CONCLUSION: There is a significant difference between Pre-2009 and Post-2009 scores."
            )
            print(
                ">> This strongly suggests 'Survivorship Bias' / Nostalgia: Older, poorly-rated shows are forgotten, heavily inflating the average scores of older items."
            )

    if len(post_2009) > 0:
        # Correlation Analysis inside the Post-2009 era (to remove retroactive bias)
        print("\n--- Post-2009 Only (Contemporary Voting Analysis) ---")
        corr, p = stats.spearmanr(post_2009["age"], post_2009["precise_score"])
        print(f"Spearman Correlation (Age vs Score): {corr:.4f} (p={p:.4e})")

        corr_std, p_std = stats.spearmanr(post_2009["age"], post_2009["std_dev"])
        print(f"Spearman Correlation (Age vs Std Dev): {corr_std:.4f} (p={p_std:.4e})")

    # ---------------------------------------------------------
    # 3. Comprehensive Visualizations
    # ---------------------------------------------------------
    print("\nGenerating comprehensive multi-plot visualization...")
    sns.set_theme(style="whitegrid")

    fig, axes = plt.subplots(3, 2, figsize=(18, 18))
    fig.suptitle(
        "Bangumi Rating Analysis: Age, Survivorship Bias, and Polarization",
        fontsize=20,
        fontweight="bold",
        y=0.98,
    )

    # Sample data for scatter plots
    plot_df = df.sample(n=min(15000, len(df)), random_state=42)

    palette_colors = {
        "Pre-2009 (Retroactive/Nostalgia)": "#e74c3c",
        "Post-2009 (Contemporary)": "#3498db",
    }

    # Plot 1: Score vs Release Year
    sns.scatterplot(
        data=plot_df,
        x="release_year",
        y="precise_score",
        hue="era",
        alpha=0.3,
        s=15,
        ax=axes[0, 0],
        palette=palette_colors,
    )
    axes[0, 0].axvline(
        x=2009, color="k", linestyle="--", linewidth=2, label="Bangumi Created (2009)"
    )
    axes[0, 0].set_title("Precise Score vs Release Year")
    axes[0, 0].set_xlabel("Release Year")
    axes[0, 0].set_ylabel("Precise Score")
    axes[0, 0].legend()

    # Plot 2: Boxplot comparing Eras
    sns.violinplot(
        data=df,
        x="era",
        y="precise_score",
        ax=axes[0, 1],
        hue="era",
        palette=palette_colors,
        inner="quartile",
        legend=False,
    )
    axes[0, 1].set_title("Score Distribution Shift (Survivorship Bias)")
    axes[0, 1].set_xlabel("Era")
    axes[0, 1].set_ylabel("Precise Score")

    # Plot 3: Standard Deviation vs Release Year
    sns.scatterplot(
        data=plot_df,
        x="release_year",
        y="std_dev",
        hue="era",
        alpha=0.3,
        s=15,
        ax=axes[1, 0],
        palette=palette_colors,
        legend=False,
    )
    axes[1, 0].axvline(x=2009, color="k", linestyle="--")
    axes[1, 0].set_title("Rating Polarization (Std Dev) vs Release Year")
    axes[1, 0].set_xlabel("Release Year")
    axes[1, 0].set_ylabel("Standard Deviation (Higher = Divisive)")

    # Plot 4: Total Votes vs Release Year
    sns.scatterplot(
        data=plot_df,
        x="release_year",
        y="total_votes",
        hue="era",
        alpha=0.3,
        s=15,
        ax=axes[1, 1],
        palette=palette_colors,
        legend=False,
    )
    axes[1, 1].set_yscale("log")
    axes[1, 1].axvline(x=2009, color="k", linestyle="--")
    axes[1, 1].set_title("Total Votes vs Release Year (Log Scale)")
    axes[1, 1].set_xlabel("Release Year")
    axes[1, 1].set_ylabel("Total Votes (Log Scale)")

    # Plot 5: Polarization Curve
    sns.scatterplot(
        data=plot_df,
        x="precise_score",
        y="std_dev",
        hue="era",
        alpha=0.4,
        s=20,
        ax=axes[2, 0],
        palette=palette_colors,
        legend=False,
    )
    axes[2, 0].set_title("The Consensus Curve: Score vs Polarization")
    axes[2, 0].set_xlabel("Precise Score")
    axes[2, 0].set_ylabel("Standard Deviation")

    # Plot 6: Votes vs Precise Score
    sns.scatterplot(
        data=plot_df,
        x="precise_score",
        y="total_votes",
        hue="era",
        alpha=0.4,
        s=20,
        ax=axes[2, 1],
        palette=palette_colors,
        legend=False,
    )
    axes[2, 1].set_yscale("log")
    axes[2, 1].set_title("Popularity (Total Votes) vs Score")
    axes[2, 1].set_xlabel("Precise Score")
    axes[2, 1].set_ylabel("Total Votes (Log Scale)")

    plt.tight_layout()
    output_filename = "results/advanced_score_analysis.png"
    plt.savefig(output_filename, dpi=300)
    print(f"\nVisualizations successfully saved to '{output_filename}'.")
    plt.show()


if __name__ == "__main__":
    main()
