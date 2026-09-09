"""
Technique 5 — APIs with login / session
=======================================
Extension of technique 3: many sites keep the data behind a login. The flow:
  1. Authenticate (sending user/password, or a token/cookie you copied).
  2. Save the session cookie/token.
  3. Reuse that session on every subsequent request.

requests.Session() stores cookies automatically between requests.

Practice site: https://quotes.toscrape.com/login
  - It has a form with a hidden "csrf_token" field that changes every time.
  - You must read it first and send it with the login (VERY common pattern).
  - After logging in, each quote shows a "Goodreads" link that's only visible
    when authenticated: that's how we verify the session works.

Test user/password: anything (the site accepts whatever).

Run:  python 05_login_sesion.py
"""

import requests
from bs4 import BeautifulSoup

BASE = "https://quotes.toscrape.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (scraping-practice)"}


def get_csrf(session: requests.Session) -> str:
    """Reads the CSRF token from the login form (hidden field)."""
    r = session.get(f"{BASE}/login", timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    return soup.select_one('input[name="csrf_token"]')["value"]


def main():
    with requests.Session() as s:
        s.headers.update(HEADERS)

        # 1. CSRF token + 2. submit login
        csrf = get_csrf(s)
        r = s.post(
            f"{BASE}/login",
            data={"csrf_token": csrf, "username": "practice", "password": "1234"},
            timeout=15,
        )
        r.raise_for_status()

        # 3. Verify the session is authenticated
        soup = BeautifulSoup(r.text, "lxml")
        if soup.select_one('a[href="/logout"]'):
            print("Login OK: the session is authenticated.")
        else:
            print("Login failed (the logout link did not appear).")
            return

        # 4. Use the session to access protected content
        home = s.get(BASE, timeout=15)
        soup = BeautifulSoup(home.text, "lxml")
        goodreads_links = soup.select('a[href*="goodreads.com"]')
        print(f"'Goodreads' links visible only when logged in: {len(goodreads_links)}")
        print("\nThe same pattern applies to real APIs: the token goes in a header,")
        print("for example  s.headers['Authorization'] = 'Bearer <token>'")


if __name__ == "__main__":
    main()
