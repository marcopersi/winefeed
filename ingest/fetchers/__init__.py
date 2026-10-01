"""Fetcher registry."""
from .idealwine import IdealwineFetcher
from .weinauktion import WeinauktionFetcher

FETCHERS = {
    "steinfels": WeinauktionFetcher(
        provider="steinfels", base_url="https://auktionen.steinfelsweine.ch"),
    "weinboerse": WeinauktionFetcher(
        provider="weinboerse", base_url="https://auktion.weinauktion.ch"),
    "idealwine": IdealwineFetcher(),
}


def get(provider):
    return FETCHERS[provider]
