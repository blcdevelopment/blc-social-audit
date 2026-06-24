"""Phase 2 social-audit data layer (standalone audit type).

- ``extractor`` — pure, deterministic normalization of raw provider payloads into the
  ``social.*`` facts that ``rubrics/social.yaml`` scores.
- ``apify_provider`` — Apify backend (network) for public Instagram profiles.
- ``collector`` — orchestrates provider fetch -> extractor with graceful degradation.
"""
