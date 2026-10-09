"""Fetcher registry."""
from .beschcannes import BeschCannesFetcher
from .dobiaschofsky import DobiaschofskyFetcher
from .dorotheum import DorotheumFetcher
from .sothebys import SothebysFetcher
from .finarte import FinarteFetcher
from .hdh import HdhFetcher
from .idealwine import IdealwineFetcher
from .koppe import KoppeFetcher
from .langtons import LangtonsFetcher
from .pandolfini import PandolfiniFetcher
from .weinauktion import WeinauktionFetcher
from .weinauktionator import WeinauktionatorFetcher
from .winefields import WinefieldsFetcher

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
    "winefields": WinefieldsFetcher(),
    "dorotheum": DorotheumFetcher(),
    "pandolfini": PandolfiniFetcher(),
    "finarte": FinarteFetcher(),
    "besch-cannes": BeschCannesFetcher(),
    "dobiaschofsky": DobiaschofskyFetcher(),
    "sothebys": SothebysFetcher(),
}


def get(provider):
    return FETCHERS[provider]
