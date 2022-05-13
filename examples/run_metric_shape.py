import nrquery

h = nrquery.Host("host-proxy-east-0")
m = h.Metric()
res = m.Sample("host.cpuSystemPercent", m.Since("1 hour ago"), m.LimitMax())
x, Y = res.LoadTrainigData()
print(res.Predict())
# test_data = nrquery.np_norm(
#     [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]
# )
# print(res.runPrediction(None, test_data))
