# バッチオーケストレーション：処理単位の定義とSAVEPOINTによる隔離

ADR 0008で「各金融機関の取込処理は機関ごとに独立してtry/exceptで囲み、軽量リトライを行う」方針を定めたが、実装（Phase 5）にあたり「機関ごと」の粒度と、DBセッションを共有しながら障害を隔離する具体的な手段を以下の通り確定した。

## 1. 「処理単位」はカード会社単位ではなく、取込ソース単位で7分割する

マネーフォワードME CSVは1ファイルに複数金融機関の明細が混在し、Gmail IMAPの1回のフェッチも複数カード会社のメールを含む。そのため文字通り「金融機関ごと」に処理を分割することはできない。代わりに、`app/services/batch_orchestrator.py`では以下7つの処理単位を独立したtry/except・リトライ対象とする。

1. MFME取引明細CSV取込
2. MFME資産評価CSV取込
3. 残高スナップショット（累積方式）
4. 振替検知
5. カードメール取込（個人用メールボックス）
6. カードメール取込（事業用メールボックス）
7. pg_dumpバックアップ

個人用・事業用メールボックスは別々のGmailアカウントであり、一方のIMAP接続障害が他方をブロックしないよう`card_email_pipeline.py`に`import_personal_card_emails`/`import_business_card_emails`を独立した公開関数として追加した（従来の`import_card_emails`は後方互換のため残置）。

## 2. SAVEPOINTの二層構造でセッションの健全性とファイル単位の一貫性を両立する

- **ステップレベル（オーケストレータ）**: `_run_step`が各処理単位を`session.begin_nested()`で囲んだ上でリトライする。これは、あるステップがDB制約違反等でセッションのトランザクションを中断状態にした場合でも、SAVEPOINTロールバックでセッションを健全な状態に戻し、後続ステップの処理を継続できるようにするため（PostgreSQLは中断状態のトランザクション上でクエリを継続できない）。
- **ファイル／メール単位（各パイプライン内部）**: `csv_import_pipeline.py`の`import_transactions_folder`/`import_assets_folder`、および`card_email_pipeline.py`の`_import_mailbox`では、1ファイル・1通のメールごとに`session.begin_nested()`で囲んだ上でtry/exceptする。CSVファイルは成功後にのみ`processed/`へ移動する仕様（Phase 3）のため、ステップレベルのSAVEPOINTだけでファイル単位の失敗を握りつぶすと「ファイルは移動済みだがDB行はロールバック済み」という不整合が起きる。ファイル単位のSAVEPOINTで失敗を握りつぶし例外を外へ伝播させない設計とすることで、後続ファイルの処理を継続しつつこの不整合を避けている。

失敗したファイル・メールは`ImportSummary.failed_files`/`CardEmailImportSummary.parse_error_count`に記録され、ステップ関数はそれを見てステップ全体を「失敗」として例外を送出するかどうかを判断する（＝ステップレベルのリトライは「フォルダ内の一部ファイル」のような部分的失敗の再試行にも安全に対応できる。成功済みファイルは既に`processed/`へ移動済みのため、再試行時は失敗ファイルのみが対象になる）。

## 3. バックアップもinstitution_resultsに含める（スキーマ変更なし）

`t_batch_logs.institution_results`は元々「機関ごとの成否内訳」というコメントだが、pg_dumpバックアップも同じJSONB配列に7番目のステップとして含めることにした。バックアップ専用のカラムを追加するほどの複雑さではなく、既存スキーマの再利用で要件を満たせるため。あわせて、コメントが元々「JSON配列」を明記していたにもかかわらずPython側の型注釈が`dict | None`だった不整合を`list | None`に修正した（マイグレーション不要、JSONB自体の変更なし）。

## 4. pg_dumpのサブプロセス実行はos.environを継承する

`subprocess.run(..., env={"PGPASSWORD": ...})`のように環境変数を丸ごと置き換えると、Windows環境ではネットワーク名前解決に必要な`SYSTEMROOT`等が失われ、pg_dumpが`localhost`を解決できずに失敗する（実機検証で発見）。`env={**os.environ, "PGPASSWORD": ...}`として既存の環境変数を継承しつつ`PGPASSWORD`のみ追加する方式に修正した。

## 5. SessionLocalに`expire_on_commit=False`を設定する

`batch_orchestrator.run_daily_batch`は`t_batch_logs`書込後・Discord通知後の2回`session.commit()`する。デフォルトの`expire_on_commit=True`のままだと、コミット後に返した`BatchLog`インスタンスの属性が失効し、呼び出し元（CLI）が`with SessionLocal() as session:`ブロックを抜けた後（セッションクローズ後）に`batch_log.status`等へアクセスすると`DetachedInstanceError`になる（実機検証で発見）。`app/db/session.py`の`SessionLocal`に`expire_on_commit=False`を設定し、コミット後もオブジェクトの属性をメモリ上の値のまま使えるようにした。
