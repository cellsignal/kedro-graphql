from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth


def init_auth_router(config):

    oauth = OAuth()
    oauth.register(
        "oidc",
        client_id=config['KEDRO_GRAPHQL_OAUTH_KEY'],
        client_secret=config['KEDRO_GRAPHQL_OAUTH_SECRET'],
        client_kwargs={
            "scope": " ".join(config['KEDRO_GRAPHQL_OAUTH_SCOPE']),
        },
        server_metadata_url=config['KEDRO_GRAPHQL_OAUTH_EXTRA_PARAMS']["OPENID_CONNECT_URL"],
    )

    auth_router = APIRouter()

    @auth_router.get("/login")
    async def login(request: Request):
        """
        Redirects the user to the OIDC Logout page
        """
        if 'id_token' not in request.session:
            return await oauth.oidc.authorize_redirect(
                request,
                redirect_uri=request.url_for("callback")
            )
        # 👆 new code
        return RedirectResponse(url=request.url_for("graphql"))

    # @auth_router.get("/signup")
    # async def signup(request: Request):
    # """
    # Redirects the user to the OIDC Sign Up page
    # """
    # return {"message": "Sign Up"}
    ##

    @auth_router.get("/logout")
    def logout(request: Request):
        """
        Redirects the user to the OIDC Logout page
        """
        # response = RedirectResponse(
        # url="https://" + auth0_config['DOMAIN']
        # + "/v2/logout?"
        # + urlencode(
        # {
        # "returnTo": request.url_for("home"),
        # "client_id": auth0_config['CLIENT_ID'],
        # },
        # quote_via=quote_plus,
        # )
        # )
        request.session.clear()
        return RedirectResponse(url=request.url_for("login"))

    @auth_router.get("/callback")
    async def callback(request: Request):
        """
        Callback redirect from OIDC provider after authentication
        """
        print("Callback called", request.cookies)
        token = await oauth.oidc.authorize_access_token(request)
        # Store `id_token`, and `userinfo` in session
        request.session['id_token'] = token['id_token']
        request.session['userinfo'] = token['userinfo']
        # 👆 new code
        return RedirectResponse(url=request.url_for("graphql"))

    return auth_router
