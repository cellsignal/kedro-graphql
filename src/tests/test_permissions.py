import pytest

from requests import Request, Session
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from cloudevents.http import CloudEvent
from cloudevents.conversion import to_structured


@pytest.fixture
def mock_payload():
    query = """
    query TestQuery($limit: Int!) {
      pipelineTemplates(limit: $limit) {
        pageMeta {
          nextCursor
        }
        pipelineTemplates {
          name
          describe
          inputs {
            name
          }
          nodes {
            name
            inputs
            outputs
            tags
          }
          outputs {
            name
          }
          parameters {
            name
            value
          }
        }
      }
    }
    """
    variables = {"limit": 5}
    return {"query": query, "variables": variables}


class TestIsAuthenticatedXForwarded:

    def event_data(self):
        attributes = {"id": "1234",
                      "type": "com.example.event",
                      "source": "example.com"}
        data = {"key": "value"}
        return CloudEvent(attributes, data)

    def event_post(self, port=5000, headers={}):
        retry = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry)
        s = Session()
        s.mount('http://', adapter)

        event_headers, body = to_structured(self.event_data())
        headers.update(event_headers)

        url = "http://localhost:"+str(port)+"/event/"
        req = Request('POST', url, data=body, headers=headers)
        req_prepped = req.prepare()
        return s.send(req_prepped)

    @pytest.mark.asyncio
    async def test_rest_with_x_forwarded_groups_header(self,
                                                       mock_server_5001):
        headers = {
            "X-Forwarded-Groups": "test_group",
            "X-Forwarded-Email": "admin@example.com"}

        resp = self.event_post(port=5001, headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_rest_without_x_forwarded_groups_header(self,
                                                          mock_server_5001):
        headers = {
            "X-Forwarded-Email": "admin@example.com"}

        resp = self.event_post(port=5001, headers=headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_graphql_with_x_forwarded_groups_header(self,
                                                          mock_payload,
                                                          mock_server_5001):

        retry = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry)
        s = Session()
        s.mount('http://', adapter)
        headers = {
            "X-Forwarded-Groups": "test_group",
            "X-Forwarded-Email": "admin@example.com"}
        url = "http://localhost:5001/graphql"
        req = Request('POST', url, json=mock_payload, headers=headers)
        req_prepped = req.prepare()
        # print("REQUEST:", req_prepped.headers, req_prepped.body)
        resp = s.send(req_prepped)
        # print("RESPONSE:", resp)
        assert resp.status_code == 200
        resp = resp.json()
        assert resp.keys() == {"data"}
        assert resp["data"].keys() == {"pipelineTemplates"}

    @pytest.mark.asyncio
    async def test_graphql_without_x_forwarded_groups_header(self,
                                                             mock_payload,
                                                             mock_server_5001):

        retry = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry)
        s = Session()
        s.mount('http://', adapter)

        url = "http://localhost:5001/graphql"
        req = Request('POST', url, json=mock_payload, headers={})
        req_prepped = req.prepare()
        # print("REQUEST:", req_prepped.headers, req_prepped.body)
        resp = s.send(req_prepped)
        # print("RESPONSE:", resp)
        assert resp.status_code == 200
        resp = resp.json()
        assert resp.keys() == {"data", "errors"}
        assert resp["errors"][0]["message"] == "User is not authenticated"

    @pytest.mark.asyncio
    async def test_graphql_with_wrong_x_forwarded_groups_header(self,
                                                                mock_payload,
                                                                mock_server_5001):

        retry = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry)
        s = Session()
        s.mount('http://', adapter)

        headers = {
            "X-Forwarded-Groups": "wrong_group",
            "X-Forwarded-Email": "admin@example.com"}
        url = "http://localhost:5001/graphql"
        req = Request('POST', url, json=mock_payload, headers=headers)

        req_prepped = req.prepare()
        # print("REQUEST:", req_prepped.headers, req_prepped.body)
        resp = s.send(req_prepped)
        # print("RESPONSE:", resp)
        assert resp.status_code == 200
        resp = resp.json()
        assert resp.keys() == {"data", "errors"}
        assert resp["errors"][0]["message"] == "User is not authenticated"

    @pytest.mark.asyncio
    async def test_graphql_with_x_forwarded_email(self,
                                                  mock_payload,
                                                  mock_server_5002):

        retry = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry)
        s = Session()
        s.mount('http://', adapter)
        headers = {
            "X-Forwarded-Email": "admin@example.com"}
        url = "http://localhost:5002/graphql"
        req = Request('POST', url, json=mock_payload, headers=headers)
        req_prepped = req.prepare()
        # print("REQUEST:", req_prepped.headers, req_prepped.body)
        resp = s.send(req_prepped)
        # print("RESPONSE:", resp)
        assert resp.status_code == 200
        resp = resp.json()
        assert resp.keys() == {"data"}
        assert resp["data"].keys() == {"pipelineTemplates"}

    @pytest.mark.asyncio
    async def test_graphql_without_x_forwarded_email(self,
                                                     mock_payload,
                                                     mock_server_5002):

        retry = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry)
        s = Session()
        s.mount('http://', adapter)
        url = "http://localhost:5002/graphql"
        req = Request('POST', url, json=mock_payload)
        req_prepped = req.prepare()
        # print("REQUEST:", req_prepped.headers, req_prepped.body)
        resp = s.send(req_prepped)
        # print("RESPONSE:", resp)
        assert resp.status_code == 200
        resp = resp.json()
        assert resp.keys() == {"data", "errors"}
        assert resp["errors"][0]["message"] == "User is not authenticated"
