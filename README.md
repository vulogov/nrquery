# python-module-template

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/vulogov/nrquery/main.svg)](https://results.pre-commit.ci/latest/github/vulogov/nrquery/main)

[![Python package](https://github.com/vulogov/nrquery/actions/workflows/python-tests.yml/badge.svg?branch=main)](https://github.com/vulogov/nrquery/actions/workflows/python-tests.yml)
[![codecov](https://codecov.io/gh/vulogov/nrquery/branch/main/graph/badge.svg?token=YCYBT8TA13)](https://codecov.io/gh/vulogov/nrquery)

Query interface for the telemetry from New Relic SaaS platform.

## Requirements

- [Python](https://python.org) >= 3.8

## Description

This module, designed to be used ether from Jypyter or from application providing you a query  access to your data stored in New Relic platform, so you can perform custom analysis.

## Installation

You can download this module from [GitHub](https://github.com/vulogov/nrquery) repository. Then run

```
make init dependencies
```
This  will install all dependencies. Then running the pip install as

```
pip install .
```
from the module directory source and nrquery module will be installed

## How to query New Relic platform ?

nrquery module uses New Relic advanced GraphQL capabilities, but currently only supports [NRQL](https://docs.newrelic.com/docs/query-your-data/nrql-new-relic-query-language/get-started/introduction-nrql-new-relics-query-language/) queries. GraphQL queries will be implemented at some point in the future. Module consists of two classes:

## Query class

nrquery.Query class provides an interface for sending NRQL queries to New Relic GraphQL API endpoint. Constructor of that class takes two values:

New Relic account (or None)
New Relic API User key (or None)

if you pass None to any of the parameters, nrquery module will try to take account information from NRACCOUNT environment variable and API key from NRAPIKEY environment variable.

If nether is specified, exception will be raised.

nrquery.Query.Run method takes NRQL query as parameter and returns nrquery.Result object.

```python
import nrquery

res = nrquery.Query().Run("SELECT COUNT(*) FROM TransactionError")
```

## Result class

You shall not directly create instances of the nrquery.Result class. Method Run of the class nrquery.Query will return an instance of the Result class. There are few class variables that can pose some interest:

* nrquery.Result.IsSuccess - True or False insicating success or failure of the query associated with result.
* nrquery.Result.Elapsed - time tat takes New Relic platform to run that query
* nrquery.Result.Query - query associated with that result

Following methods can be used to extract the value of the query. You must undestand the expected query outcome and use appropriate conversion methods:

* nrquery.Result.Json - will convert result into a plain JSON
* nrquery.Result.Series - will convert result into a single Pandas series object
* nrquery.Result.Dataframe - will convert result into a Pandas Dataframe object
* nrquery.Result.CSV - will convert result into a CSV string.
* nrqauery.Result.Numpy - will convert result into a dictionary of numpy arrays

```python
import nrquery

res = nrquery.Query().Run("SELECT * FROM TransactionError")
df = res.Dataframe()
```
