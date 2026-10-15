"""A statement's bank account (docs/09 §3.5). Synthetic."""

from app.domain.accounts import statement_account


def test_a_statement_account_is_one_account_however_the_bank_was_printed():
    """The synthetic run read "Archipelago Commerce Bank\\nBandung Dago Branch" on some statements
    and "Archipelago Commerce Bank" on others: one account, not two (each "missing" a month)."""
    plain = statement_account("Archipelago Commerce Bank", "••••4821")
    assert plain == "Archipelago Commerce Bank ••••4821"
    assert statement_account("Archipelago Commerce Bank\nBandung Dago Branch", "••••4821") == plain
    assert statement_account("  Archipelago   Commerce Bank ", "••••4821") == plain
    assert statement_account("Archipelago Commerce Bank", "••••7310") != plain
    assert statement_account(None, "••••4821") == "••••4821"
    assert statement_account("Archipelago Commerce Bank", None) == "Archipelago Commerce Bank"
