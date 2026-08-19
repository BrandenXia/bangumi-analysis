# bangumi-analysis

Some analysis based on [Bangumi](https://bgm.tv) [public data](https://github.com/bangumi/Archive).

## Usage

1. Run `./fetch-data` to fetch the latest data from Bangumi. The data will be
   stored in the `data` directory.
2. [`dataloader.py`](./dataloader.py) provides an interface to load data efficiently.
3. All the analysis scripts are at the root directory. They are:
   - [`investigate_scores.py`](./investigate_scores.py) for investigating whether
     the scores are influenced by the age of the subjects.
     (Written by Gemini 3.1 Pro Preview)

     Prompt: write a script that investigate on whether older subjects tends to
     get higher scores, use visualization and statistical analysis to convey the
     result

   - [`advance_investigate_scores.py`](./advance_investigate_scores.py) for
     further investigation on the relationship between scores and age, taking
     more factors into consideration.
     (Written by Gemini 3.1 Pro Preview)

     Prompt:
     1. don't just consider the score, it's only to 1 decimal place, calculate
        it from score_details to get higher precision
     2. bangumi was created in 2009, take this factor into consideration
     3. also take the number of votes and standard deviation into consideration
        as the subject might be overpraised or disliked so that there's
        intentional low/high rating
     4. consider more aspect carefully as needed
     5. more plots to reveal different aspects of the data

   - [`investigate_post_2009.py`](./investigate_post_2009.py) for investigating
     multidimensional analysis of factors that might influence the scores of
     subjects created after 2009.
     (Written by Gemini 3.1 Pro Preview)

     Prompt: after running the script, it's confirmed that there's a difference
     between the distributions before and after 2009, however a further research
     would be investing on the trend after 2009, the effect on popularity on
     polarity and scores, and more multi-dimensional factors

## Results

### Score Analysis

![Score vs age](https://raw.githubusercontent.com/BrandenXia/bangumi-analysis/refs/heads/main/results/score_vs_age_analysis.png)

```text
------------------------------
STATISTICAL ANALYSIS RESULTS
------------------------------
Pearson Correlation  : 0.2827 (p-value: 0.0000e+00)
Spearman Correlation : 0.3162 (p-value: 0.0000e+00)
Linear Regression    : Score = (0.0324 * Age) + 6.3931

[Conclusion]
There is a statistically significant POSITIVE relationship.
Older subjects DO tend to get higher scores (approx +0.0324 points per year of age).
```

Statistical test shown that, it's every likely that older subjects tend to give
higher scores. The correlation is not very strong, but it is statistically significant.
While the increase in score is not very large, it's still noticeable in decade-long
scale.

![Advance score vs age](https://raw.githubusercontent.com/BrandenXia/bangumi-analysis/refs/heads/main/results/advanced_score_analysis.png)

```text
==================================================
STATISTICAL ANALYSIS RESULTS
==================================================
Pre-2009 Subjects:  6,214 (Mean Score: 7.144, Mean StdDev: 1.227)
Post-2009 Subjects: 19,918 (Mean Score: 6.689, Mean StdDev: 1.246)

T-Test (Pre vs Post 2009 Scores): p-value = 7.8840e-229
>> STATISTICAL CONCLUSION: There is a significant difference between Pre-2009 and Post-2009 scores.
>> This strongly suggests 'Survivorship Bias' / Nostalgia: Older, poorly-rated shows are forgotten, heavily inflating the average scores of older items.

--- Post-2009 Only (Contemporary Voting Analysis) ---
Spearman Correlation (Age vs Score): 0.2749 (p=0.0000e+00)
Spearman Correlation (Age vs Std Dev): -0.1134 (p=5.6432e-58)
```

A more detailed analysis was conducted to account for the creation date of
Bangumi and the number of votes. The results indicate that there is a significant
difference in scores between subjects created before and after 2009, suggesting
a potential survivorship bias or nostalgia effect.

![Post 2009 multidimensional analysis](https://raw.githubusercontent.com/BrandenXia/bangumi-analysis/refs/heads/main/results/bangumi_post_2009_multidimensional.png)

```text
============================================================
MULTIVARIATE REGRESSION ANALYSIS (Post-2009)
============================================================
Goal: Isolate the effect of Year, Popularity, and Category.

--- MODEL 1: What drives HIGHER SCORES? ---
R-squared: 0.3415
-> Time Trend : Score decreases by 0.0420 points every year (p=1.6245e-255).
-> Popularity : Score increases by 0.6442 points for every 10x increase in votes (p=0.0000e+00).

--- MODEL 2: What drives POLARIZATION (Haters vs Fanboys)? ---
R-squared: 0.0838
-> Popularity : Subjects become less polarized (StdDev changes by -0.0837) as popularity 10x's (p=6.5920e-121).
```

After removing the pre-2009 subjects, a multivariate regression analysis was
conducted to isolate the effects of year, popularity, and category on scores and
polarization. The results indicate that more recent subjects tend to receive
lower scores, while increased popularity is associated with higher scores and
reduced polarization.
