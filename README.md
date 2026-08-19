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

   - [`investigate_tags.py`](./investigate_tags.py) for investigating the
     relationship between meta_tags and different factors of a subject
     (popularity, score, stdev, etc.)
     (Written by Gemini 3.1 Pro Preview)

     Prompt: work on analysis of the relationship of meta_tags to different factors of a subject (popularity, score, stdev, etc.)

## Results

(Most of the Chinese text corresponds to the English text above it)

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

The p-value here is small enough that it's statistically significant. The result
of linear regression indicates that for every additional year of age, the score
increases by 0.0324 points. Although the coefficient is not large, over several
decades, this can be quite significant.

可以看到，这里p-value非常小（已经underflow到0了），可以肯定统计意义上确实是有关联的，线性回归给出的结论是作品年龄每多一年伴随着0.0324的分数增加，虽然系数不大，但在几十年的跨度上相当显著

So the conclusion is that there is indeed a trend of biasing towards older works...?

所以结论是bangumi确实在评分上倾向于老作品…吗？

As it's often said, correlation does not imply causation. Regarding that Bangumi
is created in 2009, a reasonable guess is that there's survivorship bias, meaning
that older works that are still remembered and rated are likely to be the better
ones, while the poorly-rated older works have been forgotten. This certain might
happened, so I asked Gemini to do more work.

统计意义上的关联并不代表因果上相关，这时候我想到了bangumi是2009年建立的，猜想可能是因为2009年前令人印象深刻的作品才会被评分导致的幸存者偏差，于是继续让gemini写

So there's the following results:

于是有了这部分结论：

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

As we can see, the t-test shows a significant difference in the distributions
before and after 2009, indicating that the higher scores for older works may not
be due to intentional bias but rather influenced by survivorship bias.

可以看到，通过t-test，以2009为界的分布确实是有明显差异的，也就是说并不一定是评分上故意偏向老番，也受到了幸存者偏差的影响

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

The results shows that the coefficient for time trend is even larger than before,
while higher popularity (given enough votes) means higher scores, and for every
10x increase in the number of votes, the standard deviation decreases
(meaning more consistent ratings). Additionally, we can see that there are many
shows with a few hundred votes and scores concentrated between 6.5-7.5, likely
due to the large number of similar, templated animes (e.g., isekai animes).

结果是时间上影响的系数反而比之前更大了，同时更高人气（在人数足够的基础上）意味着分数增加，以及评分数量每增加10倍大概会对应标准差减少（也就是一致好评），同时可以看到，大概是同质类模版番（比如说异世界厕纸）的原因，有很多人数在几百人、评分集中在6.5-7.5分之间的番

### Metatags Analysis

![Anime tags analysis](https://raw.githubusercontent.com/BrandenXia/bangumi-analysis/refs/heads/main/results/anime_metatags_analysis.png)

```text
--- TOP 10 HIGHEST RATED ANIME TAGS (By Average Score) ---
美国                   | Score:  7.01 | Subjects:   322 | Median Votes:    340
欧美                   | Score:  6.92 | Subjects:   674 | Median Votes:    177
日常                   | Score:  6.88 | Subjects:   486 | Median Votes:   2472
科幻                   | Score:  6.83 | Subjects:   664 | Median Votes:    990
音乐                   | Score:  6.74 | Subjects:   127 | Median Votes:   1178
运动                   | Score:  6.73 | Subjects:   140 | Median Votes:    852
机战                   | Score:  6.72 | Subjects:   192 | Median Votes:   1122
百合                   | Score:  6.70 | Subjects:   515 | Median Votes:   1291
校园                   | Score:  6.68 | Subjects:   545 | Median Votes:   2551
剧场版                  | Score:  6.66 | Subjects:  1734 | Median Votes:    364

--- TOP 10 MOST POLARIZED ANIME TAGS (By Average Standard Deviation) ---
玄幻                   | StDev:  1.52 | Score:  6.30 | Subjects:   124
R18                  | StDev:  1.51 | Score:  5.73 | Subjects:   480
中国                   | StDev:  1.41 | Score:  6.17 | Subjects:   929
OVA                  | StDev:  1.38 | Score:  6.04 | Subjects:  2466
WEB                  | StDev:  1.35 | Score:  6.17 | Subjects:  1155
穿越                   | StDev:  1.35 | Score:  5.82 | Subjects:   143
游戏改                  | StDev:  1.33 | Score:  6.07 | Subjects:   882
子供向                  | StDev:  1.33 | Score:  6.46 | Subjects:   224
音乐                   | StDev:  1.31 | Score:  6.74 | Subjects:   127
小说改                  | StDev:  1.30 | Score:  6.29 | Subjects:  1196

--- TOP 10 MOST POPULAR ANIME TAGS (By Median Votes per Subject) ---
悬疑                   | Median Votes:   3170 | Score:  6.48 | Subjects:   173
推理                   | Median Votes:   2684 | Score:  6.42 | Subjects:   110
校园                   | Median Votes:   2551 | Score:  6.68 | Subjects:   545
日常                   | Median Votes:   2472 | Score:  6.88 | Subjects:   486
恋爱                   | Median Votes:   2148 | Score:  6.51 | Subjects:   660
后宫                   | Median Votes:   1828 | Score:  6.24 | Subjects:   476
战斗                   | Median Votes:   1720 | Score:  6.44 | Subjects:  1023
奇幻                   | Median Votes:   1706 | Score:  6.41 | Subjects:  1055
小说改                  | Median Votes:   1366 | Score:  6.29 | Subjects:  1196
百合                   | Median Votes:   1291 | Score:  6.70 | Subjects:   515
```

There isn't much to say about this analysis. It's pretty straightforward.
However, a further direction that might be interesting is to investigate on how
each tags affects each other and whether the tags' effect change as the date of
creation changes.

这部分没什么好说的，就是字面意思，不过可以考虑进一步分析各个标签之间的关系，以及对于不同年代的番，标签对评分的影响是否会发生变化

So there's the following two analysis:

也就是下面这两个分析：

![Anime tag synergy](https://raw.githubusercontent.com/BrandenXia/bangumi-analysis/refs/heads/main/results/anime_tag_synergy.png)
![Anime tags over time](https://raw.githubusercontent.com/BrandenXia/bangumi-analysis/refs/heads/main/results/anime_tags_over_time.png)
