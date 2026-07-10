# 統合資産・経費管理システム (Cash Management)

個人用・個人事業主用の複数口座・クレジットカード・証券口座を統合管理するローカルWebアプリケーション。完全ローカル環境（Windows + PostgreSQL）で動作し、日次バッチでメール・CSVからデータを取り込み、ダッシュボードで資産・キャッシュフローを可視化する。

詳細な仕様は以下を参照:

- 要件定義書: [`docs/requirements.md`](docs/requirements.md)(機能名レベルの一覧。詳細は詳細設計書へ)
- 詳細設計書: [`docs/詳細設計書/`](docs/詳細設計書/)(データ収集パイプライン・コアビジネスロジック・DB設計・ダッシュボードUI・マスタデータ管理機能)
- 課題管理書: [`docs/課題管理書.md`](docs/課題管理書.md)(未解決の拡張ポイント・解決済み課題の履歴)
- プロジェクト固有ルール: [`docs/rules/`](docs/rules/)(git.md・testing.md。グローバル規約との差分のみ)
- ドメイン用語集: [`CONTEXT.md`](CONTEXT.md)
- 設計判断（ADR）: [`docs/adr/`](docs/adr/)（0001〜0012）
- AI開発時の指示: [`CLAUDE.md`](CLAUDE.md)

## 構成

```
backend/    FastAPI + SQLAlchemy + Alembic（API・日次バッチ・DBスキーマ）
frontend/   React + Vite + TypeScript + shadcn/ui（ダッシュボード・取引管理画面）
batch/      Windowsタスクスケジューラ登録スクリプト、E2E用テストDB作成SQL
import/     マネーフォワードMEのCSVエクスポート配置先（transactions/, assets/）
backups/    pg_dumpによる自動バックアップ出力先
logs/       バッチ・アプリケーションのログ出力先
docs/       要件定義書・詳細設計書・課題管理書・rules・ADR
```

## セットアップ

前提: Windows / PostgreSQL 18がローカルにインストール済み / Python 3.14 / Node.js。

### 1. データベース

専用ロール・DBを作成済みであること（`cash_mgmt_user` / `cash_management`）。未作成の場合はpostgresスーパーユーザーで作成する。

```sql
CREATE ROLE cash_mgmt_user WITH LOGIN PASSWORD '...';
CREATE DATABASE cash_management OWNER cash_mgmt_user;
```

E2Eテスト専用DB（`cash_management_test`）が必要な場合は `batch/create_e2e_test_database.sql` をpostgresスーパーユーザーで一度だけ実行する（`cash_mgmt_user`はCREATEDB権限を持たないため）。

### 2. バックエンド

```bash
cd backend
uv sync
cp .env.example .env   # 値を編集（DB接続情報・Discord Webhook・Gmail IMAP等）
uv run alembic upgrade head
uv run python -m app.db.seed   # 金融機関・資産クラス・カテゴリの初期マスタ投入（冪等）
uv run uvicorn app.main:app --reload
```

詳細は [`backend/README.md`](backend/README.md) を参照。

### 3. フロントエンド

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE_URL 等
npm run dev
```

詳細は [`frontend/README.md`](frontend/README.md) を参照。

### 4. 日次バッチ

```bash
cd backend
uv run python -m app.cli.run_daily_import
```

Windowsタスクスケジューラへの登録（毎日深夜2時、スリープ解除・時刻超過時の即時実行・ログオン時トリガー付き）は管理者PowerShellで以下を実行する。

```powershell
cd batch
powershell -ExecutionPolicy Bypass -File .\register_task_scheduler.ps1
```

## テスト

| 対象 | コマンド | 実行場所 |
|------|----------|----------|
| バックエンド単体・結合 | `uv run pytest --cov` | `backend/` |
| フロントエンド単体 | `npm run test` | `frontend/` |
| フロントエンドE2E | `npm run test:e2e` | `frontend/` |

E2Eは `cash_management_test` DBを使用し、本番用 `cash_management` DBには影響しない（`backend/app/db/e2e_seed.py` がDB名に"test"を含まない場合は実行を拒否する安全装置を持つ）。

## 環境変数

主要な設定項目は各ディレクトリの `.env.example` を参照:

- [`.env.example`](.env.example)（バックエンド全体・バッチ）
- [`frontend/.env.example`](frontend/.env.example)（フロントエンド）

## 実装状況

Phase 0〜10が完了（DBスキーマ・MFME CSV取込・カードメールIMAP・バッチオーケストレーション・バックエンドAPI・フロントエンド・テスト整備・ドキュメント整備・マスタデータ管理機能）。フェーズごとの詳細は[`docs/requirements.md`](docs/requirements.md) 6章、未解決の拡張ポイントは[`docs/課題管理書.md`](docs/課題管理書.md)を参照。
