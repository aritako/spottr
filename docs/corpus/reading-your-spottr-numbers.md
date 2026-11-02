# Reading Your Spottr Numbers

Spottr turns logged workouts into two core metrics per exercise, tonnage and estimated one-rep max, tracked over time in weekly buckets. Understanding what each number actually measures, and what it cannot, is what separates a useful read of your training data from a misleading one.

Estimated one-rep max, e1RM, is computed from every set with the Epley formula: weight multiplied by one plus reps divided by thirty. A set of five at 100 gives an estimated one-rep max of about 117. The number is an estimate, not a measurement, and two properties follow. First, accuracy falls as reps climb: validation work on one-rep-max prediction equations finds them most reliable when the set used fewer than about ten reps, and a twenty-rep set yields a much noisier estimate than a five-rep set. Second, the estimate rises whenever either weight or reps rise, so check which one moved before celebrating: three extra reps at the same weight is real progress, but it is not the same achievement as ten more kilos for the same reps.

Tonnage is volume work: weight times reps, summed across sets. It answers how much total work an exercise received and is best read as a trend line per exercise, rising through a training block, dipping in a deload week, and comparing month over month. Its limits matter. Tonnage conflates load and reps, so ten sets of three at 100 and three sets of ten at 100 are identical tonnage despite being different workouts, and it moves whenever set count, rep scheme, or load changes, which means a tonnage drop can reflect a planned volume cut rather than lost performance. Tonnage is a volume signal, not a growth signal.

Both metrics are organized into weekly buckets with ISO week labels like 2026-W44, where weeks start on Monday. Partial weeks at the start or end of a period, a missed session, or a holiday read as dips that mean nothing. Spottr reports the weekly best e1RM, the highest estimate produced by any single set that week, so one big rep-out lifts the whole week's value; the weekly tonnage is the sum of all sets. A deload week shows up clearly as a tonnage trough, and a slightly lower weekly best e1RM during a deload is expected, not a decline.

Like-for-like comparison is the rule. Compare an exercise only with itself, because each lift has its own loading scale and skill component, and compare e1RM values from similar rep ranges where possible, since high-rep estimates are inflated noise. Switching exercise variations resets the series: a barbell row and a chest-supported row are different skills with different numbers, and the switch itself explains the first week's difference.

Spottr today computes tonnage and e1RM per exercise over time, and the coach uses them for exactly these roles: tonnage for volume questions, how much work an exercise received; e1RM for strength questions, whether performance on an exercise is climbing. Set counts and personal-record detection are planned future metrics, so answers should rest on the two that exist.

The habit worth building is reading both lines together. Rising tonnage with flat e1RM across a hypertrophy block is the block doing its job. Rising e1RM on modest tonnage during a strength phase is exactly right. Both flat for a month with high effort says a programming variable needs to change, and both falling across several weeks while programming is unchanged is a fatigue signal, not a motivational one.

## Sources

- Spottr metric definitions, estimated one-rep max (Epley), set and workout tonnage, weekly bucketing: app/engine/helpers.py
- LeSuer, D. A., McCormick, J. H., Mayhew, J. L., Wasserstein, R. L., & Arnold, M. D. (1997). The accuracy of prediction equations for estimating 1-RM performance in the bench press, squat, and deadlift. Journal of Strength and Conditioning Research, 11(4), 211-213.
- Mayhew, J. L., et al. (2008). Accuracy of prediction equations for determining one-repetition maximum in untrained exercisers. https://pubmed.ncbi.nlm.nih.gov/18714230/
