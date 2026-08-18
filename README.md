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

## Results

### Score vs Age Analysis

![Score vs age](./results/score_vs_age.png)

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
