# python-module-template

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/vulogov/nrquery/main.svg)](https://results.pre-commit.ci/latest/github/vulogov/nrquery/main)

[![Python package](https://github.com/vulogov/nrquery/actions/workflows/python-tests.yml/badge.svg?branch=main)](https://github.com/vulogov/nrquery/actions/workflows/python-tests.yml)
[![codecov](https://codecov.io/gh/vulogov/nrquery/branch/main/graph/badge.svg?token=YCYBT8TA13)](https://codecov.io/gh/vulogov/nrquery)

[Project description here]

## Requirements

- [Python](https://python.org) >= 3.8

## Internal Links

- [Development Installation Guide](docs/development.md)
- [Repo documentation](docs/)

---

## A template for my non-library style boilerplate.

Straight forward to use!

### Single module projects

- Rename `module_example.py` as desired
- Update `py_modules = module_example` in `setup.cfg` with name
- Update requirements.in as needed
- Run `make update` to populate requirements.txt

### Multi file module projects

- All the steps above
- `py_modules = module_example` becomes a multi-line config with each module name
