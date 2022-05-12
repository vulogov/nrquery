"""New Relic Query interface"""

import os
import json
import requests
import datetime
import dateparser
import pandas as pd
import numpy as np
from scipy.stats import norm
from typing import Any

GQLAPI = "https://api.newrelic.com/graphql"

QTPL = """
{
   actor {
      account(id: %s) {
         nrql(query: "%s") {
            results
         }
      }
   }
}
"""

Q = """
{
   actor {
      account(id: %s) {
         %s
      }
   }
}
"""

DEADNODESTPL = """
{
    actor {
        entitySearch(query: "reporting is false and lastReportingChangeAt > %d") {
          results {
            entities {
              name,
              guid
            }
          }
        }
    }
}
"""

ALQ = """
{
  actor {
    entitySearch(query: "alertable is true") {
      results {
        entities {
          name,
          guid
        }
      }
    }
  }
}
"""

NAMQ = """
{
  actor {
    entitySearch(query: "accountId = %s and domain = 'INFRA' and type = 'HOST'  and tags.hostname = '%s'") {
      results {
        entities {
          name
          guid
          accountId
        }
      }
    }
  }
}
"""


class NREnvError(Exception):
    pass


class NRContextError(Exception):
    pass


class NRResultError(Exception):
    pass


def get_env_data(name: str, val: Any) -> Any:
    if val is not None:
        return val
    if name in os.environ.keys():
        return os.environ.get(name)
    raise NREnvError("Error getting value for %s" % name)


def np_normalize(arr, t_min, t_max):
    norm_arr = []
    diff = t_max - t_min
    diff_arr = max(arr) - min(arr)
    for i in arr:
        temp = (((i - min(arr)) * diff) / diff_arr) + t_min
        norm_arr.append(temp)
    return norm_arr


def np_norm(arr):
    return np_normalize(arr, 0, 1)


class WhereClause:
    def Since(self, s):
        return " SINCE %s" % s

    def LimitMax(self):
        return " LIMIT MAX"


class QueryGenerator(WhereClause):
    def __init__(self, source):
        self.SOURCE = source

    def SampleOf(self, name):
        return "SELECT `%s` FROM %s WHERE entity.guid = '%s'" % (
            name,
            self.SOURCE,
            self.Host.GUID,
        )


class Host:
    def __init__(self, name: str, account: str = None, api_key: str = None):
        self.NRACCOUNT = get_env_data("NRACCOUNT", account)
        self.NRAPIKEY = get_env_data("NRAPIKEY", api_key)
        self.NAME = name
        q = Query(self.NRACCOUNT, self.NRAPIKEY)
        res = q.ExecuteRaw(NAMQ % (self.NRACCOUNT, name))
        if not res.IsSuccess:
            self.IsSuccess = False
            return
        jres = res.RawJson()
        acc = []
        try:
            acc = jres["data"]["actor"]["entitySearch"]["results"]["entities"]
            self.IsSuccess = True
        except KeyError:
            self.IsSuccess = False
        if len(acc) == 1:
            self.GUID = acc[0]["guid"]
        else:
            self.GUID = None
            self.IsSuccess = False

    def Metric(self):
        return Metric(self)


class SampleConvert:
    def to_numpy(self):
        data = {}
        for i in self.Name:
            v = self.Value[i].to_numpy()
            data[i] = v
        return data


class CalculateWeight:
    def linear(self, data):
        res = {}
        for k in data.keys():
            res[k] = np.ones(len(data[k]))
        return res

    def exponential(self, data):
        res = {}
        for k in data.keys():
            res[k] = np_norm(np.exp(np.arange(len(data[k]))))
        return res

    def log(self, data):
        res = {}
        for k in data.keys():
            res[k] = np_norm(np.log(np.arange(1.0, len(data[k]) + 1)))
        return res

    def bellcurve(self, data):
        res = {}
        for k in data.keys():
            wa = np.arange(-(len(data[k]) / 2), len(data[k]) / 2, 1)
            res[k] = np_norm(norm.pdf(wa, 0, 1))
        return res


