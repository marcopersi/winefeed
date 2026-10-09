"""Sothebys login via camoufox (solves the Cloudflare Turnstile challenge).

Standard Playwright/patchright keep ``navigator.webdriver`` and the automation
fingerprint, which Cloudflare Turnstile detects. ``camoufox`` runs a patched
Firefox with a humanized fingerprint, so the invisible Turnstile widget on the
Auth0 universal-login page resolves automatically.

Returns the ``globid`` cookie value (a JWT, ~10h lifetime) for use with the
regular ``curl_cffi`` session.
"""
import time

AUTH_URL = ("https://www.sothebys.com/api/auth0login"
            "?lang=en&fromHeader=Y&locale=en")


def login(user, password, headless=True):
    """Log in and return the ``globid`` cookie value, or None on failure."""
    # Lazy import: camoufox is a heavy optional dependency (not on CI).
    from camoufox.sync_api import Camoufox

    with Camoufox(headless=headless, humanize=True) as browser:
        page = browser.new_page()
        page.goto(AUTH_URL, timeout=60000)
        time.sleep(5)
        page.fill('input[name="username"]', user)
        page.locator('button[type="submit"]').first.click()
        time.sleep(8)
        page.fill('input[name="password"]', password)
        page.locator('button[type="submit"]').first.click()
        time.sleep(10)
        cookies = page.context.cookies()
        globid = next((c for c in cookies if c["name"] == "globid"), None)
        return globid["value"] if globid else None
