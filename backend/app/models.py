import datetime
import decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ============================================================
# マスタテーブル群 (m_)
# ============================================================


class Institution(Base):
    __tablename__ = "m_institutions"
    __table_args__ = {"comment": "金融機関マスタ"}

    id: Mapped[int] = mapped_column(primary_key=True, comment="金融機関ID")
    institution_name: Mapped[str] = mapped_column(comment="金融機関名（例: 楽天銀行、三井住友カード）")
    institution_type: Mapped[str] = mapped_column(comment="機関種別（bank/credit_card/securities/qr_payment）")
    card_alert_sender_email: Mapped[str | None] = mapped_column(
        comment="クレジットカード利用速報メールの送信元アドレス（Fromヘッダ。institution_type=credit_cardのみ使用。実メールサンプル確認後に設定）"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), comment="作成日時"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), comment="更新日時"
    )


class Account(Base):
    __tablename__ = "m_accounts"
    __table_args__ = {"comment": "口座マスタ（銀行口座・クレジットカード・証券口座・QR決済アカウント・ローン）"}

    id: Mapped[int] = mapped_column(primary_key=True, comment="口座ID")
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("m_institutions.id"), comment="金融機関ID（m_institutions参照）"
    )
    account_name: Mapped[str] = mapped_column(comment="口座表示名（例: 楽天銀行 個人）")
    account_type: Mapped[str] = mapped_column(
        comment="口座種別（bank/credit_card/securities/qr_payment/loan）"
    )
    is_business: Mapped[bool] = mapped_column(default=False, comment="事業用口座フラグ（口座自体の分類）")
    is_active: Mapped[bool] = mapped_column(
        default=True, comment="有効フラグ（解約・休眠口座はFALSE。自動取込対象からは外れるが過去データは保持）"
    )
    default_business_ratio: Mapped[decimal.Decimal] = mapped_column(
        Numeric(5, 2), default=decimal.Decimal("100.00"),
        comment="当口座で新規作成される取引に適用する事業按分デフォルト率(%)",
    )
    tracks_balance: Mapped[bool] = mapped_column(
        default=False,
        comment="残高追跡対象フラグ（TRUEの口座のみt_asset_snapshotsを持つ。クレカ・都度引き落とし式QR決済はFALSE）",
    )
    balance_method: Mapped[str | None] = mapped_column(
        comment="残高算出方式（cumulative=初期残高+取引累積 / moneyforward=MF連携 / manual=手動入力）"
    )
    opening_balance: Mapped[decimal.Decimal | None] = mapped_column(
        Numeric(12, 2), comment="初期残高（balance_method=cumulativeの口座のみ使用）"
    )
    opening_balance_date: Mapped[datetime.date | None] = mapped_column(
        Date, comment="初期残高の基準日"
    )
    moneyforward_account_name: Mapped[str | None] = mapped_column(
        comment="マネーフォワードME連携時の口座表示名（CSVの「保有金融機関」列とのマッチングに使用。未設定の場合はaccount_nameで照合）"
    )
    card_last4: Mapped[str | None] = mapped_column(
        String(4),
        comment="クレジットカード番号下4桁（account_type=credit_cardのみ使用。利用速報メール本文からの抽出値との整合性検証用）",
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), comment="作成日時"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), comment="更新日時"
    )


class Category(Base):
    __tablename__ = "m_categories"
    __table_args__ = {"comment": "カテゴリマスタ（収入・支出どちらの取引にも使う中立的な分類）"}

    id: Mapped[int] = mapped_column(primary_key=True, comment="カテゴリID")
    category_name: Mapped[str] = mapped_column(
        unique=True, comment="カテゴリ名（例: 食費、交通費、給与、未分類）"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), comment="作成日時"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), comment="更新日時"
    )


class CategoryRule(Base):
    __tablename__ = "m_category_rules"
    __table_args__ = {"comment": "カテゴリ自動分類ルールマスタ（摘要文字列との部分文字列マッチング）"}

    id: Mapped[int] = mapped_column(primary_key=True, comment="ルールID")
    keyword_pattern: Mapped[str] = mapped_column(
        comment="摘要とのマッチングに使うキーワード（部分文字列一致）"
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("m_categories.id"), comment="一致時に適用するカテゴリID（m_categories参照）"
    )
    priority: Mapped[int] = mapped_column(
        default=100, comment="適用優先順位（値が小さいほど優先。最初に一致したルールを採用）"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), comment="作成日時"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), comment="更新日時"
    )


class AssetClass(Base):
    __tablename__ = "m_asset_classes"
    __table_args__ = {"comment": "資産クラスマスタ"}

    id: Mapped[int] = mapped_column(primary_key=True, comment="資産クラスID")
    asset_class_name: Mapped[str] = mapped_column(
        unique=True, comment="資産クラス名（例: 現金、国内株式、投資信託、ローン）"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), comment="作成日時"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), comment="更新日時"
    )


class Budget(Base):
    __tablename__ = "m_budgets"
    __table_args__ = (
        UniqueConstraint(
            "category_id", "year_month", "is_business", name="uq_m_budgets_category_month"
        ),
        {"comment": "予算マスタ（カテゴリ×年月×個人/事業区分ごとの予算額）"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, comment="予算ID")
    category_id: Mapped[int] = mapped_column(
        ForeignKey("m_categories.id"), comment="対象カテゴリID（m_categories参照）"
    )
    year_month: Mapped[str] = mapped_column(comment="対象年月（YYYY-MM形式）")
    is_business: Mapped[bool] = mapped_column(default=True, comment="事業予算/個人予算の区分")
    budget_amount: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 2), comment="予算金額")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), comment="作成日時"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), comment="更新日時"
    )


