# Backend（統合資産・経費管理システム）

FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQLで構成されるバックエンド。ダッシュボード集計・取引管理・振替手動紐づけのAPIと、日次バッチ（メール・CSV取込、振替検知、残高スナップショット、バックアップ、Discord通知）を提供する。詳細な仕様は [`../docs/requirements.md`](../docs/requirements.md)、設計判断は [`../docs/adr/`](../docs/adr/) を参照。

## セットアップ

```bash
uv sync
cp .env.example .env   # ../ の .env.example を参照してこのディレクトリに配置
uv run alembic upgrade head
uv run python -m app.db.seed
```

`.env` の主な設定項目（詳細は [`../.env.example`](../.env.example)）:

- `DATABASE_URL` — PostgreSQL接続文字列
- `DISCORD_WEBHOOK_URL` — バッチ結果通知先
- `GMAIL_PERSONAL_ADDRESS` / `GMAIL_PERSONAL_APP_PASSWORD` / `GMAIL_BUSINESS_ADDRESS` / `GMAIL_BUSINESS_APP_PASSWORD` — カード利用速報メール取得用IMAP認証情報
- `ACCOUNT_HOLDER_NAMES` — 振替自動検知の摘要マッチング用口座名義
- `IMPORT_TRANSACTIONS_DIR` / `IMPORT_ASSETS_DIR` — マネーフォワードMEのCSV配置先
- `PG_DUMP_PATH` / `BACKUP_DIR` — バックアップ設定
- `CORS_ALLOW_ORIGINS` — フロントエンド開発サーバーのオリジン

## 開発サーバー起動

```bash
uv run uvicorn app.main:app --reload
```

`GET /health` でDB疎通確認を含むヘルスチェックができる。

## 日次バッチの手動実行

```bash
uv run python -m app.cli.run_daily_import
```

7処理単位（MFME取引明細CSV取込／MFME資産評価CSV取込／残高スナップショット／振替検知／カードメール取込[個人用]／カードメール取込[事業用]／pg_dumpバックアップ）を独立したtry/except・軽量リトライで実行し、結果を `t_batch_logs` に記録した上でDiscordへ通知する（[ADR 0011](../docs/adr/0011-batch-orchestration-unit-and-savepoints.md)）。DB接続自体が失敗した場合はDBを経由しない簡易Discord通知を送る（[ADR 0008](../docs/adr/0008-batch-resilience-strategy.md)）。

## マイグレーション

```bash
uv run alembic revision --autogenerate -m "変更内容"
uv run alembic upgrade head
```

新規テーブル・カラムには `docs/requirements.md` 4章の規約（マスタ `m_` / トランザクション `t_` 接頭辞、全テーブル・カラムへの日本語コメント）に従うこと。DDL詳細は [`../docs/詳細設計書/03_データベース設計.md`](../docs/詳細設計書/03_データベース設計.md) を参照。

## テスト

```bash
uv run pytest --cov
```

`tests/conftest.py` の `db_session` フィクスチャは実PostgreSQLへ接続し、各テストをSAVEPOINTでロールバックすることでDBを汚さずに結合テストを行う。FastAPIエンドポイントのテストは `client` フィクスチャ（`db_session` のトランザクションをDB依存関係ごとオーバーライド）を使う。

## ディレクトリ構成

```
app/
├── api/            APIルーター（dashboard, transactions, transfers, reference, health）
├── services/        ビジネスロジック（CSV取込、カードメール取込、振替検知、バッチオーケストレーション等）
├── schemas/         Pydanticスキーマ
├── cli/             日次バッチのエントリポイント（run_daily_import.py）
├── db/              セッション管理・シード・E2E用シード
├── core/            共通設定・営業日判定等
└── models.py         SQLAlchemyモデル（全10テーブル）
alembic/             マイグレーション
tests/               pytest
```
