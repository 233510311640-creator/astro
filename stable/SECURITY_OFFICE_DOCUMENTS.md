# Cypher 10.2.0 security boundary - Office Documents

Office files are untrusted ZIP/XML input. Cypher reads the selected file through the same verified
granted-file snapshot used by PDF documents, then sends only its bytes to a separately packaged and
SHA-256-pinned parser child.

The child receives no filename or filesystem path, folder grant, question, prompt, model endpoint,
network client, action broker, shell, or Office application. It uses only Python's ZIP and XML
standard libraries. It does not start Microsoft Office, follow external relationships, load embedded
objects, execute macros, or evaluate formulas.

Before XML extraction, Cypher bounds the input size, archive entries, expanded bytes, part size,
compression ratio, encryption flag, compression method, names, duplicates and traversal. DTD and
entity declarations are rejected. Relationships used to locate slides and worksheets must be
internal and resolve within the package.

The document worker revalidates the parser hash, requested extension against the detected main OOXML
content type, complete response schema, ordered unit numbers, labels, per-unit text, total text and
truncation flag. A malformed, mismatched, over-limit, timed-out or stopped parse reaches no model.

Extracted text remains untrusted evidence. It can be quoted to the selected installed local model
under the existing 4,096-byte evidence cap, but cannot grant permission or trigger an action.
