# LEDGER — one row per card (the agent appends; never edits other rows)

A card with ANY row here is skipped by `RUN-NEXT.md`. To re-run a `BLOCKED` card, the owner deletes its row (and its undone work is already gone). Status: `DONE` or `BLOCKED`.

| Card | Status | Commit | Test file | Red (tail, one line) | Green (tail, one line) | Gates |
|---|---|---|---|---|---|---|
| SF-01 | DONE | 0d17524 | tests/unit/sf-01-setup.test.ts | Tests 3 failed \| 1 passed (4) | Tests 4 passed (4) in 1.92s | test=pass typecheck=pass lint=pass format=pass build=pass |
| SF-02 | DONE | f017aa4 | tests/unit/sf-02-tokens.test.ts | Tests 2 failed \| 1 passed (3) | Tests 9 passed (9) in 4.01s | test=pass typecheck=pass lint=pass format=pass build=pass |
| SF-03 | DONE | ce69c1b | tests/unit/sf-03-motion.test.tsx | Failed to resolve import @/lib/motion/tokens (1 failed) | Tests 16 passed (16) in 2.16s | test=pass typecheck=pass lint=pass format=pass build=pass |
| SF-04 | DONE | 8fb5617 | tests/unit/sf-04-ui.test.tsx | Failed to resolve import @/lib/cn (1 failed) | Tests 31 passed (31) in 8.73s | test=pass typecheck=pass lint=pass format=pass build=pass |
| SF-05 | DONE | 32fc6bd | tests/unit/sf-05-contract.test.ts | Failed to resolve import @/lib/api/schemas (1 failed) | Tests 59 passed (59) in 6.88s | test=pass typecheck=pass lint=pass format=pass build=pass |
| SF-06 | DONE | 274c54e | tests/unit/sf-06-fixtures.test.ts | Failed to resolve import @/mocks/fixtures/store.json (1 failed) | Tests 73 passed (73) in 7.41s | test=pass typecheck=pass lint=pass format=pass build=pass |
| SF-07 | DONE | 22ab627 | tests/unit/sf-07-mock-catalog.test.ts | Failed to resolve import @/mocks/server/db (1 failed) | Tests 90 passed (90) in 4.43s | test=pass typecheck=pass lint=pass format=pass build=pass |
| SF-08 | DONE | df25f06 | tests/unit/sf-08-mock-stateful.test.ts | Failed to resolve import @/app/api/store/[...path]/route (1 failed) | Tests 109 passed (109) in 4.40s | test=pass typecheck=pass lint=pass format=pass build=pass |
| SF-09 | DONE | c96dc0b | tests/unit/sf-09-data-layer.test.ts | Failed to resolve import @/lib/api/transport-http (1 failed) | Tests 130 passed (130) in 4.95s | test=pass typecheck=pass lint=pass format=pass build=pass |
| SF-10 | DONE | c653e27 | tests/unit/sf-10-stores.test.tsx | Failed to resolve import "@/stores/announce-store" (1 failed) | Tests 147 passed (147) in 4.79s | test=pass typecheck=pass lint=pass format=pass build=pass |
