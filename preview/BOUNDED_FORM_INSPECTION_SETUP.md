# Bounded public form inspection

Install Cypher 10.7.0 with `INSTALL_CYPHER_BOUNDED_FORM_INSPECTION.cmd`, then press
Ctrl+Alt+Space. Enter `Web: forms https://example.org/` or use **Inspect Forms** in the
system rail and replace the URL.

Cypher reads one explicit public HTTPS HTML page in isolation and reports at most five
same-host forms with up to eight named non-sensitive fields each. It shows the declared GET
or POST method, eligible HTTPS action and field types/required markers. It never shows input
values, hidden fields, password fields or off-host actions. No filling or submission occurs.

Inspection uses static HTML and limited inline/ARIA hiding checks. External stylesheets,
JavaScript-rendered controls, dynamic validation and actual browser visibility are not
evaluated. The page remains untrusted data. The reader follows existing public-address,
DNS, robots, redirect, content-type, byte and time limits and has no browser profile,
cookies, login, local model, file or Windows action context.
