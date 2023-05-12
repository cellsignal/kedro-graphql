from fastapi.middleware.cors import CORSMiddleware
from kedro_graphql import KedroGraphql


class MyApp(KedroGraphql):

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