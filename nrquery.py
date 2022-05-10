"""New Relic Query interface"""

import os
import json
import requests
import datetime
import dateparser
import pandas as pd
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
              name
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
            if "beginTimeSeconds" in v[0] and "endTimeSeconds" in v[0]:
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
