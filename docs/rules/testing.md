# テスト方針（cash_management固有）

グローバルの `~/.claude/DB_CONVENTIONS.md`・`~/.claude/WORKFLOW_CONVENTIONS.md` を補足する、このプロジェクト固有のテスト運用。

## テスト構成

| 対象 | フレームワーク | 実行場所 | コマンド |
|------|--------------|----------|----------|
| バックエンド単体・結合 | pytest | `backend/` | `uv run pytest --cov` |
| フロントエンド単体・コンポーネント | Vitest + React Testing Library + jsdom | `frontend/` | `npm run test` |
| フロントエンドE2E | Playwright | `frontend/` | `npm run test:e2e` |

現在の実績: バックエンドpytest 187件全パス・カバレッジ98%、フロントエンドVitest 38件全パス。

## テストDBの分離（DB_CONVENTIONS.mdとの差分）

グローバル規約は環境変数`DATABASE_TEST_URL`またはCLIフラグでのテストDB切替を推奨しているが、本プロジェクトの実装は以下の方式を採用している（意図的な差分。安全性の目標は同一）。

- **バックエンド単体・結合テスト**: 実PostgreSQLへSAVEPOINTロールバック方式で接続する`db_session`フィクスチャ（`backend/tests/conftest.py`）を使用。FastAPI `TestClient`をDB依存関係ごとオーバーライドする`client`フィクスチャも用意。
- **フロントエンドE2E**: 専用の`cash_management_test`データベースを分離。`cash_mgmt_user`はCREATEDB権限を持たないため、`batch/create_e2e_test_database.sql`をpostgresスーパーユーザーで一度だけ実行してデータベースを作成する運用（一度きりの手動セットアップ）。以降のスキーマ破棄・再作成・シード投入は`backend/app/db/e2e_seed.py`（Playwrightの`globalSetup`から`DATABASE_URL`をテストDB向けに上書きして起動）が毎回自動で行う。
- **安全装置**: `e2e_seed.py`はデータベース名に"test"を含まない場合は実行を拒否する（本番`cash_management`DBを誤って初期化する事故を防止）。

将来、他プロジェクトと同様に明示的な`DATABASE_TEST_URL`環境変数へ寄せることも検討可能だが、現状の名前ガード方式で安全性は担保できているため優先度は低い。

## E2Eで発見した実バグの例
`UnlinkedTransfersPanel`の出金側/入金側`Select`が`useState<string>()`(初期値`undefined`)を使っていたため、紐づけ成功後にstateを`undefined`へ戻してもRadix Selectの表示が「uncontrolled→controlled→uncontrolled」の遷移で正しくプレースホルダに戻らない不具合があった。`useState('')`に変更し、常にcontrolledな空文字列を「未選択」の番兵値として使うよう修正した。Radix Selectはjsdom上での実操作が困難なため、Vitest側はSelect操作を伴わない状態・native要素の検証に留め、実際の選択操作の検証はPlaywright E2Eが担保する設計とした。

## 関連
- 要件定義書: [`../requirements.md`](../requirements.md)
- ダッシュボード・取引管理UI設計: [`../詳細設計書/04_ダッシュボードUI設計.md`](../詳細設計書/04_ダッシュボードUI設計.md)
- バックエンドREADME: [`../../backend/README.md`](../../backend/README.md)
- フロントエンドREADME: [`../../frontend/README.md`](../../frontend/README.md)
