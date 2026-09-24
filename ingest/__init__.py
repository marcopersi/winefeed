"""Periodic auction-data ingest.

Fetches the newest auctions from each house, deduplicates against a persisted
manifest, and stores the raw data for the existing `data/` pipeline.
"""