class SampleStatistics(CalculateWeight):
    def apply0(self, fun, data):
        res = {}
        for k in data.keys():
            res[k] = fun(data[k])
        return res

    def applyw(self, fun, model, data):
        res = {}
        if model == "linear":
            w = self.linear(data)
        elif model == "exponential":
            w = self.exponential(data)
        elif model == "log":
            w = self.log(data)
        elif model == "bellcurve":
            w = self.bellcurve(data)
        else:
            w = self.linear(data)
        for k in data.keys():
            res[k] = fun(data[k], weights=w[k])
        return res

    def Sum(self):
        return self.apply0(np.sum, self.to_numpy())

    def Prod(self):
        return self.apply0(np.prod, self.to_numpy())

    def Floor(self):
        return self.apply0(np.floor, self.to_numpy())

    def Gradient(self):
        return self.apply0(np.gradient, self.to_numpy())

    def Min(self):
        return self.apply0(np.nanmin, self.to_numpy())

    def Max(self):
        return self.apply0(np.nanmax, self.to_numpy())

    def Normalize(self):
        return self.apply0(np_norm, self.to_numpy())

    def Avg(self, model="linear"):
        return self.applyw(np.ma.average, model, self.to_numpy())


class Sample(SampleStatistics, SampleConvert):
    def __init__(self, metric_name, host, metric, df):
        self.Name = [metric_name]
        self.Host = host
        self.Metric = metric
        self.Value = df

    def __repr__(self):
        return str(self.Value)


class Metric(QueryGenerator):
    def __init__(self, host):
        self.Host = host
        self.IsSuccess = host.IsSuccess
        QueryGenerator.__init__(self, "Metric")

    def Query(self, query):
        print(query)
        q = Query(self.Host.NRACCOUNT, self.Host.NRAPIKEY)
        res = q.Execute(query).Dataframe()
        del res["datetime"]
        del res["timestamp"]
        return res

    def Sample(self, metric, *clauses):
        c = " "
        for i in clauses:
            c += " " + i
        return Sample(
            metric,
            self.Host,
            self,
            self.Query(self.SampleOf(metric) + c + self.LimitMax()),
        )


class Query:
    def __init__(self, account: Any = None, api_key: Any = None):
        self.ClearQueries()
        self.NRACCOUNT = get_env_data("NRACCOUNT", account)
        self.NRAPIKEY = get_env_data("NRAPIKEY", api_key)

    def ClearQueries(self):
        self.queries = []

    def __add__(self, query: str) -> list:
        self.queries.append(query)
        return self

    def Run(self, query: Any = None) -> Any:
        if query is None and len(self.queries) == 0:
            raise NRContextError("Query context is empty")
        if query is not None and isinstance(query, str) and len(self.queries) == 0:
            return self.Execute(query)
        if query is not None and isinstance(query, str) and len(self.queries) > 0:
            self.queries.append(query)
        if len(self.queries) > 0:
            res = []
            for q in self.queries:
                res.append(self.Execute(q))
            self.ClearQueries()
            return ResultList(self, res)
        raise NRContextError("Query context is invalid")

    def Execute(self, query: str) -> Any:
        hdr = {"Content-Type": "application/json", "API-Key": self.NRAPIKEY}
        qry = QTPL % (self.NRACCOUNT, query)
        data = json.dumps({"query": qry})
        r = requests.post(GQLAPI, data=data, headers=hdr)
        res = Result(self, query, r)
        if not res.IsSuccess:
            raise NRResultError("Query: %s not succesfull" % query)
        return res

    def ExecuteRaw(self, query: str) -> Any:
        hdr = {"Content-Type": "application/json", "API-Key": self.NRAPIKEY}
        data = json.dumps({"query": query})
        r = requests.post(GQLAPI, data=data, headers=hdr)
        res = Result(self, query, r)
        if not res.IsSuccess:
            raise NRResultError("Query: %s not succesfull" % query)
        return res

    def Deadnodes(self, query="1 day ago"):
        ts = dateparser.parse(query)
        tsms = ts.timestamp() * 1000
        DNQ = DEADNODESTPL % tsms
        return self.ExecuteRaw(DNQ)

    def Alertable(self):
        return self.ExecuteRaw(ALQ)


