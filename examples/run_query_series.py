import nrquery

res = nrquery.Query().Run("SELECT count(*) FROM TransactionError")
print(res.Series())
