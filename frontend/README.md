# Frontend（統合資産・経費管理システム）

React 19 + TypeScript + Vite + Tailwind CSS v4 + shadcn/ui。ダッシュボード（純資産推移・予算消化率・キャッシュフロー・カテゴリ別支出）と取引管理画面（フィルタ・インライン編集・振替の手動紐づけ）を提供する。詳細な仕様は [`../docs/requirements.md`](../docs/requirements.md) 7章を参照。

## セットアップ

```bash
npm install
cp .env.example .env   # VITE_API_BASE_URL をバックエンドの起動先に合わせて設定
npm run dev
```

バックエンド（`../backend/`）を先に起動しておくこと（既定 `http://localhost:8000`）。

## スクリプト

| コマンド | 内容 |
|----------|------|
| `npm run dev` | Vite開発サーバー |
| `npm run build` | 型チェック（`tsc -b`）＋本番ビルド |
| `npm run lint` | oxlint |
| `npm run preview` | ビルド成果物のプレビュー |
| `npm run test` | Vitest（単体・コンポーネントテスト） |
| `npm run test:watch` | Vitest watchモード |
| `npm run test:e2e` | Playwright E2E |

## 重要な設計判断

- **バックエンドのDecimalフィールドはJSON文字列で返る**: `amount` / `business_ratio` / `net_worth` / `budget_amount` 等はFastAPIの`response_model`シリアライズにより数値ではなく文字列として返る（Pydantic v2の精度保持デフォルト挙動）。`src/api/types.ts` では該当フィールドをすべて `string` 型とし、チャート描画・金額比較の直前に `Number()` へ変換する。新しいAPIレスポンスの型を追加する際もこのルールに従うこと。
- **TanStack Tableは `getRowId: (row) => String(row.id)` を必ず設定する**: 未設定だと行の位置インデックスがキーになり、ページ送りや再フェッチ時に別取引へインライン編集が誤爆する（`TransactionsTable` 参照）。
- **shadcn/ui の `Select` は空文字列 `''` で初期化する**: `useState<string>()`（`undefined`初期値）にすると、値を`undefined`へ戻す際に「uncontrolled→controlled→uncontrolled」の遷移でプレースホルダ表示に正しく戻らない。常にcontrolledな空文字列を「未選択」の番兵値として使う（`UnlinkedTransfersPanel` 参照）。

## テストの分担

- **Vitest（単体・コンポーネント）**: `lib/format.ts`、`TransactionsTable`、`TransactionFiltersBar`、`BudgetProgressWidget`、`UnlinkedTransfersPanel` 等。Radix Select はjsdom上での実クリック操作に難があるため、Select操作を伴わない状態・native要素の検証に留める。
- **Playwright（E2E）**: ダッシュボード表示・取引管理（フィルタ・カテゴリ再適用）・振替の手動紐づけ（Selectの実操作を含む）を検証。専用の `cash_management_test` DBを使用し、`backend/app/db/e2e_seed.py` が `frontend/e2e/global-setup.ts` から毎回スキーマ再作成・シード投入を行う（本番用 `cash_management` DBは汚さない）。

## ディレクトリ構成

```
src/
├── api/              APIクライアント・型定義（Decimalフィールドはstring）
├── components/       共通UIコンポーネント（layout, ui, ErrorBoundary）
├── features/
│   ├── dashboard/     ダッシュボード4ウィジェット
│   ├── transactions/  取引管理画面（フィルタ・データグリッド）
│   └── transfers/     振替の手動紐づけ
├── lib/               フォーマット・クエリクライアント設定
└── test/              Vitestセットアップ
e2e/                   Playwright E2Eテスト・global-setup
```
