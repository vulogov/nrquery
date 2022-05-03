import nrquery

res = nrquery.Query().Run("SELECT * FROM TransactionError LIMIT 1")
print(res.Dataframe())
