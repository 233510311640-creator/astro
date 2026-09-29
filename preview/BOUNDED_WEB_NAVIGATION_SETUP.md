# Cypher 10.5.0 — Bounded Public Page Navigation

This release adds a safe first navigation step to the monochrome command center.

Use:

```text
Web: links https://example.org/
```

Cypher reads exactly one public HTTPS page through the isolated worker and lists at most six visible,
eligible same-site navigation links. It does not open those links, use browser cookies, run page scripts, submit
forms, click controls, start downloads, call a model, or modify a file.

To open a result, copy its displayed command, for example:

```text
Open Brave then visit https://example.org/more
```

That second request uses the existing browser executable checks and one-time native approval. The
approval shows the exact browser and destination before anything opens.

The link map excludes off-site and hidden anchors, form links, duplicate destinations, page fragments, non-HTTPS
schemes, local/private targets, credential-like or signed query URLs, and common download-file targets.
The linked destination is not fetched or verified until you explicitly request another read or map.

Run `INSTALL_CYPHER_BOUNDED_WEB_NAVIGATION.cmd` as the signed-in standard Windows user. Keep the
complete 10.4.0 release as the rollback package.
