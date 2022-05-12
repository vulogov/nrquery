import nrquery

h = nrquery.Host("host-proxy-east-0")
m = h.Metric()
res = m.Sample("host.cpuSystemPercent", m.Since("1 hour ago"))
print("Sum=", res.Sum())
print("Normalize=", res.Normalize())
print("Avg=", res.Avg())
print("Avg(exponential)=", res.Avg("exponential"))
print("Avg(bellcurve)=", res.Avg("bellcurve"))
print("Avg(log)=", res.Avg("log"))
