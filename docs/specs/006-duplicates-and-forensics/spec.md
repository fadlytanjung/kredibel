# Spec 006 — Duplicates and Document Forensics

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 · P1 (`A03`, `A05`, `M05`, revision diff, visual forensics in spec 015) |
| **Owner role** | B: Risk engine |
| **Depends on** | 005 |
| **Requirements** | FR-012, FR-023, NFR-04, P0-03, P0-07 |
| **Design** | [`docs/08`](../../08-risk-engine.md) §1–§3; [`docs/07`](../../07-document-intelligence.md) §3.3, §6.5; `contracts/policy/forensics.v1.yaml` |

## Summary

After reading, each document is checked for **content duplicates** (the same statement period, the
same invoice, the same receipt, the same ledger line uploaded again in another file) and for
**integrity** (arithmetic, PDF structure and fonts). Possible duplicates are **held**: their values do
not count until a person decides. Every finding has evidence; each document gets a verdict.

## User stories

### US-006-1: Content duplicates are held, not counted

- **AC-006-1** `D02` when a statement has the same account (bank + last 4 digits) as another and the
  periods overlap by ≥ 1 day: HIGH if the overlapping rows differ, MEDIUM if identical. Adjacent
  periods (31 Jan / 1 Feb) are not duplicates.
- **AC-006-2** `D03` for the same issuer (`token_set_ratio ≥ 90`) and invoice number, or the same
  issuer, issue date and total; `D04` (HIGH, both kept) for the same issuer and number with a different
  total or date.
- **AC-006-3** `D05` for the same merchant, date and total (± 1 unit), or a page-1 perceptual hash
  within distance 8.
- **AC-006-4** `D06` for two ledger entries with the same date, amount, account and reference, within
  one file or across files.
- **AC-006-5** The **newer** document (or entry) gets `duplicate {kind: CONTENT, code, ofDocId,
  decision: PENDING}` and `heldAsDuplicate: true` on it and all its records; held values are excluded
  from month figures, matching and the money flow; a `POSSIBLE_DUPLICATE` review item is created; the
  library shows "Possible copy of …".
- **AC-006-6** Deciding "duplicate" keeps the values excluded (`CONFIRMED`); "not a duplicate"
  (`REJECTED`) releases them; both mark the months dirty (resolution UI in spec 009).

### US-006-2: Integrity checks with evidence

- **AC-006-7** `A01` running balance, `A02` opening/closing, `A04` invoice and receipt arithmetic, as
  in [`docs/08`](../../08-risk-engine.md) §2.3; CRITICAL only when every value is `AGREED` and no
  witness-only row lies between; otherwise `E01`-level uncertainty (P6).
- **AC-006-8** `M01`, `M02`, `M03` (detect revisions), `M04`, `M06` from the inspection of the
  original file ([`docs/08`](../../08-risk-engine.md) §2.4).
- **AC-006-9** `E01`, `E02`, `E03`, `E05` from reading; `X05` and `X06` per statement against the
  workspace's names and accounts (the rest of the cross-document checks are month checks, spec 007).
- **AC-006-10** Every finding has the shape of [`docs/08`](../../08-risk-engine.md) §1 with facts and
  evidence references (document, page, box, record); IDs are deterministic; a re-run resolves findings
  that no longer apply and keeps `ACKNOWLEDGED`/`DISMISSED` ones.
- **AC-006-11** Each statement, invoice and receipt gets an integrity verdict (`CLEAN`, `SUSPICIOUS`,
  `TAMPERED`, `UNVERIFIABLE`) by [`docs/08`](../../08-risk-engine.md) §3; ledger exports get none.

### US-006-3: Scenario outcomes

- **AC-006-12** S2's March statement is `TAMPERED` with `A01` at the edited row, `A02`, `M01`, `M02`,
  `M03`, `M04`; S1's documents are all `CLEAN`.
- **AC-006-13** S3's four content duplicates are held with the expected codes, and S3's month figures
  equal S1's.

## Out of scope

`D07` double payment and month-level checks (007), risk levels (008), resolution UI (009), Model
Armor, visual forensics and revision diff (015).
