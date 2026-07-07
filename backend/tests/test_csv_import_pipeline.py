import datetime

from sqlalchemy import select

from app.models import Account, Institution, Transaction
from app.services.csv_import_pipeline import (
    import_assets_folder,
    import_transactions_folder,
    run_daily_import,
)

_TXN_HEADER = "計算対象,日付,内容,金額（円）,保有金融機関,大項目,中項目,メモ,振替,ID\n"
_ASSET_HEADER = "日付,保有金融機関,銘柄,評価額（円）,取得金額（円）\n"


def _bank_institution_id(session) -> int:
    return session.execute(
        select(Institution.id).where(Institution.institution_name == "楽天銀行")
    ).scalar_one()


def _securities_institution_id(session) -> int:
    return session.execute(
        select(Institution.id).where(Institution.institution_name == "楽天証券")
    ).scalar_one()


def _make_bank_account(session, name: str, mf_name: str | None = None) -> Account:
    account = Account(
        institution_id=_bank_institution_id(session),
        account_name=name,
        account_type="bank",
        default_business_ratio=0,
        tracks_balance=True,
        balance_method="cumulative",
        opening_balance=0,
        opening_balance_date=datetime.date(2026, 1, 1),
        moneyforward_account_name=mf_name or name,
    )
    session.add(account)
    session.flush()
    return account


def test_import_transactions_folder_inserts_and_flags_unresolved(db_session, tmp_path):
    account = _make_bank_account(db_session, "パイプライン口座A")

    folder = tmp_path / "transactions"
    folder.mkdir()
    csv_text = (
        _TXN_HEADER
        + f"1,2026/07/01,スーパー,-1000,{account.account_name},食費,,,0,pipe-001\n"
        + "1,2026/07/01,謎の引落,-2000,不明銀行,,,,0,pipe-002\n"
    )
    (folder / "transactions.csv").write_text(csv_text, encoding="utf-8-sig")

    summary = import_transactions_folder(db_session, folder, datetime.date(2026, 7, 8))
    db_session.flush()

    assert summary.files_processed == 1
    assert summary.new_transaction_count == 2
    assert summary.duplicate_skipped_count == 0
    assert "不明銀行" in summary.unresolved_institution_labels
    assert not (folder / "transactions.csv").exists()
    assert (folder / "processed" / "2026-07-08" / "transactions.csv").exists()

    resolved_txn = db_session.execute(
        select(Transaction).where(Transaction.source_hash.isnot(None), Transaction.account_id == account.id)
    ).scalar_one()
    assert resolved_txn.account_id == account.id

    unresolved_txn = db_session.execute(
        select(Transaction).where(Transaction.description == "謎の引落")
    ).scalar_one()
    assert unresolved_txn.account_id is None


def test_import_transactions_folder_skips_duplicate_across_runs(db_session, tmp_path):
    account = _make_bank_account(db_session, "パイプライン口座B")

    folder = tmp_path / "transactions"
    folder.mkdir()
    row = f"1,2026/07/01,家賃,-80000,{account.account_name},住居費,,,0,pipe-dup\n"

    (folder / "first.csv").write_text(_TXN_HEADER + row, encoding="utf-8-sig")
    summary1 = import_transactions_folder(db_session, folder, datetime.date(2026, 7, 8))
    db_session.flush()
    assert summary1.new_transaction_count == 1

    (folder / "second.csv").write_text(_TXN_HEADER + row, encoding="utf-8-sig")
    summary2 = import_transactions_folder(db_session, folder, datetime.date(2026, 7, 8))

    assert summary2.new_transaction_count == 0
    assert summary2.duplicate_skipped_count == 1


def test_import_transactions_folder_with_no_files_is_a_noop(db_session, tmp_path):
    folder = tmp_path / "transactions_empty"
    folder.mkdir()

    summary = import_transactions_folder(db_session, folder, datetime.date(2026, 7, 8))

    assert summary.files_processed == 0
    assert summary.new_transaction_count == 0


def test_import_assets_folder_writes_securities_snapshot(db_session, tmp_path):
    account = Account(
        institution_id=_securities_institution_id(db_session),
        account_name="パイプライン証券口座",
        account_type="securities",
        default_business_ratio=0,
        tracks_balance=True,
        balance_method="moneyforward",
        moneyforward_account_name="パイプライン証券口座",
    )
    db_session.add(account)
    db_session.flush()

    folder = tmp_path / "assets"
    folder.mkdir()
    csv_text = _ASSET_HEADER + f"2026/07/01,{account.account_name},トヨタ自動車,300000,250000\n"
    (folder / "assets.csv").write_text(csv_text, encoding="utf-8-sig")

    summary = import_assets_folder(db_session, folder, datetime.date(2026, 7, 8))

    assert summary.asset_snapshot_count == 1
    assert summary.files_processed == 1


def test_run_daily_import_links_transfer_between_two_cumulative_accounts(db_session, tmp_path, monkeypatch):
    account_a = _make_bank_account(db_session, "日次パイプライン口座A")
    account_b = _make_bank_account(db_session, "日次パイプライン口座B")

    txn_folder = tmp_path / "transactions"
    txn_folder.mkdir()
    asset_folder = tmp_path / "assets"
    asset_folder.mkdir()

    csv_text = (
        _TXN_HEADER
        + f"1,2026/07/08,{account_b.account_name}への振替,-5000,{account_a.account_name},,,,0,daily-1\n"
        + f"1,2026/07/08,振込入金,5000,{account_b.account_name},,,,0,daily-2\n"
    )
    (txn_folder / "transactions.csv").write_text(csv_text, encoding="utf-8-sig")

    from app.core import config as config_module

    monkeypatch.setattr(config_module.settings, "import_transactions_dir", str(txn_folder))
    monkeypatch.setattr(config_module.settings, "import_assets_dir", str(asset_folder))

    summary = run_daily_import(db_session, as_of=datetime.date(2026, 7, 8))

    assert summary.new_transaction_count == 2
    assert summary.transfer_detected_count == 1
    assert summary.asset_snapshot_count >= 2  # 累積口座2件分の残高スナップショット
