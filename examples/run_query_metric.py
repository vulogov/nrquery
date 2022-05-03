import nrquery
import numpy as np

res = nrquery.Query().Run(
    """SELECT average(loadAverageOneMinute) as '1 minute', average(loadAverageFiveMinute) AS '5 minutes', average(loadAverageFifteenMinute) AS '15 minutes' FROM SystemSample WHERE `entityGuid` = 'MTYwNjg2MnxJTkZSQXxOQXw0ODg3MTU4MjM0NTcwMjEwMjcw' TIMESERIES auto"""
)
df = res.Dataframe()
min1 = df["1 minute"].to_numpy()
stddev1 = np.nanstd(min1)
var1 = np.nanvar(min1)
print("Standard deviation of 1 minute load average is", stddev1)
print("Variance of 1 minute load average is", var1)