class ResultList:
    def __init__(self, qinst: Query, value: list):
        self.Q = qinst
        self.Value = value
        self.IsSuccess = True
        self.Elapsed = datetime.timedelta(0)
        for r in self.Value:
            if r.Value.status_code != 200:
                self.IsSuccess = False
                break
            else:
                self.Elapsed += r.Value.elapsed

    def Dataframe(self) -> Any:
        ix = []
        ix_type = None
        if self.IsSuccess and len(self.Value) > 0:
            rdf = pd.DataFrame()
            for r in self.Value:
                if not r.IsSuccess:
                    raise NRResultError("Query: %s not succesfull" % r.Query)
                res = r.Json()
                if len(res) > 0 and isinstance(res[0], dict):
                    if ix_type is None:
                        if "timestamp" in res[0]:
                            ix_type = "timestamp"
                        elif "beginTimeSeconds" in res[0]:
                            ix_type = "beginTimeSeconds"
                for v in res:
                    if ix_type is not None:
                        if ix_type in v:
                            if ix_type == "timestamp":
                                ix.append(pd.to_datetime(v["timestamp"], unit="ms"))
                            elif ix_type == "beginTimeSeconds":
                                ix.append(
                                    pd.to_datetime(res["beginTimeSeconds"], unit="s")
                                )
                            else:
                                ix.append(None)
                if len(ix) > 0:
                    df = pd.DataFrame(res, index=ix)
                    ix = []
                else:
                    df = pd.DataFrame(res)
                rdf = pd.concat([rdf, df])
            return rdf
        raise NRResultError("Error during DataFrame merge")


class Result:
    def __init__(self, qinst: Query, query: str, value: Any):
        self.Q = qinst
        self.Query = query
        self.Value = value
        if self.Value.status_code == 200:
            self.IsSuccess = True
        else:
            self.IsSuccess = False
        self.Elapsed = self.Value.elapsed

    def Deadnodes(self) -> Any:
        return self.Results()

    def Alertable(self) -> Any:
        return self.Results()

    def Results(self) -> Any:
        try:
            if self.IsSuccess:
                return self.Value.json()["data"]["actor"]["entitySearch"]["results"][
                    "entities"
                ]
        except KeyError:
            raise NRResultError("Query: %s returned no useful result" % self.Query)
        raise NRResultError("Query: %s returned failure" % self.Query)

    def Json(self) -> Any:
        try:
            if self.IsSuccess:
                return self.Value.json()["data"]["actor"]["account"]["nrql"]["results"]
        except KeyError:
            raise NRResultError("Query: %s returned no useful result" % self.Query)
        raise NRResultError("Query: %s returned failure" % self.Query)

    def RawJson(self) -> Any:
        try:
            if self.IsSuccess:
                return self.Value.json()
        except KeyError:
            raise NRResultError("Query: %s returned no useful result" % self.Query)
        raise NRResultError("Query: %s returned failure" % self.Query)

    def Series(self) -> Any:
        v = self.Json()
        if self.IsSuccess and len(v) == 1 and isinstance(v[0], dict):
            return pd.Series(v[0], name=self.Query)
        raise NRResultError("Query: %s returned failure" % self.Query)

    def Dataframe(self) -> Any:
        v = self.Json()
        if self.IsSuccess and len(v) > 0 and isinstance(v[0], dict):
            if "timestamp" in v[0]:
                ix = []
                for e in v:
                    if "timestamp" in e:
                        ix.append(pd.to_datetime(e["timestamp"], unit="ms"))
                    else:
                        ix.append(None)
                res = pd.DataFrame(v, index=ix)
            elif "beginTimeSeconds" in v[0] and "endTimeSeconds" in v[0]:
                ix = []
                for e in v:
                    if "beginTimeSeconds" in e and "endTimeSeconds" in e:
                        ix.append(pd.to_datetime(e["beginTimeSeconds"], unit="s"))
                    else:
                        ix.append(None)
                res = pd.DataFrame(v, index=ix)
            else:
                res = pd.DataFrame(v)
            if "timestamp" in res:
                res["datetime"] = pd.to_datetime(res["timestamp"], unit="ms")
            if "beginTimeSeconds" in res:
                res["beginDateTime"] = pd.to_datetime(res["beginTimeSeconds"], unit="s")
            if "endTimeSeconds" in res:
                res["endDateTime"] = pd.to_datetime(res["endTimeSeconds"], unit="s")
            return res
        raise NRResultError("Query: %s returned failure" % self.Query)

    def Numpy(self) -> dict:
        res = {}
        df = self.Dataframe()
        for c in df:
            res[c] = df[c].to_numpy()
        return res

    def CSV(self) -> str:
        df = self.Dataframe()
        return df.to_csv()

    def Model(self) -> Any:
        return Model(self)


class Model:
    def __init__(self, res):
        self.Value = res
        self.Df = res.Dataframe()
