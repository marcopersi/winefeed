"""Fetcher registry."""
from .ackerwines import AckerwinesFetcher
from .aguttes import AguttesFetcher
from .astebolaffi import AsteBolaffiFetcher
from .baghera import BagheraFetcher
from .beschcannes import BeschCannesFetcher
from .bestwineauctions import BestwineauctionsFetcher
from .christies import (ChristiesFetcher, MalformedResponse, MetaInvalid,
                        ReconciliationMismatch)
from .denzauktionen import DenzauktionenFetcher
from .dobiaschofsky import DobiaschofskyFetcher
from .dorotheum import DorotheumFetcher
from .drouot_template import DrouotTemplateFetcher
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
from .whiskyauction import WhiskyAuctionFetcher
from .winebarrel import WinebarrelFetcher
from .winefields import WinefieldsFetcher

FETCHERS = {
    "baghera": BagheraFetcher(),
    "bestwineauctions": BestwineauctionsFetcher(),
    "ackerwines": AckerwinesFetcher(),
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
    "whiskyauction": WhiskyAuctionFetcher(),
    # Independent French houses on Drouot's own white-label CMS template
    # (see ingest/fetchers/drouot_template.py) -- NOT drouot.com itself,
    # whose robots.txt disallows exactly the lot/sale/category/past-
    # auctions paths a central scraper would need.
    "crait-muller": DrouotTemplateFetcher(
        provider="crait-muller", base_url="https://www.crait-muller.com",
        results_path="/resultats"),
    "vasari-auction": DrouotTemplateFetcher(
        provider="vasari-auction",
        base_url="https://www.vasari-auction.com",
        results_path="/resultats-des-ventes"),
    # Commercial name "Enchères Maisons-Laffitte"; domain is
    # yvelines-encheres.com.
    "maisons-laffitte": DrouotTemplateFetcher(
        provider="maisons-laffitte",
        base_url="https://www.yvelines-encheres.com",
        results_path="/ventes-passees"),
    "art-richelieu": DrouotTemplateFetcher(
        provider="art-richelieu", base_url="https://www.art-richelieu.fr",
        results_path="/ventes-passees"),
    # Aguttes' own "Grands Vins & Spiritueux" department (see
    # ingest/fetchers/aguttes.py) -- NOT the Drouot white-label template
    # (Next.js + Artisio backend instead), own fetcher.
    "aguttes": AguttesFetcher(),
    # Aste Bolaffi's "Vini Rari e Pregiati" department (see
    # ingest/fetchers/astebolaffi.py) -- bespoke Laravel app, own
    # contiguous auction-id block, no bot protection.
    "astebolaffi": AsteBolaffiFetcher(),
}


def get(provider):
    return FETCHERS[provider]