# ============================================================
# トランザクション（実績）テーブル群 (t_)
# ============================================================


class Transaction(Base):
    __tablename__ = "t_transactions"
    __table_args__ = (
        Index("idx_t_transactions_date", "transaction_date"),
        Index("idx_t_transactions_account_id", "account_id"),
        Index("idx_t_transactions_category_id", "category_id"),
        Index("idx_t_transactions_raw_data", "raw_data", postgresql_using="gin"),
        {"comment": "取引（各口座・カードの入出金実績）"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, comment="取引ID")
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("m_accounts.id", ondelete="CASCADE"), comment="口座ID（m_accounts参照）"
    )
    transaction_date: Mapped[datetime.date] = mapped_column(Date, comment="取引日")
    amount: Mapped[decimal.Decimal] = mapped_column(
        Numeric(12, 2), comment="取引金額（支出はマイナス、収入はプラスで統一）"
    )
    description: Mapped[str] = mapped_column(comment="摘要")
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("m_categories.id"), comment="カテゴリID（m_categories参照、NULLは未分類）"
    )
    business_ratio: Mapped[decimal.Decimal] = mapped_column(
        Numeric(5, 2),
        default=decimal.Decimal("100.00"),
        comment="事業按分比率(%)。0より大きい値が事業取引を意味する（is_businessフラグは持たない）",
    )
    source_type: Mapped[str] = mapped_column(
        comment="取得元種別（gmail_imap/moneyforward_csv/moneyforward_scraping/manual）"
    )
    source_hash: Mapped[str] = mapped_column(
        unique=True,
        comment="重複検知用SHA256ハッシュ（account_id+date+amount+description+ソース側一意ID[Message-ID等]から算出）",
    )
    raw_data: Mapped[dict | None] = mapped_column(
        JSONB, comment="取得した生データ（JSON形式。メールのMessage-ID、カード番号下4桁の検証結果等を含む）"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), comment="作成日時"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), comment="更新日時"
    )


class Transfer(Base):
    __tablename__ = "t_transfers"
    __table_args__ = (
        CheckConstraint(
            "from_transaction_id <> to_transaction_id", name="chk_t_transfers_distinct"
        ),
        {"comment": "口座間振替の相殺リンク（二重計上防止。リンクされた取引は各種集計から除外する）"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, comment="振替リンクID")
    from_transaction_id: Mapped[int] = mapped_column(
        ForeignKey("t_transactions.id", ondelete="CASCADE"),
        unique=True,
        comment="出金側取引ID（t_transactions参照）",
    )
    to_transaction_id: Mapped[int] = mapped_column(
        ForeignKey("t_transactions.id", ondelete="CASCADE"),
        unique=True,
        comment="入金側取引ID（t_transactions参照）",
    )
    match_confidence: Mapped[str] = mapped_column(
        default="auto", comment="検知方式（auto=自動検知/manual=手動紐付け）"
    )
    linked_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), comment="紐付け日時"
    )


class AssetSnapshot(Base):
    __tablename__ = "t_asset_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_date",
            "account_id",
            "ticker_or_name",
            name="uq_t_asset_snapshots_date_account_ticker",
        ),
        Index("idx_t_asset_snapshots_date", "snapshot_date"),
        {"comment": "資産スナップショット（残高追跡対象口座の日次評価額。ローンはマイナス値で記録）"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, comment="スナップショットID")
    snapshot_date: Mapped[datetime.date] = mapped_column(Date, comment="評価基準日")
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("m_accounts.id", ondelete="CASCADE"), comment="口座ID（m_accounts参照）"
    )
    asset_class_id: Mapped[int] = mapped_column(
        ForeignKey("m_asset_classes.id"), comment="資産クラスID（m_asset_classes参照）"
    )
    ticker_or_name: Mapped[str] = mapped_column(
        comment="銘柄コードまたは名称（現金・ローンは口座名をそのまま格納）"
    )
    current_value: Mapped[decimal.Decimal] = mapped_column(
        Numeric(12, 2), comment="評価額（時価）。ローンはマイナス値"
    )
    book_value: Mapped[decimal.Decimal | None] = mapped_column(
        Numeric(12, 2), comment="簿価（取得原価。証券のみ使用）"
    )
    source_type: Mapped[str] = mapped_column(
        comment="取得元（cumulative=初期残高+取引累積/moneyforward=MF連携/manual=手動入力）"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), comment="作成日時"
    )


class BatchLog(Base):
    __tablename__ = "t_batch_logs"
    __table_args__ = {"comment": "日次バッチ実行履歴"}

    id: Mapped[int] = mapped_column(primary_key=True, comment="バッチ実行ID")
    run_date: Mapped[datetime.date] = mapped_column(Date, comment="実行対象日")
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), comment="開始日時")
    finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), comment="終了日時"
    )
    status: Mapped[str] = mapped_column(comment="実行結果（success/partial_success/failed）")
    new_transaction_count: Mapped[int] = mapped_column(default=0, comment="新規取込件数")
    transfer_detected_count: Mapped[int] = mapped_column(default=0, comment="振替検知件数")
    institution_results: Mapped[list | None] = mapped_column(
        JSONB, comment="機関ごとの成否内訳（JSON配列: 機関名/status/件数またはエラー内容）"
    )
    error_message: Mapped[str | None] = mapped_column(
        comment="バッチ全体レベルのエラー内容（発生時のみ）"
    )
    discord_notified_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), comment="Discord通知送信日時"
    )
