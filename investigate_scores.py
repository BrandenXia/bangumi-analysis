import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr, spearmanr, linregress
from datetime import datetime

import dataloader


def main():
    print("Loading subjects data...")
    # Load the DuckDB relation
    subjects = dataloader.load_subjects()

    current_year = datetime.now().year

    # Extract valid data
    # 1. We require valid dates and scores
    # 2. We filter out unranked/unrated items (rank IS NOT NULL, score > 0) to avoid noise from obscure/unrated entries
    # 3. We restrict the release year to a reasonable window (e.g., 1960 to current_year) to prevent extreme outliers
    query = f"""
        SELECT 
            year(date) AS release_year,
            score
        FROM subjects
        WHERE date IS NOT NULL 
          AND score IS NOT NULL 
          AND score > 0
          AND rank IS NOT NULL
          AND year(date) BETWEEN 1960 AND {current_year}
    """

    # DuckDB automatically finds the 'subjects' variable in the local scope
    df = duckdb.sql(query).df()

    if df.empty:
        print("No valid data found to analyze.")
        return

    print(f"Successfully loaded {len(df)} ranked subjects for analysis.\n")

    # Calculate 'age' (how many years old the subject is)
    df["age"] = current_year - df["release_year"]

    # ---------------------------------------------------------
    # 1. Statistical Analysis
    # ---------------------------------------------------------
    print("-" * 30)
    print("STATISTICAL ANALYSIS RESULTS")
    print("-" * 30)

    # Pearson Correlation (measures linear relationship)
    p_corr, p_val_p = pearsonr(df["age"], df["score"])
    print(f"Pearson Correlation  : {p_corr:.4f} (p-value: {p_val_p:.4e})")

    # Spearman Correlation (measures monotonic relationship, less sensitive to outliers)
    s_corr, p_val_s = spearmanr(df["age"], df["score"])
    print(f"Spearman Correlation : {s_corr:.4f} (p-value: {p_val_s:.4e})")

    # Linear Regression (quantifies the effect)
    slope, intercept, r_value, p_value_lin, std_err = linregress(df["age"], df["score"])
    print(f"Linear Regression    : Score = ({slope:.4f} * Age) + {intercept:.4f}")

    print("\n[Conclusion]")
    if p_value_lin < 0.05:
        if slope > 0:
            print("There is a statistically significant POSITIVE relationship.")
            print(
                f"Older subjects DO tend to get higher scores (approx +{slope:.4f} points per year of age)."
            )
        else:
            print("There is a statistically significant NEGATIVE relationship.")
            print(
                f"Older subjects DO NOT get higher scores. Newer subjects score higher (approx {slope:.4f} points per year of age)."
            )
    else:
        print(
            "There is no statistically significant relationship between age and score."
        )

    # ---------------------------------------------------------
    # 2. Visualization
    # ---------------------------------------------------------
    print("\nGenerating visualizations...")
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Plot A: Scatter Plot with Regression Line
    # If the dataset is huge, sample it for the scatter plot to prevent severe overplotting,
    # while the regression line is still calculated on the sampled data (or use the full dataframe logic).
    plot_df = df.sample(n=min(10000, len(df)), random_state=42)

    sns.regplot(
        data=plot_df,
        x="release_year",
        y="score",
        ax=axes[0],
        scatter_kws={"alpha": 0.15, "color": "#3498db"},
        line_kws={"color": "#e74c3c", "linewidth": 2},
    )
    axes[0].set_title("Subject Score vs. Release Year (with Trend Line)")
    axes[0].set_xlabel("Release Year")
    axes[0].set_ylabel("Score")
    axes[0].set_xlim(1960, current_year)

    # Plot B: Boxplot Grouped by Decade
    df["decade"] = (df["release_year"] // 10) * 10

    sns.boxplot(
        data=df,
        x="decade",
        y="score",
        ax=axes[1],
        hue="decade",
        palette="viridis",
        legend=False,
    )
    axes[1].set_title("Distribution of Scores by Decade")
    axes[1].set_xlabel("Decade")
    axes[1].set_ylabel("Score")

    # Final Layout Adjustments
    plt.suptitle(
        "Investigation: Do Older Subjects Tend to Get Higher Scores?",
        fontsize=16,
        fontweight="bold",
    )
    plt.tight_layout()

    # Save and show
    output_filename = "results/score_vs_age_analysis.png"
    plt.savefig(output_filename, dpi=300)
    print(f"Visualizations successfully saved to '{output_filename}'.")
    plt.show()


if __name__ == "__main__":
    main()
