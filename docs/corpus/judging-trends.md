# Judging Trends in Your Training Data

Single workouts are noisy. Day-to-day performance swings with sleep, food, stress, time of day, and plain variance, which means one good session proves nothing and one bad session disproves nothing. A useful read of training data starts with a simple discipline: never conclude anything from a single week.

How much data is enough. A trend needs roughly three to four weeks of points, more if the weekly series is jumpy. With fewer than that, the honest answer is that there is not enough information yet, and the coach should say so rather than narrate meaning into noise. Flagging small samples is a feature of good coaching, not an admission of weakness: two weeks of flat numbers is a pause, not a verdict.

What normal progress looks like. Improvement arrives in waves, not a straight line. Weekly best estimated one-rep max rises for several weeks, plateaus, maybe dips, then rises again as the program and recovery line up. Weekly tonnage climbs deliberately across a training block by design, then drops in a deload week on purpose. A sawtooth with a rising ceiling is healthy; expecting monotonic ascent sets you up to misread every ordinary dip.

Artifacts that mimic decline. A weekly best e1RM is just the highest single set of the week, so a week where the top set got missed, cut short, or done tired reads lower for reasons that have nothing to do with ability. Check whether the week simply contained fewer or softer sets before diagnosing lost strength. Partial weeks at calendar boundaries, holidays, and schedule shifts do the same to tonnage. An exercise swap resets the series entirely, so the first week of a new variation is not comparable to the last week of the old one.

Like-for-like, always. Compare an exercise with itself, the same metric, the same bucket size, similar rep ranges, because estimated one-rep max from a five-rep set and from a fifteen-rep set are not the same kind of number, as the Reading Your Spottr Numbers document explains. Mixing rep schemes mid-block makes the e1RM series jitter for reasons that are arithmetic, not physiological.

Regression to the mean. An exceptional week, the one where everything felt light, is usually followed by an ordinary one. The temptation is to read the fall as a problem and the peak as the new normal; both readings are usually wrong. The trend across a month is the truth; the extremes are weather.

What the patterns mean, roughly. Flat tonnage and flat e1RM for four to six weeks while effort stays high: a programming variable needs to change, load, reps, sets, range of motion, or exercise selection, per the Progressive Overload document. Declining numbers across two to three weeks on unchanged programming: suspect fatigue and check sleep, stress, and soreness before blaming the program, per the Fatigue and Recovery Management document, and consider a deload. Rising numbers: change nothing, and let the block run.

The final discipline is epistemic honesty about what the data can say. Tonnage and e1RM describe work performed and best-set performance; they do not directly measure fatigue, muscle growth, or recovery. Read them as strong indicators, corroborate with how the body feels and performs, and when the data is thin, gather more data before acting on it.

## Sources

- Spottr weekly bucketing and metric definitions: app/engine/helpers.py
- Spottr coaching instructions on small-sample caution and metric selection: app/engine/prompts/instructions.py
