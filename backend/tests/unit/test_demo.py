"""A demo workspace is a copy of the template (spec 021, AC-021-2): the template's workspace ID
and people are swapped everywhere, other values are kept, and the record's own fields are not
taken over. Synthetic data only."""

from datetime import UTC, datetime

from app.domain.demo import SKIPPED_COLLECTIONS, rewrite, workspace_extras

SWAP = {"org_demo_template": "org_01NEW", "u_template": "u-1"}


def test_ac021_2_ids_paths_and_people_point_inside_the_copy():
    at = datetime(2026, 9, 30, tzinfo=UTC)
    record = {
        "runId": "month-org_demo_template-2026-08-3",
        "gcsPath": "gs://docs/orgs/org_demo_template/documents/doc_1/original.pdf",
        "uploadedBy": "u_template",
        "stages": [{"node": "read_page", "tokensIn": 2100, "at": at}],
        "ledgerMappings": {"lay_6c1f": {"by": "u_template"}},
        "amount": 1250000,
    }
    copied = rewrite(record, SWAP)
    assert copied["runId"] == "month-org_01NEW-2026-08-3"
    assert copied["gcsPath"] == "gs://docs/orgs/org_01NEW/documents/doc_1/original.pdf"
    assert copied["uploadedBy"] == "u-1" and copied["ledgerMappings"]["lay_6c1f"]["by"] == "u-1"
    assert copied["stages"][0] == {"node": "read_page", "tokensIn": 2100, "at": at}
    assert copied["amount"] == 1250000 and record["uploadedBy"] == "u_template", "input unchanged"


def test_ac021_2_people_history_conversations_and_usage_stay_with_the_template():
    assert {"members", "invites", "events", "assistantThreads", "usage", "usageMonthly"} == set(
        SKIPPED_COLLECTIONS
    )
    extras = workspace_extras(
        {
            "orgId": "org_demo_template",
            "name": "Sunrise Coffee Roasters",
            "subscription": {"planId": "free_trial", "limitOverrides": {"documentsPerMonth": 600}},
            "createdBy": "u_template",
            "counts": {"documents": 78},
            "ledgerMappings": {"lay_6c1f": {"date": "Date"}},
            "learning": {"shareVerifiedLabels": False},
        },
        SWAP,
    )
    assert extras == {
        "counts": {"documents": 78},
        "ledgerMappings": {"lay_6c1f": {"date": "Date"}},
        "learning": {"shareVerifiedLabels": False},
    }, "the demo limits of the template never reach a copy"
