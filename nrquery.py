"""New Relic Query interface"""

import os
import json
import requests
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


class NREnvError(Exception):
    pass


class NRResultError(Exception):
    pass


def get_env_data(name: str, val: Any) -> Any:
    if val is not None:
        return val
    if name in os.environ.keys():
        return os.environ.get(name)
    raise NREnvError("Error getting value for %s" % name)


class Query:
    def __init__(self, account: Any = None, api_key: Any = None):
        self.NRACCOUNT = get_env_data("NRACCOUNT", account)
        self.NRAPIKEY = get_env_data("NRAPIKEY", api_key)

    def Run(self, query: str) -> Any:
        hdr = {"Content-Type": "application/json", "API-Key": self.NRAPIKEY}
        qry = QTPL % (self.NRACCOUNT, query)
        data = json.dumps({"query": qry})
        r = requests.post(GQLAPI, data=data, headers=hdr)
        res = Result(query, r)
        if not res.IsSuccess:
            raise NRResultError("Query: %s not succesfull" % query)
        return res


class Result:
    def __init__(self, query: str, value: Any):
        self.Query = query
        self.Value = value
        if self.Value.status_code == 200:
            self.IsSuccess = True
        else:
            self.IsSuccess = False
        self.Elapsed = self.Value.elapsed

    def Json(self) -> Any:
        if self.IsSuccess:
            return self.Value.json()["data"]["actor"]["account"]["nrql"]["results"]
        raise NRResultError("Query: %s returned failure" % self.Query)

    def Series(self) -> Any:
        v = self.Json()
        if self.IsSuccess and len(v) == 1 and isinstance(v[0], dict):
            return pd.Series(v[0], name=self.Query)
        raise NRResultError("Query: %s returned failure" % self.Query)

    def Dataframe(self) -> Any:
        v = self.Json()
        if self.IsSuccess and len(v) > 0 and isinstance(v[0], dict):
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
