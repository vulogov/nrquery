import nrquery

h = nrquery.Host("host-proxy-east-0")
m = h.Metric()
res = m.Sample("host.cpuSystemPercent", m.Since("1 hour ago"), m.LimitMax())
print(res)
