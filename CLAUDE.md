# CLAUDE.md

## プロジェクト概要
個人用・個人事業主用の複数口座・クレジットカード・証券口座を統合管理するローカルWebアプリケーション。完全ローカル環境で動作し、日次バッチでメール・CSVからデータを取り込み、ダッシュボードで資産・キャッシュフローを可視化する。

## 技術スタック
- Python 3.14 / FastAPI（バックエンド）、React + TypeScript + Vite（フロントエンド） / Windows
- DB: PostgreSQL（Alembicでマイグレーション管理）
- バージョン管理: Git

## 参照ファイル
- 要件定義書          → @docs/requirements.md
- 詳細設計書          → @docs/詳細設計書/
- 課題管理表          → @docs/課題管理表.md
- 運用開始手順書      → @docs/運用開始手順書.md
- ドメイン用語集      → @CONTEXT.md
- 設計判断の記録      → @docs/adr/
- プロジェクト固有ルール → @docs/rules/（git.md・testing.md。グローバル規約との差分のみ記載）

## AI回答方針
- 複数実装がある場合はトレードオフを説明してから推奨案を提示する
- より良い設計があれば指示に縛られず積極的に提案する
- セキュリティ上の懸念点は必ず指摘する

## ドキュメントの自動見直し
- backend/app または frontend/src のコードを変更したセッションでは、Stopフック（`.claude/settings.json`）が docs/requirements.md・docs/詳細設計書/・CONTEXT.md・docs/adr/・docs/課題管理表.md のいずれも更新していないことを検知し、セッション終了前にドキュメント更新の要否を確認させる。
