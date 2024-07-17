FROM python:3.11.9-alpine3.19

COPY . /opt/kedro-graphql-viz

## required to build psutil
RUN apk add gcc python3-dev musl-dev linux-headers \ 
    && pip install -r /opt/kedro-graphql-viz/src/requirements.txt

WORKDIR /opt/kedro-graphql-viz

RUN pip install -e .

CMD ["kedro", "gql", "--reload"]