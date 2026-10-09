"""Sothebys login via camoufox (solves the Cloudflare Turnstile challenge).

Standard Playwright/patchright keep ``navigator.webdriver`` and the automation
fingerprint, which Cloudflare Turnstile detects. ``camoufox`` runs a patched
Firefox with a humanized fingerprint, so the invisible Turnstile widget on the
Auth0 universal-login page resolves automatically.

Returns the ``globid`` cookie value (a JWT, ~10h lifetime) for use with the
regular ``curl_cffi`` session.
"""
import os
import time

AUTH_URL = ("https://www.sothebys.com/api/auth0login"
            "?lang=en&fromHeader=Y&locale=en")

PASSWORD_TIMEOUT_MS = 120000


def login(user, password, headless=True):
    """Log in and return the ``globid`` cookie value, or None on failure."""
    # Lazy import: camoufox is a heavy optional dependency (not on CI).
    from camoufox.sync_api import Camoufox

    with Camoufox(headless=headless, humanize=True) as browser:
        page = browser.new_page()
        page.goto(AUTH_URL, timeout=60000)
        page.wait_for_selector('input[name="username"]', timeout=30000)
        page.fill('input[name="username"]', user)
        page.locator('button[type="submit"]').first.click()
        # The invisible Turnstile resolves automatically, then the password
        # field appears. On a datacenter IP Cloudflare may present a visible
        # challenge, which can take longer (or fail).
        try:
            page.wait_for_selector('input[name="password"]',
                                   timeout=PASSWORD_TIMEOUT_MS)
        except Exception as exc:
            _dump_debug(page)
            raise exc
        page.fill('input[name="password"]', password)
        page.locator('button[type="submit"]').first.click()
        for _ in range(20):
            time.sleep(2)
            globid = next((c for c in page.context.cookies()
                           if c["name"] == "globid"), None)
            if globid:
                return globid["value"]
        return None


def _dump_debug(page):
    path = os.environ.get("SOTHEBYS_DEBUG_DIR")
    if not path:
        return
    os.makedirs(path, exist_ok=True)
    try:
        page.screenshot(path=os.path.join(path, "login.png"))
    except Exception:  # noqa: BLE001
        pass
    try:
        with open(os.path.join(path, "login.html"), "w",
                  encoding="utf-8") as fh:
            fh.write(page.content())
    except Exception:  # noqa: BLE001
        pass
