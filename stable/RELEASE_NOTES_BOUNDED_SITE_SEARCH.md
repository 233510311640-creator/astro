# Cypher 10.8.0 — Bounded Public Site Search

`Web: search PUBLIC-HTTPS-URL : QUERY` checks one public page for a single eligible
same-site GET search destination and field, then attempts one query request and returns
exact bounded excerpts from the fetched page. Duplicate identical search boxes are
deduplicated; different actions or fields remain ambiguous and reject. The command
center adds a Site Search starter.

This is isolated public-page search, not interactive browser automation. It does not
render JavaScript results or fill a browser form. Cypher 10.7.0 remains available for
rollback.
