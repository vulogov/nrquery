import nrquery

res = nrquery.Query().Run(
    """SELECT average(loadAverageOneMinute) as '1 minute', average(loadAverageFiveMinute) AS '5 minutes', average(loadAverageFifteenMinute) AS '15 minutes' FROM SystemSample WHERE `entityGuid` = 'MTYwNjg2MnxJTkZSQXxOQXw0ODg3MTU4MjM0NTcwMjEwMjcw' TIMESERIES auto"""
)
df = res.Dataframe()
print(df)
