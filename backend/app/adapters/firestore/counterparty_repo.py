"""CounterpartyRepository on Firestore (docs/09 §3.13)."""

from datetime import date
from decimal import Decimal

from google.cloud.firestore import AsyncClient, FieldFilter

from app.adapters.firestore.models.counterparty import CounterpartyDoc
from app.adapters.firestore.txn import dump
from app.domain.counterparties import AccountSeen, Counterparty, MonthTotals, fold_name
from app.ports.counterparty_repository import CounterpartyRepository

_BATCH = 400


def _to_doc(c: Counterparty) -> CounterpartyDoc:
    return CounterpartyDoc(
        counterparty_id=c.counterparty_id,
        name=c.name,
        aliases=list(c.aliases),
        kind=c.kind,
        roles=list(c.roles),
        totals_by_month={
            month: {
                "inMinor": int(t.in_amount * 100),
                "outMinor": int(t.out_amount * 100),
                "count": t.count,
            }
            for month, t in c.totals_by_month.items()
        },
        accounts_seen=[
            {
                "accountMasked": a.account_masked,
                "firstSeen": a.first_seen.isoformat(),
                "lastSeen": a.last_seen.isoformat(),
            }
            for a in c.accounts_seen
        ],
        open_invoices=c.open_invoices,
        first_date=c.first_date.isoformat() if c.first_date else None,
        last_date=c.last_date.isoformat() if c.last_date else None,
        sample_evidence=list(c.sample_evidence),
        bank_line_ids=list(c.bank_line_ids),
        invoice_ids=list(c.invoice_ids),
        receipt_ids=list(c.receipt_ids),
        bucket=c.bucket,
        name_fold=fold_name(c.name),
    )


def _to_domain(d: CounterpartyDoc) -> Counterparty:
    return Counterparty(
        counterparty_id=d.counterparty_id,
        name=d.name,
        aliases=tuple(d.aliases),
        kind=d.kind,  # type: ignore[arg-type]
        roles=tuple(d.roles),  # type: ignore[arg-type]
        totals_by_month={
            month: MonthTotals(
                Decimal(t.get("inMinor", 0)) / 100,
                Decimal(t.get("outMinor", 0)) / 100,
                int(t.get("count", 0)),
            )
            for month, t in sorted(d.totals_by_month.items())
        },
        accounts_seen=tuple(
            AccountSeen(
                a["accountMasked"],
                date.fromisoformat(a["firstSeen"]),
                date.fromisoformat(a["lastSeen"]),
            )
            for a in d.accounts_seen
        ),
        open_invoices=d.open_invoices,
        first_date=date.fromisoformat(d.first_date) if d.first_date else None,
        last_date=date.fromisoformat(d.last_date) if d.last_date else None,
        sample_evidence=tuple(d.sample_evidence),
        bank_line_ids=tuple(d.bank_line_ids),
        invoice_ids=tuple(d.invoice_ids),
        receipt_ids=tuple(d.receipt_ids),
        bucket=d.bucket,
    )


class FirestoreCounterpartyRepository(CounterpartyRepository):
    def __init__(self, db: AsyncClient) -> None:
        self._db = db

    def _col(self, org_id: str):
        return self._db.collection("orgs").document(org_id).collection("counterparties")

    async def replace_all(self, org_id: str, parties: list[Counterparty]) -> None:
        keep = {p.counterparty_id for p in parties}
        stale = [s.id async for s in self._col(org_id).select([]).stream() if s.id not in keep]
        items = [("set", p) for p in parties]
        for start in range(0, len(items), _BATCH):
            batch = self._db.batch()
            for _, p in items[start : start + _BATCH]:
                batch.set(self._col(org_id).document(p.counterparty_id), dump(_to_doc(p)))
            await batch.commit()
        for start in range(0, len(stale), _BATCH):
            batch = self._db.batch()
            for doc_id in stale[start : start + _BATCH]:
                batch.delete(self._col(org_id).document(doc_id))
            await batch.commit()

    async def list_counterparties(
        self,
        org_id: str,
        *,
        role: str | None = None,
        q: str | None = None,
        limit: int = 200,
        cursor: str | None = None,
    ) -> tuple[list[Counterparty], str | None]:
        query = self._col(org_id)
        if role:
            query = query.where(filter=FieldFilter("roles", "array_contains", role))
        found = [
            _to_domain(CounterpartyDoc.model_validate(s.to_dict()))
            async for s in query.limit(2000).stream()
        ]
        needle = fold_name(q) if q else ""
        if needle:
            found = [
                c
                for c in found
                if needle in fold_name(c.name) or any(needle in fold_name(a) for a in c.aliases)
            ]
        found.sort(key=lambda c: (c.name.casefold(), c.counterparty_id))
        start = 0
        if cursor:
            ids = [c.counterparty_id for c in found]
            start = ids.index(cursor) + 1 if cursor in ids else 0
        page = found[start : start + limit]
        more = page[-1].counterparty_id if len(found) > start + limit and page else None
        return page, more

    async def get(self, org_id: str, counterparty_id: str) -> Counterparty | None:
        snap = await self._col(org_id).document(counterparty_id).get()
        return _to_domain(CounterpartyDoc.model_validate(snap.to_dict())) if snap.exists else None
