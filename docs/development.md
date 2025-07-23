## How to install dependencies

To install them, run:

```
pip install -r src/requirements.txt
```

## How to test

```
pytest src/tests
```

To configure the coverage threshold, go to the `.coveragerc` file.

## Project dependencies

To generate or update the dependency requirements for your project:

```
kedro build-reqs
```

This will `pip-compile` the contents of `src/requirements.txt` into a new file `src/requirements.lock`. You can see the output of the resolution by opening `src/requirements.lock`.

After this, if you'd like to update your project requirements, please update `src/requirements.txt` and re-run `kedro build-reqs`.

[Further information about project dependencies](https://kedro.readthedocs.io/en/stable/kedro_project_setup/dependencies.html#project-specific-dependencies)


## Auto-reload

The cli interface supports "auto-reloading" in order to make development easier.
When starting the api server and worker specify the `-r` or `--reload` option
to turn on auto-reloading.  Any changes to the "src" directory of your kedro
project will trigger a reload.

Start the api server with auto-reload enabled.

```
kedro gql --reload
```

Start a worker (in another terminal) with auto-reload enabled.

```
kedro gql -w --reload
```

The path to watch can be further refined using the `--reload-path` option.
In the following examples a reload will be triggered when changes are
made to files in the `src/kedro_graphql/src/runners` directory.
Start the api server with auto-reload enabled.

```
kedro gql --reload --reload-path ./src/kedro_graphql/runners
```

Start a worker (in another terminal) with auto-reload enabled.

```
kedro gql -w --reload --reload-path ./src/kedro_graphql/runners
```

## TO DO

- support custom runners e.g. Argo Workflows, AWS Batch, etc...
- support passing credentials via api

