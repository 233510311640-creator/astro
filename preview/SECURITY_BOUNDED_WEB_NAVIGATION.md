# Security boundary — Bounded Public Page Navigation

The page map is observation only. The isolated research worker receives one explicit public HTTPS URL,
performs the same fail-closed network checks used by `Web: read`, parses bounded HTML, and returns at most
six visible same-site anchor labels with canonical destinations. Off-site anchors are excluded before output.

External HTML, labels and URLs are untrusted data. They cannot approve an action or become model/tool
instructions. The mapper does not use a model, browser profile, cookie store, login state, script engine,
form engine, file writer, Windows action, shell, clipboard or raw input.

Opening is a separate human command. The existing browser action re-resolves a supported fixed-path or
registered browser, hashes its executable, binds the exact public HTTPS destination into a 60-second
one-time approval, revalidates it, and launches without a shell. Mapping never grants that approval.

This release is not authenticated browsing, general browser automation, DOM scripting, purchasing,
posting, uploading, downloading, or multi-step unattended navigation.
