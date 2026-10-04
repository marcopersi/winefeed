"""Fetcher registry."""
from .hdh import HdhFetcher
from .idealwine import IdealwineFetcher
from .koppe import KoppeFetcher
from .langtons import LangtonsFetcher
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
    "koppe": KoppeFetcher(),
    "langtons": LangtonsFetcher(),
}


def get(provider):
    return FETCHERS[provider]
