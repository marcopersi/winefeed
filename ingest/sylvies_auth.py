"""sylvies.be login via camoufox (solves the Azure WAF JS challenge).

Standard requests/curl_cffi get a bare 403 "Azure WAF JS Challenge" page;
camoufox runs a patched, humanized Firefox that solves it automatically.
Unlike sothebys, no Cloudflare Turnstile widget sits in front of the login
form itself -- the WAF challenge is solved once on page load, then a plain
email+password form submit is enough.

Returns the cookies needed for a regular ``curl_cffi``/``requests`` session
(``afd_azwaf_jsclearance`` for the WAF, ``.ASPXAUTH`` for the login) --
confirmed these survive on a plain HTTP session with no further JS
challenges on subsequent requests, so camoufox is only needed for this one
login step, not for every fetch.
"""
LOGIN_URL = "https://www.sylvies.be/en/account/login"


def login(user, password, headless=True):
    """Log in and return a dict of cookies, or None on failure."""
    # Lazy import: camoufox is a heavy optional dependency (not on CI).
    from camoufox.sync_api import Camoufox

    with Camoufox(headless=headless, humanize=True) as browser:
        page = browser.new_page()
        page.goto(LOGIN_URL, timeout=60000)
        page.wait_for_selector('input[name="Login.Email"]', timeout=30000)
        page.fill('input[name="Login.Email"]', user)
        page.fill('input[name="Login.Password"]', password)
        # Confirmed real case: this page's first `button[type=submit]` is
        # an unrelated element (not the login form) -- the actual login
        # button is the form's `input[type=submit]`.
        page.locator('input[type="submit"]').click()
        page.wait_for_load_state("networkidle", timeout=30000)
        cookies = {c["name"]: c["value"] for c in page.context.cookies()}
        if ".ASPXAUTH" not in cookies:
            return None
        return cookies
