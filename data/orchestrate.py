"""Monthly ingest orchestrator: fetch -> parse -> archive for build_db.

Ties the ``ingest`` fetchers to the ``data`` pipeline: a house's fetcher
downloads new auctions (JSON or binary XLSX/PDF), file-based results are
parsed into the ``{auction, lots}`` shape, and everything is written into the
``ARCHIVE`` tree that ``build_db.py`` reads.
"""
import json
import os
import tempfile

from parse_results import parse_hdh_pdf, parse_weinauktionator_xlsx

# Provider -> parser for file-based fetchers (binary -> auction+lot JSON).
FILE_PARSERS = {
    "weinauktionator": (".xlsx", parse_weinauktionator_xlsx),
    "hdh": (".pdf", parse_hdh_pdf),
}


def run_provider(provider, session, manifest_path, archive_path, env=None):
    """Fetch, parse and archive all new auctions of ``provider``.

    Returns the number of newly fetched auctions. ``env`` is a dict of login
    credentials; fetchers with an ``auth`` method are logged in first.
    """
    # Lazy import: ingest lives at the repo root, not under data/.
    from ingest.fetchers import get as get_fetcher
    from ingest.registry import (dedup, load_manifest, mark_fetched,
                                 save_manifest, set_last_run)

    manifest = load_manifest(manifest_path)
    fetcher = get_fetcher(provider)
    if env and hasattr(fetcher, "auth"):
        fetcher.auth(session, env)
    new_refs = dedup(fetcher.discover(session), manifest, provider)

    fetched = 0
    for ref in new_refs:
        result = fetcher.fetch(session, ref)
        if result.content:
            _store_parsed(provider, result, archive_path)
        else:
            _store_json(provider, result, archive_path)
        mark_fetched(manifest, ref)
        fetched += 1

    set_last_run(manifest, provider)
    save_manifest(manifest_path, manifest)
    return fetched


def _store_parsed(provider, result, archive_path):
    parser = FILE_PARSERS.get(provider)
    if parser is None:
        _store_binary(provider, result, archive_path)
        return
    suffix, parse = parser
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, f"input{suffix}")
        with open(src, "wb") as fh:
            fh.write(result.content)
        parsed = parse(src)
    _write_json(archive_path, provider, _filename(result, parsed), parsed)


def _store_json(provider, result, archive_path):
    _write_json(archive_path, provider,
                f"{result.auction_id}.json", result.data)


def _store_binary(provider, result, archive_path):
    os.makedirs(os.path.join(archive_path, provider), exist_ok=True)
    with open(os.path.join(archive_path, provider,
                           result.filename or result.auction_id),
              "wb") as fh:
        fh.write(result.content)


def _filename(result, parsed):
    auction = parsed.get("auction", {})
    if result.provider == "hdh":
        sale = auction.get("sale_number") or result.auction_id
        return f"{sale}.json"
    if result.provider == "weinauktionator":
        return f"weinauktionator_results_{result.auction_id}.json"
    return f"{result.auction_id}.json"


def _write_json(archive_path, provider, filename, data):
    directory = os.path.join(archive_path, provider)
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, filename), "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, default=str)
