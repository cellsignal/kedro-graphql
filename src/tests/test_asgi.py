import pytest

from cloudevents.http import CloudEvent
from cloudevents.conversion import to_structured
from requests import Request, Session
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


class TestASGI:

    @pytest.fixture
    def event_data(self):
        attributes = {"id": "1234",
                      "type": "com.example.event",
                      "source": "example.com"}
        data = {"key": "value"}
        return CloudEvent(attributes, data)

    @pytest.mark.asyncio
    async def test_post_event(self,
                              mock_server,
                              mock_celery_session_app,
                              celery_session_worker,
                              event_data):
        retry = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry)
        s = Session()
        s.mount('http://', adapter)

        headers, body = to_structured(event_data)

        url = "http://localhost:5000/event/"
        req = Request('POST', url, data=body, headers=headers)
        req_prepped = req.prepare()
        # print("REQUEST:", req_prepped.headers, req_prepped.body)
        resp = s.send(req_prepped)
        # print("RESPONSE:", resp)
        assert resp.status_code == 200
        resp = resp.json()
        # print("RESPONSE JSON:", resp)
        assert resp.keys() == {"id"}
