"""Fetcher registry."""
from .hdh import HdhFetcher
from .idealwine import IdealwineFetcher
from .weinauktion import WeinauktionFetcher
from .weinauktionator import WeinauktionatorFetcher

FETCHERS = {
    "steinfels": WeinauktionFetcher(
        provider="steinfels", base_url="https://auktionen.steinfelsweine.ch"),
    "weinboerse": WeinauktionFetcher(
        provider="weinboerse", base_url="https://auktion.weinauktion.ch"),
    "idealwine": IdealwineFetcher(),
    "weinauktionator": WeinauktionatorFetcher(),
    "hdh": HdhFetcher(),
}


def get(provider):
    return FETCHERS[provider]
