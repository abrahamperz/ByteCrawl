"""
EXTRA — Handling CAPTCHAs
=========================
A CAPTCHA is a barrier designed to stop bots. You don't "break" it by force:
the legitimate strategies are basically three.

------------------------------------------------------------------------------
STRATEGY 1 (the best): AVOID IT
------------------------------------------------------------------------------
Many CAPTCHAs only appear when the site suspects you're a bot:
  - Going too fast                  -> slow down (DOWNLOAD_DELAY, sleep).
  - Bot User-Agent                  -> use a real browser one.
  - No cookies / "human" session    -> reuse a session with a real login.
  - Is there an API behind it (technique 3)? APIs usually have NO CAPTCHA.
If you scrape calmly and look like a normal user, it often never shows up.

------------------------------------------------------------------------------
STRATEGY 2: SOLVE IT YOURSELF (semi-manual with Playwright)
------------------------------------------------------------------------------
For small volumes, open a NON-headless browser, solve the CAPTCHA by hand
once, and let the script continue with the already-validated session.
"""

# --- Strategy 2 example: pause to solve by hand ---
def manual_captcha():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # visible on purpose
        page = browser.new_page()
        page.goto("https://www.google.com/recaptcha/api2/demo")

        print("Solve the CAPTCHA in the browser window...")
        # Wait until the success marker appears (site-specific selector).
        # The user solves it manually; the script just waits.
        page.wait_for_selector("#recaptcha-demo-submit", timeout=120_000)
        print("CAPTCHA solved. The session can now continue automatically.")
        browser.close()


# ------------------------------------------------------------------------------
# STRATEGY 3: EXTERNAL SOLVING SERVICE (paid)
# ------------------------------------------------------------------------------
# Services like 2Captcha or Anti-Captcha solve the challenge for you (humans
# or AI) and return the token. You inject it into the form.
# Requires:  pip install 2captcha-python   and an API key with credit.
def external_captcha_service(sitekey: str, url: str):
    """Skeleton for using an external solver (requires a real API key)."""
    from twocaptcha import TwoCaptcha  # part of the 2captcha-python package

    solver = TwoCaptcha("YOUR_API_KEY")
    result = solver.recaptcha(sitekey=sitekey, url=url)
    token = result["code"]
    # That 'token' gets injected into the form's g-recaptcha-response field
    # and then the form is submitted as usual.
    return token


# ------------------------------------------------------------------------------
# LEGAL / ETHICAL NOTE
# ------------------------------------------------------------------------------
# - Respect robots.txt and the site's Terms of Service.
# - Bypassing CAPTCHAs on third-party sites may violate their terms.
# - To PRACTICE, use sites built for it (toscrape.com) or your own systems
#   where you have permission.

if __name__ == "__main__":
    print(__doc__)
    print("Edit this file and uncomment the strategy you want to try.")
    # manual_captcha()
