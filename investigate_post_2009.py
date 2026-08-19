import duckdb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import statsmodels.formula.api as smf
from datetime import datetime

import dataloader


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


def get_type_name(t):
    mapping = {1: "Book", 2: "Anime", 3: "Music", 4: "Game", 6: "Real"}
    return mapping.get(t, "Other")


def main():
    print("Loading Post-2009 data from DuckDB...")
    subjects = dataloader.load_subjects()
    current_year = datetime.now().year

    # Extract Data Strictly for >= 2009
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
          AND year(date) BETWEEN 2009 AND {current_year}
    """
    df = duckdb.sql(query).df()
    print(f"Loaded {len(df)} initial records (2009-{current_year}).")

    print("Calculating precise metrics...")
    metrics = df["score_details"].apply(compute_precise_metrics)
    df[["precise_score", "std_dev", "total_votes"]] = pd.DataFrame(
        metrics.tolist(), index=df.index
    )

    # Cast types and drop invalid/low-vote entries
    for col in ["precise_score", "std_dev", "total_votes"]:
        df[col] = df[col].astype(float)

    df = df.dropna(subset=["precise_score"]).copy()

    # Feature Engineering
    df["type_name"] = df["type"].apply(get_type_name)
    df["log_votes"] = np.log10(df["total_votes"])  # Log10 for linearizing popularity

    # Popularity Tiers for visualization
    df["popularity_tier"] = pd.qcut(
        df["total_votes"], q=4, labels=["Niche", "Moderate", "Popular", "Mainstream"]
    )

    print(f"Retained {len(df)} statistically valid records.\n")

    if df.empty:
        print("Dataframe is empty after filtering! Exiting.")
        return

    # ---------------------------------------------------------
    # 2. Multi-Dimensional Statistical Analysis (OLS Regression)
    # ---------------------------------------------------------
    print("=" * 60)
    print("MULTIVARIATE REGRESSION ANALYSIS (Post-2009)")
    print("=" * 60)
    print("Goal: Isolate the effect of Year, Popularity, and Category.\n")

    # Model 1: Predicting Score
    # Formula: Score depends on release year + log(votes) + type of subject
    score_model = smf.ols(
        "precise_score ~ release_year + log_votes + C(type_name)", data=df
    ).fit()
    print("--- MODEL 1: What drives HIGHER SCORES? ---")
    print(f"R-squared: {score_model.rsquared:.4f}")

    # Extract p-values and coefficients
    coefs = score_model.params
    pvals = score_model.pvalues

    # Effect of Year
    year_p = pvals["release_year"]
    year_c = coefs["release_year"]
    if year_p < 0.05:
        trend = "decreases" if year_c < 0 else "increases"
        print(
            f"-> Time Trend : Score {trend} by {abs(year_c):.4f} points every year (p={year_p:.4e})."
        )
    else:
        print("-> Time Trend : No significant change over time.")

    # Effect of Popularity
    pop_p = pvals["log_votes"]
    pop_c = coefs["log_votes"]
    if pop_p < 0.05:
        trend = "decreases" if pop_c < 0 else "increases"
        print(
            f"-> Popularity : Score {trend} by {abs(pop_c):.4f} points for every 10x increase in votes (p={pop_p:.4e})."
        )

    # Model 2: Predicting Polarity (Standard Deviation)
    print("\n--- MODEL 2: What drives POLARIZATION (Haters vs Fanboys)? ---")
    std_model = smf.ols(
        "std_dev ~ release_year + log_votes + C(type_name)", data=df
    ).fit()
    print(f"R-squared: {std_model.rsquared:.4f}")

    s_pop_p = std_model.pvalues["log_votes"]
    s_pop_c = std_model.params["log_votes"]
    if s_pop_p < 0.05:
        trend = "more" if s_pop_c > 0 else "less"
        print(
            f"-> Popularity : Subjects become {trend} polarized (StdDev changes by {s_pop_c:.4f}) as popularity 10x's (p={s_pop_p:.4e})."
        )

    # ---------------------------------------------------------
    # 3. Advanced Visualizations
    # ---------------------------------------------------------
    print("\nGenerating multi-dimensional visualizations...")
    sns.set_theme(style="whitegrid")
    fig = plt.figure(figsize=(20, 14))
    fig.suptitle(
        "Post-2009 Bangumi Analysis: Trends, Popularity, and Polarity",
        fontsize=22,
        fontweight="bold",
        y=0.98,
    )

    # Use GridSpec for a clean layout
    gs = fig.add_gridspec(2, 3)

    plot_df = df.sample(n=min(20000, len(df)), random_state=42)

    # Plot 1: Time Trend of Scores (Aggregated by Year)
    ax1 = fig.add_subplot(gs[0, 0:2])
    sns.lineplot(
        data=df,
        x="release_year",
        y="precise_score",
        hue="type_name",
        marker="o",
        ax=ax1,
        errorbar=("ci", 95),
    )
    ax1.set_title(
        "Year-over-Year Average Score by Subject Type (with 95% CI)", fontsize=14
    )
    ax1.set_xlabel("Release Year")
    ax1.set_ylabel("Mean Precise Score")
    ax1.set_xticks(range(2009, current_year + 1, 2))

    # Plot 2: Popularity vs Score (Hexbin density plot)
    ax2 = fig.add_subplot(gs[0, 2])
    hb = ax2.hexbin(
        plot_df["log_votes"],
        plot_df["precise_score"],
        gridsize=30,
        cmap="YlGnBu",
        mincnt=1,
    )
    cb = fig.colorbar(hb, ax=ax2)
    cb.set_label("Count in Bin")
    # Add trend line
    sns.regplot(
        data=plot_df,
        x="log_votes",
        y="precise_score",
        scatter=False,
        ax=ax2,
        color="red",
    )
    ax2.set_title("Does Popularity Boost Scores?", fontsize=14)
    ax2.set_xlabel("Log10(Total Votes)")
    ax2.set_ylabel("Precise Score")

    # Plot 3: Popularity vs Polarization
    ax3 = fig.add_subplot(gs[1, 0])
    sns.regplot(
        data=plot_df,
        x="log_votes",
        y="std_dev",
        ax=ax3,
        scatter_kws={"alpha": 0.2, "s": 10},
        line_kws={"color": "red"},
    )
    ax3.set_title("Polarization vs Popularity", fontsize=14)
    ax3.set_xlabel("Log10(Total Votes)")
    ax3.set_ylabel("Standard Deviation (Polarity)")

    # Plot 4: Score Distribution by Popularity Tiers
    ax4 = fig.add_subplot(gs[1, 1])
    sns.boxplot(
        data=df,
        x="popularity_tier",
        y="precise_score",
        ax=ax4,
        hue="popularity_tier",
        palette="coolwarm",
        legend=False,
    )
    ax4.set_title("Score Distribution Across Popularity Tiers", fontsize=14)
    ax4.set_xlabel("Popularity Tier")
    ax4.set_ylabel("Precise Score")

    # Plot 5: Polarization by Subject Type
    ax5 = fig.add_subplot(gs[1, 2])
    sns.violinplot(
        data=df,
        x="type_name",
        y="std_dev",
        ax=ax5,
        hue="type_name",
        palette="Set2",
        inner="quartile",
        legend=False,
    )
    ax5.set_title("Polarization (Std Dev) by Category", fontsize=14)
    ax5.set_xlabel("Subject Category")
    ax5.set_ylabel("Standard Deviation")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    output_filename = "results/bangumi_post_2009_multidimensional.png"
    plt.savefig(output_filename, dpi=300)
    print(f"\nVisualizations successfully saved to '{output_filename}'.")
    plt.show()


if __name__ == "__main__":
    main()
