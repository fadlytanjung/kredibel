"""UsageRepository on Firestore: decide and count in one transaction (AC-013-9, AC-013-10)."""

from collections.abc import Sequence
from decimal import Decimal

from google.cloud.firestore import AsyncClient, AsyncTransaction, async_transactional
from google.cloud.firestore_v1.async_document import AsyncDocumentReference

from app.adapters.firestore.models.workspace import OrgDoc, UsageDayDoc, UsageMonthDoc
from app.adapters.firestore.txn import dump, with_backoff
from app.domain.models.workspace import Subscription, UsageDay, UsageMonth
from app.domain.plans import Allowed, Decision
from app.ports.workspace_repository import (
    Decide,
    PendingWrite,
    UsageIncrement,
    UsageRepository,
    UsageSettlement,
)


def _month(doc: UsageMonthDoc) -> UsageMonth:
    return UsageMonth(
        month=doc.month,
        documents_uploaded=doc.documents_uploaded,
        pages_reserved=doc.pages_reserved,
        pages_read=doc.pages_read,
        pages_cached=doc.pages_cached,
        ocr_pages=doc.ocr_pages,
        parser_pages=doc.parser_pages,
        ai_spend_usd=Decimal(doc.ai_spend_usd),
    )


def _day(doc: UsageDayDoc) -> UsageDay:
    return UsageDay(
        day=doc.day, month_runs=doc.month_runs, assistant_questions=doc.assistant_questions
    )


class FirestoreUsageRepository(UsageRepository):
    def __init__(self, client: AsyncClient) -> None:
        self._db = client

    def _refs(
        self, org_id: str, month: str, day: str
    ) -> tuple[AsyncDocumentReference, AsyncDocumentReference, AsyncDocumentReference]:
        org = self._db.collection("orgs").document(org_id)
        return (
            org,
            org.collection("usageMonthly").document(month),
            org.collection("usage").document(day),
        )

    async def meter(
        self,
        org_id: str,
        *,
        month: str,
        day: str,
        decide: Decide,
        increment: UsageIncrement,
        writes: Sequence[PendingWrite] = (),
    ) -> tuple[Decision, Subscription]:
        org_ref, month_ref, day_ref = self._refs(org_id, month, day)

        @async_transactional
        async def run(txn: AsyncTransaction) -> tuple[Decision, Subscription]:
            org_snap = await org_ref.get(transaction=txn)
            month_snap = await month_ref.get(transaction=txn)
            day_snap = await day_ref.get(transaction=txn)
            sub = Subscription.model_validate(
                OrgDoc.model_validate(org_snap.to_dict()).subscription
            )
            month_doc = UsageMonthDoc.model_validate(
                month_snap.to_dict() or {"orgId": org_id, "month": month}
            )
            day_doc = UsageDayDoc.model_validate(
                day_snap.to_dict() or {"orgId": org_id, "day": day}
            )

            decision = decide(sub, _month(month_doc), _day(day_doc))
            if not isinstance(decision, Allowed):
                return decision, sub

            if increment.documents_uploaded or increment.pages_reserved:
                txn.set(
                    month_ref,
                    dump(
                        month_doc.model_copy(
                            update={
                                "documents_uploaded": month_doc.documents_uploaded
                                + increment.documents_uploaded,
                                "pages_reserved": month_doc.pages_reserved
                                + increment.pages_reserved,
                            }
                        )
                    ),
                )
            if increment.month_runs or increment.assistant_questions:
                txn.set(
                    day_ref,
                    dump(
                        day_doc.model_copy(
                            update={
                                "month_runs": day_doc.month_runs + increment.month_runs,
                                "assistant_questions": day_doc.assistant_questions
                                + increment.assistant_questions,
                            }
                        )
                    ),
                )
            for write in writes:
                txn.set(self._db.document(write.path), write.data)
            return decision, sub

        return await with_backoff(lambda: run(self._db.transaction(max_attempts=1)))

    async def settle(self, org_id: str, settlement: UsageSettlement) -> None:
        month_ref = self._refs(org_id, settlement.month, "")[1]

        @async_transactional
        async def run(txn: AsyncTransaction) -> None:
            snap = await month_ref.get(transaction=txn)
            doc = UsageMonthDoc.model_validate(
                snap.to_dict() or {"orgId": org_id, "month": settlement.month}
            )
            spend = Decimal(doc.ai_spend_usd) + settlement.ai_spend_usd
            txn.set(
                month_ref,
                dump(
                    doc.model_copy(
                        update={
                            # Counted pages become the pages actually read (AC-013-10).
                            "pages_reserved": doc.pages_reserved
                            + settlement.pages_read
                            - settlement.pages_reserved,
                            "pages_read": doc.pages_read + settlement.pages_read,
                            "pages_cached": doc.pages_cached + settlement.pages_cached,
                            "ocr_pages": doc.ocr_pages + settlement.ocr_pages,
                            "parser_pages": doc.parser_pages + settlement.parser_pages,
                            "ai_spend_usd": str(spend),
                        }
                    )
                ),
            )

        await with_backoff(lambda: run(self._db.transaction(max_attempts=1)))

    async def get_usage(self, org_id: str, *, month: str, day: str) -> tuple[UsageMonth, UsageDay]:
        _, month_ref, day_ref = self._refs(org_id, month, day)
        month_snap = await month_ref.get()
        day_snap = await day_ref.get()
        return (
            _month(
                UsageMonthDoc.model_validate(
                    month_snap.to_dict() or {"orgId": org_id, "month": month}
                )
            ),
            _day(UsageDayDoc.model_validate(day_snap.to_dict() or {"orgId": org_id, "day": day})),
        )
