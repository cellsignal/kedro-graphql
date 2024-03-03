FROM python:3.10.13-alpine3.19

COPY . /opt/kedro-graphql-viz

RUN pip install -r /opt/kedro-graphql-viz/src/requirements.txt

WORKDIR /opt/kedro-graphql-viz

RUN pip install -e .

CMD ["kedro", "gql", "--reload"]