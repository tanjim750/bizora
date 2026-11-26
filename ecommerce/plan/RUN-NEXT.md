# RUN-NEXT — do the next card (one card per conversation)

The owner starts each new Antigravity conversation, opened on the folder `ecommerce/`, with this one line:
`Open plan/RUN-NEXT.md, read it completely, and do exactly what it says.`
(To force a specific card: `Open plan/RUN-NEXT.md, read it completely, and do exactly what it says, for card SF-07 only.`)

Everything below is the owner's instruction to you.

1. Read `plan/PROTOCOL.md` completely. It is binding. Nothing in this file overrides it.
2. Run `git branch --show-current` (must print `storefront`; otherwise STOP and tell the owner — never switch branches) and `git status --short -- frontend` (must print nothing; otherwise STOP and list it).
3. Print `plan/ORDER.md` and `plan/LEDGER.md`. Your card is: the card the owner named, or else the FIRST card in the ORDER table (top to bottom, ignoring `IMG-01` unless the owner named it) that has no row in the ledger. Print: `CARD: <ID> — <title>`.
4. If any card in its "Depends on" column lacks a `DONE` row, do not write code: append a `BLOCKED` row ("depends on <ID>") and report in the protocol's S8 format.
5. Read `plan/cards/<ID>.md` completely, then the plan sections it lists under "Read".
6. Do the protocol's steps S0 to S8 for this one card: tests first and red, build, all gates, self-audit, ONE local commit with the card's exact message (no co-author, no AI wording), the ledger row, the report.
7. Stop. Do not start the next card. Do not push, merge, rebase, open a pull request or switch branch. Your last line is `NEXT CARD: <ID>` (the next card in ORDER without a ledger row).
