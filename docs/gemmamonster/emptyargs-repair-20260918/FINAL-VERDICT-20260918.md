# C5 STATUS (frozen verdict, 2026-09-18)

Whitespace regression:
CONFIRMED FIXED

Empty-args regression:
NOT REPRODUCED
267 subsequent canonical calls produced filled required arguments.

Attribution:
A parser               EXONERATED
B schema ingestion     EXONERATED
C grammar semantics    EXONERATED
D live sampling        UNRESOLVED
E persistent model defect NOT ESTABLISHED

F3:
ISOLATED NON-REPRODUCED RUNTIME ANOMALY
EVIDENCE-ONLY
NOT A BASIS FOR PRODUCT CHANGES

F1-F5:
VALID HARDENING / API WORK
NOT CLAIMED AS REPAIR OF A REPRODUCIBLE EMPTY-ARGS BUG

F4:
IMPLEMENTED/EXPERIMENTAL
LIVE PROMOTION DEFERRED

NEXT:
C6 forward-port on fresh upstream bases,
carrying the confirmed whitespace fix and
independently justified hardening only.
