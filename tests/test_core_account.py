import pytest

from nexus.core.account import Account


def test_account_create_and_realized_pnl() -> None:
    account = Account.create(1000.0)

    assert account.balance == pytest.approx(1000.0)
    assert account.equity == pytest.approx(1000.0)
    assert account.free_margin == pytest.approx(1000.0)

    account.update_margin(100.0)
    assert account.free_margin == pytest.approx(900.0)

    account.apply_realized_pnl(25.0)
    assert account.balance == pytest.approx(1025.0)
    assert account.equity == pytest.approx(1025.0)
    assert account.realized_pnl == pytest.approx(25.0)
    assert account.free_margin == pytest.approx(925.0)
