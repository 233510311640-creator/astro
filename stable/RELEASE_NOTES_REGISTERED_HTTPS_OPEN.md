# Cypher 10.1.1 release notes - Registered HTTPS Open

## Fixed

`open brave then search chess.com` previously missed every deterministic Windows route. The generic
launch parser treated the complete phrase as an application name, failed to resolve it, and allowed
the request to reach general chat. The model then truthfully refused a capability that the native
host should have handled.

10.1.1 adds a higher-priority deterministic parser for one registered application plus one public
HTTPS domain or URL. It normalizes a bare domain, rejects invalid destinations, resolves the exact
human-managed app record, and presents one native approval before execution.

## Verification boundary

The approval fingerprint includes the action kind, app ID/name, executable path, executable length,
timestamp and SHA-256, normalized URL length and SHA-256, selection policy and expiry. Execution
revalidates these values and invokes the executable directly with one quoted argument and no shell.

Cypher reports delivery only after Windows accepted the invocation and a matching registered-app
window or live process was observed. It does not inspect the address bar, page contents or network,
so it does not claim that the destination loaded.

## Retained

The 10.1.0 PDF document features and all earlier file, research, runtime, workflow, approval, Stop,
recovery and Monochrome Signal behavior remain unchanged.
