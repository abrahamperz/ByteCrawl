"""Session login flow: CSRF extraction, failure handling, bearer tokens."""

import pytest
import requests

from bytecrawl import Scraper
from tests.conftest import FakeResponse

LOGIN_FORM = """<html><body><form>
<input name="csrf_token" value="tok123">
<input name="user"><input name="pass">
</form></body></html>"""


class TestLogin:
    def test_csrf_token_read_and_posted(self, http):
        http.routes["https://x.test/login"] = FakeResponse(text=LOGIN_FORM)
        http.routes["POST https://x.test/login"] = FakeResponse(status=200)

        Scraper().session().login("https://x.test/login",
                                  {"user": "ana", "pass": "s3cret"},
                                  csrf_field="csrf_token")

        method, url, kw = http.calls[-1]
        assert (method, url) == ("POST", "https://x.test/login")
        assert kw["data"] == {"user": "ana", "pass": "s3cret",
                              "csrf_token": "tok123"}

    def test_csrf_input_without_value_posts_empty(self, http):
        # Regression: token["value"] used to KeyError on <input> with no value.
        http.routes["https://x.test/login"] = FakeResponse(
            text='<input name="csrf_token">')
        http.routes["POST https://x.test/login"] = FakeResponse(status=200)

        Scraper().session().login("https://x.test/login", {"user": "ana"},
                                  csrf_field="csrf_token")
        assert http.calls[-1][2]["data"]["csrf_token"] == ""

    def test_failed_post_raises(self, http):
        # Regression: a rejected login used to fail silently.
        http.routes["https://x.test/login"] = FakeResponse(text=LOGIN_FORM)
        http.routes["POST https://x.test/login"] = FakeResponse(status=403)

        with pytest.raises(requests.HTTPError):
            Scraper().session().login("https://x.test/login", {"user": "ana"},
                                      csrf_field="csrf_token")

    def test_login_without_csrf_skips_get(self, http):
        http.routes["POST https://x.test/login"] = FakeResponse(status=200)
        Scraper().session().login("https://x.test/login", {"user": "ana"})
        assert [c[0] for c in http.calls] == ["POST"]


class TestBearer:
    def test_sets_authorization_header(self):
        s = Scraper().session().bearer("abc123")
        assert s._s.headers["Authorization"] == "Bearer abc123"

    def test_fetch_returns_page(self, http):
        http.routes["https://x.test/private"] = FakeResponse(
            text="<html><body>secret</body></html>")
        page = Scraper().session().fetch("https://x.test/private")
        assert "secret" in page.html
        assert page.status == 200
