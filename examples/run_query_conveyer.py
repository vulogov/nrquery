import nrquery

q = nrquery.Query()
q += "SELECT * FROM TransactionError LIMIT 1"
q += "SELECT * FROM TransactionError LIMIT 1"
res = q.Run()
print("All queries elapsed:", res.Elapsed)
df = res.Dataframe()
print(df)
