import nrquery

res = nrquery.Query().Run("SELECT * FROM TransactionError")
print(res.Json())
