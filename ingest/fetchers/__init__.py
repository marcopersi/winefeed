"""Fetcher registry."""
from .baghera import BagheraFetcher
from .beschcannes import BeschCannesFetcher
from .christies import (ChristiesFetcher, MalformedResponse, MetaInvalid,
                        ReconciliationMismatch)
from .denzauktionen import DenzauktionenFetcher
from .dobiaschofsky import DobiaschofskyFetcher
from .dorotheum import DorotheumFetcher
from .sothebys import SothebysFetcher
from .sylvies import SylviesFetcher
from .finarte import FinarteFetcher
from .franzwermuth import FranzWermuthFetcher
from .hdh import HdhFetcher
from .idealwine import IdealwineFetcher
from .koppe import KoppeFetcher
from .langtons import LangtonsFetcher
from .munichwinecompany import MunichWineCompanyFetcher
from .pandolfini import PandolfiniFetcher
from .weinauktion import WeinauktionFetcher
from .weinauktionator import WeinauktionatorFetcher
from .winebarrel import WinebarrelFetcher
from .winefields import WinefieldsFetcher

FETCHERS = {
    "baghera": BagheraFetcher(),
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
    "christies": ChristiesFetcher(),
    "winebarrel": WinebarrelFetcher(),
    "sylvies": SylviesFetcher(),
    "denzauktionen": DenzauktionenFetcher(),
    "munich-wine-company": MunichWineCompanyFetcher(),
    "franzwermuth": FranzWermuthFetcher(),
}


def get(provider):
    return FETCHERS[provider]
