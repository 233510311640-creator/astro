# Release notes — Cypher 10.2.2 Bounded Browser Search

- Adds deterministic natural-language browser search before model routing.
- Supports both `Search the web for QUERY in BROWSER` and `Open BROWSER then search QUERY` forms.
- Uses one fixed provider and origin: `https://duckduckgo.com/`.
- Preserves direct opening for valid public domains and HTTPS URLs.
- Binds the normalized query, query hash, provider, generated destination, destination hash, exact browser executable, executable metadata/hash, and 60-second expiry into one approval fingerprint.
- Rebuilds and compares the search destination immediately before execution.
- Uses direct process launch with one quoted HTTPS argument and shell execution disabled.
- Does not inspect results, page contents, the address bar, cookies, saved passwords, or browser profile data.
