The base application is a strawberry + FastAPI instance.  One can leverage the
additional features FastAPI offers by defining a custom application class.

This example adds a [CORSMiddleware](https://fastapi.tiangolo.com/tutorial/cors/#use-corsmiddleware).

```python
## src/kedro_graphql/example/app.py
from fastapi.middleware.cors import CORSMiddleware
from kedro_graphql.asgi import KedroGraphQL



class MyApp(KedroGraphQL):

    def __init__(self): 
        super(MyApp, self).__init__()

        origins = [
            "http://localhost",
            "http://localhost:8080",
        ]
        
        self.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        print("added CORSMiddleware")

```

When starting the api server specify the import path using the
```--app``` flag.

```bash
kedro gql --app "my_kedro_project.app.MyApp"
## example output
added CORSMiddleware
INFO:     Started server process [7032]
INFO:     Waiting for application startup.
Connected to the MongoDB database!
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:5000 (Press CTRL+C to quit)
```