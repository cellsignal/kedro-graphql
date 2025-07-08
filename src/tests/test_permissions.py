import pytest

from requests import Request, Session
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


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


class TestIsAuthenticatedXForwardedRBAC:

    @pytest.mark.asyncio
    async def test_missing_x_forwarded_groups_header(self,
                                                     mock_payload,
                                                     mock_server_rbac):

        retry = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry)
        s = Session()
        s.mount('http://', adapter)

        url = "http://localhost:5000/graphql"
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
    async def test_with_x_forwarded_groups_header(self,
                                                  mock_payload,
                                                  mock_server_rbac):

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
        url = "http://localhost:5000/graphql"
        req = Request('POST', url, json=mock_payload, headers=headers)
        req_prepped = req.prepare()
        # print("REQUEST:", req_prepped.headers, req_prepped.body)
        resp = s.send(req_prepped)
        # print("RESPONSE:", resp)
        assert resp.status_code == 200
        resp = resp.json()
        assert resp.keys() == {"data"}
        assert resp["data"].keys() == {"pipelineTemplates"}
