from panel.auth import GenericLoginHandler, log, _deserialize_state, decode_response_body, decode_token, OAuthLoginHandler
from panel.config import config
from panel.io.state import state
from tornado.httpclient import HTTPError as HTTPClientError, HTTPRequest, HTTPError
import urllib.parse as urlparse


class PKCELoginHandler(GenericLoginHandler):
    """
    Handles the PKCE login flow for Panel.
    """

    async def _fetch_access_token(
        self, client_id, redirect_uri=None, client_secret=None, code=None,
        refresh_token=None, username=None, password=None
    ):
        """
        Overrides the panel.auth.OAuthLoginHandler._fetch_access_token method to implement the PKCE flow.
        See https://github.com/holoviz/panel/issues/7979.

        Fetches the access token.

        Parameters
        ----------
        client_id:
          The client ID
        redirect_uri:
          The redirect URI
        code:
          The response code from the server
        client_secret:
          The client secret
        refresh_token:
          A token used for refreshing the access_token
        username:
          A username
        password:
          A password
        """
        log.debug("%s making access token request.", type(self).__name__)
        params = {
            'client_id': client_id,
            **self._EXTRA_TOKEN_PARAMS
        }
        if redirect_uri:
            params['redirect_uri'] = redirect_uri
        if self._SCOPE:
            params['scope'] = ' '.join(self._SCOPE)
        if code:
            params['code'] = code
            params['code_verifier'] = self.get_code_cookie()
        if refresh_token:
            refreshing = True
            params['refresh_token'] = refresh_token
            params['grant_type'] = 'refresh_token'
        else:
            refreshing = False
        if client_secret:
            params['client_secret'] = client_secret
        elif username:
            params.update(username=username, password=password)
        else:
            params['code_verifier'] = self.get_code_cookie()

        http = self.get_auth_http_client()

        # Request the access token.
        req = HTTPRequest(
            self._OAUTH_ACCESS_TOKEN_URL,
            method='POST',
            body=urlparse.urlencode(params),
            headers=self._API_BASE_HEADERS
        )
        try:
            response = await http.fetch(req)
        except HTTPClientError as e:
            log.debug("%s access token request failed.", type(self).__name__)
            self._raise_error(e.response, status=401)

        if not response.body or not (body := decode_response_body(response)):
            log.debug("%s token endpoint did not return a valid access token.",
                      type(self).__name__)
            self._raise_error(response)

        if 'access_token' not in body:
            if refresh_token:
                log.debug("%s token endpoint did not reissue an access token.",
                          type(self).__name__)
                return None, None, None
            self._raise_error(response, body, status=401)

        expires_in = body.get('expires_in')
        if expires_in:
            expires_in = int(expires_in)

        access_token, refresh_token = body['access_token'], body.get('refresh_token')
        if refreshing:
            # When refreshing the tokens we do not need to re-fetch the id_token or user info
            return None, access_token, refresh_token, expires_in
        elif id_token := body.get('id_token'):
            try:
                user = OAuthLoginHandler.set_auth_cookies(
                    self, id_token, access_token, refresh_token, expires_in)
            except HTTPError:
                pass
            else:
                log.debug("%s successfully obtained access_token and id_token.",
                          type(self).__name__)
                return user, access_token, refresh_token, expires_in

        user_headers = dict(self._API_BASE_HEADERS)
        if self._OAUTH_USER_URL:
            if self._access_token_header:
                user_url = self._OAUTH_USER_URL
                user_headers['Authorization'] = self._access_token_header.format(
                    body['access_token']
                )
            else:
                user_url = '{}{}'.format(self._OAUTH_USER_URL, body['access_token'])

            log.debug("%s requesting OpenID userinfo.", type(self).__name__)
            try:
                user_response = await http.fetch(user_url, headers=user_headers)
                id_token = decode_response_body(user_response)
            except HTTPClientError:
                id_token = None

        if not id_token:
            log.debug(
                "%s could not fetch user information, the token endpoint did not "
                "return an id_token and no OpenID user info endpoint was provided. "
                "Attempting to code access_token to resolve user information.",
                type(self).__name__
            )
            try:
                id_token = decode_token(body['access_token'])
            except Exception:
                log.debug("%s could not decode access_token.", type(self).__name__)
                self._raise_error(response, body, status=401)

        log.debug("%s successfully obtained access_token and userinfo.",
                  type(self).__name__)
        user = OAuthLoginHandler.set_auth_cookies(
            self, id_token, access_token, refresh_token, expires_in)
        return user, access_token, refresh_token, expires_in

    async def get(self):
        """
        Handles the GET request for the PKCE login flow.

        Copied and modified from panel.auth.CodeChallengeLoginHandler
        See https://github.com/holoviz/panel/issues/7979
        """
        code = self.get_argument("code", "")
        url_state = self.get_argument("state", "")
        redirect_uri = self._redirect_uri
        if not code or not url_state:
            self._authorize_redirect(redirect_uri)
            return

        cookie_state = self.get_state_cookie()
        if cookie_state != url_state:
            log.warning("OAuth state mismatch: %s != %s", cookie_state, url_state)
            raise HTTPError(400, "OAuth state mismatch")

        decoded_state = _deserialize_state(url_state)
        user = await self.get_authenticated_user(redirect_uri, config.oauth_key, url_state, client_secret=config.oauth_secret, code=code)
        if user is None:
            raise HTTPError(403)
        log.debug("%s authorized user, redirecting to app.", type(self).__name__)
        self.redirect(decoded_state.get('next_url', state.base_url))

    def _authorize_redirect(self, redirect_uri):
        state = self.get_state()
        self.set_state_cookie(state)
        code_verifier, code_challenge = self.get_code()
        self.set_code_cookie(code_verifier)
        params = {
            "client_id": config.oauth_key,
            "response_type": "code",
            "scope": ' '.join(self._SCOPE),
            "state": state,
            "response_mode": "query",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "redirect_uri": redirect_uri
        }
        query_params = urlparse.urlencode(params)
        self.redirect(f"{self._OAUTH_AUTHORIZE_URL}?{query_params}")
