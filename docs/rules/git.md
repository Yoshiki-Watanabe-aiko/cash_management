# Git運用（cash_management固有）

グローバルの `~/.claude/GIT_CONVENTIONS.md` を補足する、このプロジェクト固有のGit運用。差分がない項目（コミットメッセージ規約・.gitignore対象等）はグローバル規約をそのまま適用する。

## ブランチ命名（グローバル規約との差分）

グローバル規約は `feat/{内容}` / `feature/{内容}` を標準としているが、本プロジェクトはPhase 0〜10の段階的開発（`~/.claude/WORKFLOW_CONVENTIONS.md`の「フェーズ分割開発」）を採用しており、フェーズ単位の大きな機能追加では `phase{番号}-{内容}` ブランチを使う（例: `phase7-frontend`, `phase10-master-data-management`）。

- **フェーズ単位の大きな機能追加**: `phase{番号}-{内容}` を使う（意図的な差分。1フェーズ＝1機能セットの粒度が大きいため、`feat/`より意味が伝わりやすい）。
- **フェーズに紐づかない小さめの修正・ドキュメント更新等**: グローバル規約通り `feat/{内容}` / `fix/{内容}` / `docs/{内容}` を使う（本ドキュメント整理作業のブランチ`docs/project-scaffold-alignment`が実例）。

## コミットメッセージ
グローバル規約通り、日本語 + Conventional Commits型プレフィックス（`feat`/`fix`/`refactor`/`test`/`docs`/`chore`）。既存コミット履歴で一貫して守られている。

## PRマージ運用
`~/.claude/CLAUDE.md`の「プログラム修正後はGitをコミットしPRを行いmainリポジトリにマージする」方針通り、各フェーズはPRを作成してmainへマージする（実績: PR #1でphase10をマージ済み）。

## 関連
- グローバル規約: `~/.claude/GIT_CONVENTIONS.md`, `~/.claude/WORKFLOW_CONVENTIONS.md`
- 要件定義書: [`../requirements.md`](../requirements.md)
