# 統合資産・経費管理システム (Local Finance & Asset Management System) 要求仕様書 v3

> v2からグリリングセッション（設計レビュー）で確定した方針を反映した更新版。ドメイン用語は `CONTEXT.md`、個別の設計判断の背景は `docs/adr/0001`〜`0008` を参照。

## 1. プロジェクト概要
個人用および個人事業主用の複数口座・クレジットカード・証券口座を統合管理するローカルWebアプリケーション。完全ローカル環境で動作し、情報漏洩リスクを排除しつつ、高度なデータ分析と自動化を実現する。

## 2. 開発環境・技術スタック
- **OS**: Windows
- **IDE**: Visual Studio Code
- **AI Agent**: Claude Code
- **バージョン管理**: Git
- **インフラ/実行環境**:
  - Windows タスクスケジューラ（日次バッチ実行用、深夜2時想定）
    - 「スケジュールされた時刻を逃した場合はできるだけ早く実行する」「スリープを解除して実行する」を有効化
    - 保険としてログオン時/起動時トリガーも追加（[ADR 0008](../docs/adr/0008-batch-resilience-strategy.md)）
  - ホストバインド (`0.0.0.0`) による同一ローカルネットワーク内からのアクセス許可（認証は設けない。利便性優先）
- **データベース**: PostgreSQL（Windowsローカルに直接インストール済みの環境を利用）
  - マイグレーション管理: Alembic
  - **命名規則**: マスタテーブルは接頭辞 `m_`、トランザクション（実績・履歴）テーブルは接頭辞 `t_` を付与する
  - 全テーブル・カラムに日本語コメント（`COMMENT ON TABLE` / `COMMENT ON COLUMN`）を付与する
- **バックエンド**: Python 3.14.4 / FastAPI
  - 依存関係管理: Poetry または uv
  - ロギング: 標準 `logging` モジュール（ファイル出力）
  - データ処理: `pandas` 等を利用した正規化・クレンジング
  - 祝日計算: `jpholiday`（日本の祝日を算出。年次メンテナンス不要）
- **フロントエンド**: React + TailwindCSS
  - UIコンポーネント: shadcn/ui
  - アイコン: Lucide Icons
  - ルーティング: react-router-dom
  - データフェッチ: React Query
  - 日付処理: date-fns
- **通知連携**: Discord（Webhook）
  - 通知タイミング: バッチ実行の**都度**送信（機関ごとの成功/失敗サマリーを含む）
  - DB接続自体に失敗した致命的なケースでは、DBを経由しない簡易通知経路で「起動失敗」を別途通知する（[ADR 0008](../docs/adr/0008-batch-resilience-strategy.md)）

## 3. 対象金融機関（初期実装で全金融機関を並行対応）
- **クレジットカード**: 三井住友カード, 楽天カード, EPOSカード, PayPayカード, viewカード, セゾンカード, イオンカード（各カードで個人用/事業用が存在）
- **銀行**: 楽天銀行, 三井住友銀行, 三菱UFJ銀行, ゆうちょ銀行, PayPay銀行, イオン銀行, 住信SBIネット銀行, みずほ銀行, りそな銀行（各銀行で個人用/事業用が存在）
- **証券会社**: 楽天証券, SBI証券, 三菱UFJeスマート証券, マネックス証券
- **QRコード決済**: PayPay, 楽天Pay（チャージ式で利用）
- **ローン**: 三井住友銀行, PayPay銀行（残債200〜300万円規模。[ADR 0002](../docs/adr/0002-loan-liability-tracking.md)）

> クレジットカードと都度引き落とし式QR決済は、口座残高・資産スナップショットの追跡対象外（支出のカテゴリ分類・事業按分専用）。理由は [ADR 0007](../docs/adr/0007-balance-tracking-scope.md) を参照。

## 4. データ収集パイプライン（バックエンドバッチ処理）

日次（深夜2時想定）でWindowsタスクスケジューラによりPythonスクリプトを実行し、以下のフローでデータを処理する。

### 4.1 クレジットカード：IMAP + アプリパスワード方式
- Gmail APIのOAuth登録・審査・リフレッシュトークン管理を避け、**IMAP + Googleアプリパスワード**で「利用速報メール」を取得する。コストゼロ・無人運用向き。
- **個人用・事業用は別々のGmailアドレス**で運用されているため、`.env`に2組のIMAP認証情報（アドレス＋アプリパスワード）を保持し、2つのメールボックスをそれぞれ処理する。
- カード会社の判別は送信元メールアドレス（Fromヘッダ）、個人用/事業用の判別は受信メールボックスで行う（[ADR 0006](../docs/adr/0006-card-account-resolution-by-mailbox.md)）。
- 補助的な検証として、メール本文からカード番号下4桁を抽出し、想定する口座と矛盾がないか確認する。
- カード会社ごとに正規表現ベースのパーサーを実装（日付・金額・店舗名を抽出）。実メールサンプルが入手できた会社から順次実装する。
- **実装状況**: IMAP接続・送信元アドレスによる金融機関解決（`m_institutions.card_alert_sender_email`）・受信メールボックスによる口座解決・下4桁整合性検証・重複防止（`t_transactions.source_hash`）・パーサー登録レジストリの一連のフレームワークは実装済み。実メールサンプルが未入手のため、カード会社別パーサー本体は未実装（レジストリは空）。詳細はADR 0010を参照。

### 4.2 銀行・証券・ローン：マネーフォワードME経由
- **入出金明細**と**資産評価額（証券・ローン残高）**は別々のCSVエクスポート・別フォルダで取込む（例: `import/transactions/`, `import/assets/`）。
- 第一段階: マネーフォワードMEの明細CSVエクスポート機能を利用し、指定フォルダに配置されたCSVをバッチが読み込む方式（ログイン自動化不要、低リスク）。
- 第二段階（将来拡張）: Playwright等によるスクレイピング自動化を追加。
- 対象フォルダにその日の新規CSVが存在しない場合はエラーではなく正常なスキップとして扱い、Discordサマリーに「対象ファイルなし」と明記する。
- ローンはマネーフォワードME連携を第一候補とし、導入時に一度だけ判定して、取得できなければ口座単位で恒久的に手動入力運用へ切り替える（[ADR 0002](../docs/adr/0002-loan-liability-tracking.md)）。

### 4.3 共通処理フロー
1. **データ取得**（4.1 / 4.2 の方式でメール・CSVを取得）
2. **データクレンジング & 判定**
   - 金融機関ごとのフォーマット揺れを吸収
   - カテゴリ自動分類（`m_category_rules`を`priority`昇順で評価し、最初に一致したキーワード[部分文字列一致]を採用。一致しなければ「未分類」）
   - 口座間移動（振替）の自動相殺ロジック（5.2章）
   - **重複防止**: 口座ID・日付・金額・摘要に加え、メールの`Message-ID`やCSV行の一意情報を含めてSHA256ハッシュ化し、`t_transactions.source_hash`にUNIQUE制約＋`ON CONFLICT DO NOTHING`で二重計上を防ぐ（[ADR 0003](../docs/adr/0003-dedup-hash-includes-source-unique-id.md)）
3. **DB保存**
   - 生データはJSONB型（`raw_data`）で保持しつつ、正規化データを各種テーブルへ`INSERT/UPDATE`
   - 残高追跡対象口座（銀行・証券・ローン・チャージ式QR決済）は、日次で`t_asset_snapshots`へスナップショットを書き込む。銀行・チャージ式QR決済は「初期残高＋取引累積」で算出し、証券・ローン（MF連携時）はMFの評価額をそのまま保存する（[ADR 0007](../docs/adr/0007-balance-tracking-scope.md)）
4. **バックアップ & 通知**
   - `pg_dump`による自動バックアップ（**Google Drive**同期フォルダへ保存）。直近30日分の日次バックアップ＋各月末分は1年間保持し、期限切れは自動削除
   - 機関ごとの成功/失敗を`t_batch_logs.institution_results`（JSONB）に記録し、Discordへ毎回通知
   - 機関単位の処理は独立してtry/exceptで囲み、軽量リトライ（3回）を行い、1社の失敗が他社をブロックしない（[ADR 0008](../docs/adr/0008-batch-resilience-strategy.md)）

**実装状況**: Phase 5で実装済み。`app/services/batch_orchestrator.py`が「MFME取引明細CSV取込／MFME資産評価CSV取込／残高スナップショット／振替検知／カードメール取込(個人用)／カードメール取込(事業用)／pg_dumpバックアップ」の7処理単位を独立したtry/except・軽量リトライ（既定3回・5秒間隔、`.env`の`BATCH_RETRY_COUNT`/`BATCH_RETRY_DELAY_SECONDS`で調整可）で実行し、結果を`t_batch_logs`へ記録した上でDiscordへサマリー通知する。処理単位の粒度や実装上のSAVEPOINT設計は[ADR 0011](../docs/adr/0011-batch-orchestration-unit-and-savepoints.md)を参照。DB接続自体が失敗する致命的なケースでは`app/cli/run_daily_import.py`の最上位try/exceptがDBを経由しない簡易Discord通知を送る。Windowsタスクスケジューラへの登録は`batch/register_task_scheduler.ps1`（管理者PowerShellで手動実行、要件2章の「時刻を逃した場合はできるだけ早く実行」「スリープ解除して実行」「ログオン時/起動時トリガー」を設定）で行う。バックアップ保存先は現状リポジトリ内`backups/`フォルダを既定とし、Google Drive同期フォルダへ変更する場合は`.env`の`BACKUP_DIR`を絶対パスで上書きする。

## 5. コア・ビジネスロジック

### 5.1 個人・事業の混在管理
- 口座単位（`m_accounts.is_business`）で口座を分類する。
- 取引単位の事業性は`business_ratio`（0〜100%、NULL不可）のみで表現する。`is_business`という真偽値は取引・カテゴリいずれにも持たせない（[ADR 0004](../docs/adr/0004-business-ratio-only-no-is-business-flag.md)）。
- 取引作成時、`m_accounts.default_business_ratio`を必ず継承する（事業専用口座=100%、個人専用口座=0%、混在口座=任意%）。個別取引での手動修正は引き続き可能。

### 5.2 口座間移動（振替）の自動相殺ロジック
以下の条件をすべて満たす明細ペアを検知し、`t_transfers`テーブルに登録して二重計上を防ぐ（[ADR 0005](../docs/adr/0005-transfer-detection-and-exclusion.md)）。
1. 金額の絶対値が完全一致。
2. 日本の祝日（`jpholiday`で算出）と年末年始の銀行休業期間（12/31〜1/3、固定）を除いた**真の営業日**で0〜3日以内。
3. 摘要欄に口座名義（全角/半角スペース許容、`.env`で設定）または保有口座・カードの名称が含まれる。

条件3を満たさないペアは自動リンクせず、手動補正画面でのリンクに委ねる。日次バッチは「直近7日以内・未リンクの取引」を毎回再評価する（新規取込分に限定しない）。`t_transfers`にリンクされた取引は、キャッシュフロー・カテゴリ別支出・予算消化率など、あらゆる集計から除外する。

### 5.3 カテゴリ自動分類
- `m_category_rules`（キーワード[部分文字列]→`m_categories.id`のマッピング、`priority`昇順で評価し最初の一致を採用）を取込処理時に適用。
- 一致しない場合は「未分類」カテゴリのまま保存し、手動補正画面で修正する。
- ルール追加・変更後、手動補正画面の「未分類の取引にルールを再適用」ボタンで、未分類のみ一括再判定できる（既に手動でカテゴリ設定済みの取引は上書きしない）。

### 5.4 予算管理
- `m_budgets`（費目×年月×個人/事業区分ごとの予算額）。
- 予算消化率は、取引金額をそのまま合計するのではなく、`amount × business_ratio / 100`（事業分）／`amount × (100 - business_ratio) / 100`（個人分）で按分した金額を合計して算出する。

### 5.5 残高・資産スナップショット
- 「残高追跡対象口座」（銀行・証券・ローン・チャージ式QR決済）のみ`t_asset_snapshots`を持つ。クレジットカード・都度引き落とし式QR決済は対象外（[ADR 0007](../docs/adr/0007-balance-tracking-scope.md)）。
- 銀行・チャージ式QR決済: `m_accounts.opening_balance`（口座登録時に1回だけ手入力）＋以降の取引累積で日次残高を算出し、`t_asset_snapshots`へ書き込む。
- 証券: マネーフォワードMEの資産評価CSVから銘柄別評価額を取得し、そのまま保存。
- ローン: マネーフォワードME連携（成功時）またはユーザーの月次手動入力（失敗時、口座単位で固定）から取得し、マイナス値として保存する。
- 「純資産」= 全ての資産スナップショットの合計（投資性資産＋現金性資産－ローン残高）。ダッシュボードの時系列ウィジェットは「純資産の推移」として表示する（総資産ではない）。
- 外貨建て資産（米国株等）は現時点で未保有だが将来保有の可能性が高い。当面は円換算後の評価額のみ保存し、原通貨・為替レートの分解管理はスコープ外とする（将来拡張ポイント）。
- 稼働開始前の過去データは遡って取り込まない。稼働開始日時点の残高を`opening_balance`として設定し、そこから先を追跡する。

## 6. データベース設計（PostgreSQL DDL）

命名規則: マスタテーブル = `m_`接頭辞、トランザクション（実績）テーブル = `t_`接頭辞。全テーブル・カラムに日本語コメントを付与する。実装時はAlembicでこれらのテーブルを構築する。

```sql
-- ============================================================
-- マスタテーブル群 (m_)
-- ============================================================

CREATE TABLE m_institutions (
    id SERIAL PRIMARY KEY,
    institution_name VARCHAR(100) NOT NULL,
    institution_type VARCHAR(50) NOT NULL,
    card_alert_sender_email VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE m_institutions IS '金融機関マスタ';
COMMENT ON COLUMN m_institutions.id IS '金融機関ID';
COMMENT ON COLUMN m_institutions.institution_name IS '金融機関名（例: 楽天銀行、三井住友カード）';
COMMENT ON COLUMN m_institutions.institution_type IS '機関種別（bank/credit_card/securities/qr_payment）';
COMMENT ON COLUMN m_institutions.card_alert_sender_email IS 'クレジットカード利用速報メールの送信元アドレス（Fromヘッダ。institution_type=credit_cardのみ使用。実メールサンプル確認後に設定、ADR 0010）';
COMMENT ON COLUMN m_institutions.created_at IS '作成日時';
COMMENT ON COLUMN m_institutions.updated_at IS '更新日時';

CREATE TABLE m_accounts (
    id SERIAL PRIMARY KEY,
    institution_id INTEGER NOT NULL REFERENCES m_institutions(id),
    account_name VARCHAR(100) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    is_business BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    default_business_ratio NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    tracks_balance BOOLEAN NOT NULL DEFAULT FALSE,
    balance_method VARCHAR(20),
    opening_balance NUMERIC(12, 2),
    opening_balance_date DATE,
    moneyforward_account_name VARCHAR(100),
    card_last4 VARCHAR(4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE m_accounts IS '口座マスタ（銀行口座・クレジットカード・証券口座・QR決済アカウント・ローン）';
COMMENT ON COLUMN m_accounts.id IS '口座ID';
COMMENT ON COLUMN m_accounts.institution_id IS '金融機関ID（m_institutions参照）';
COMMENT ON COLUMN m_accounts.account_name IS '口座表示名（例: 楽天銀行 個人）';
COMMENT ON COLUMN m_accounts.account_type IS '口座種別（bank/credit_card/securities/qr_payment/loan）';
COMMENT ON COLUMN m_accounts.is_business IS '事業用口座フラグ（口座自体の分類）';
COMMENT ON COLUMN m_accounts.is_active IS '有効フラグ（解約・休眠口座はFALSE。自動取込対象からは外れるが過去データは保持）';
COMMENT ON COLUMN m_accounts.default_business_ratio IS '当口座で新規作成される取引に適用する事業按分デフォルト率(%)';
COMMENT ON COLUMN m_accounts.tracks_balance IS '残高追跡対象フラグ（TRUEの口座のみt_asset_snapshotsを持つ。クレカ・都度引き落とし式QR決済はFALSE）';
COMMENT ON COLUMN m_accounts.balance_method IS '残高算出方式（cumulative=初期残高+取引累積 / moneyforward=MF連携 / manual=手動入力）';
COMMENT ON COLUMN m_accounts.opening_balance IS '初期残高（balance_method=cumulativeの口座のみ使用）';
COMMENT ON COLUMN m_accounts.opening_balance_date IS '初期残高の基準日';
COMMENT ON COLUMN m_accounts.moneyforward_account_name IS 'マネーフォワードME連携時の口座表示名（CSVの「保有金融機関」列とのマッチングに使用。未設定の場合はaccount_nameで照合。ADR 0009）';
COMMENT ON COLUMN m_accounts.card_last4 IS 'クレジットカード番号下4桁（account_type=credit_cardのみ使用。利用速報メール本文からの抽出値との整合性検証用、ADR 0010）';
COMMENT ON COLUMN m_accounts.created_at IS '作成日時';
COMMENT ON COLUMN m_accounts.updated_at IS '更新日時';

CREATE TABLE m_categories (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE m_categories IS 'カテゴリマスタ（収入・支出どちらの取引にも使う中立的な分類）';
COMMENT ON COLUMN m_categories.id IS 'カテゴリID';
COMMENT ON COLUMN m_categories.category_name IS 'カテゴリ名（例: 食費、交通費、給与、未分類）';
COMMENT ON COLUMN m_categories.created_at IS '作成日時';
COMMENT ON COLUMN m_categories.updated_at IS '更新日時';

CREATE TABLE m_category_rules (
    id SERIAL PRIMARY KEY,
    keyword_pattern VARCHAR(255) NOT NULL,
    category_id INTEGER NOT NULL REFERENCES m_categories(id),
    priority INTEGER NOT NULL DEFAULT 100,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE m_category_rules IS 'カテゴリ自動分類ルールマスタ（摘要文字列との部分文字列マッチング）';
COMMENT ON COLUMN m_category_rules.id IS 'ルールID';
COMMENT ON COLUMN m_category_rules.keyword_pattern IS '摘要とのマッチングに使うキーワード（部分文字列一致）';
COMMENT ON COLUMN m_category_rules.category_id IS '一致時に適用するカテゴリID（m_categories参照）';
COMMENT ON COLUMN m_category_rules.priority IS '適用優先順位（値が小さいほど優先。最初に一致したルールを採用）';
COMMENT ON COLUMN m_category_rules.created_at IS '作成日時';
COMMENT ON COLUMN m_category_rules.updated_at IS '更新日時';

CREATE TABLE m_asset_classes (
    id SERIAL PRIMARY KEY,
    asset_class_name VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE m_asset_classes IS '資産クラスマスタ';
COMMENT ON COLUMN m_asset_classes.id IS '資産クラスID';
COMMENT ON COLUMN m_asset_classes.asset_class_name IS '資産クラス名（例: 現金、国内株式、投資信託、ローン）';
COMMENT ON COLUMN m_asset_classes.created_at IS '作成日時';
COMMENT ON COLUMN m_asset_classes.updated_at IS '更新日時';

CREATE TABLE m_budgets (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES m_categories(id),
    year_month CHAR(7) NOT NULL,
    is_business BOOLEAN NOT NULL DEFAULT TRUE,
    budget_amount NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_m_budgets_category_month UNIQUE (category_id, year_month, is_business)
);
COMMENT ON TABLE m_budgets IS '予算マスタ（カテゴリ×年月×個人/事業区分ごとの予算額）';
COMMENT ON COLUMN m_budgets.id IS '予算ID';
COMMENT ON COLUMN m_budgets.category_id IS '対象カテゴリID（m_categories参照）';
COMMENT ON COLUMN m_budgets.year_month IS '対象年月（YYYY-MM形式）';
COMMENT ON COLUMN m_budgets.is_business IS '事業予算/個人予算の区分';
COMMENT ON COLUMN m_budgets.budget_amount IS '予算金額';
COMMENT ON COLUMN m_budgets.created_at IS '作成日時';
COMMENT ON COLUMN m_budgets.updated_at IS '更新日時';

-- ============================================================
-- トランザクション（実績）テーブル群 (t_)
-- ============================================================

CREATE TABLE t_transactions (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES m_accounts(id) ON DELETE CASCADE,
    transaction_date DATE NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    description TEXT NOT NULL,
    category_id INTEGER REFERENCES m_categories(id),
    business_ratio NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    source_type VARCHAR(50) NOT NULL,
    source_hash CHAR(64) NOT NULL,
    raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_t_transactions_source_hash UNIQUE (source_hash)
);
COMMENT ON TABLE t_transactions IS '取引（各口座・カードの入出金実績）';
COMMENT ON COLUMN t_transactions.id IS '取引ID';
COMMENT ON COLUMN t_transactions.account_id IS '口座ID（m_accounts参照）';
COMMENT ON COLUMN t_transactions.transaction_date IS '取引日';
COMMENT ON COLUMN t_transactions.amount IS '取引金額（支出はマイナス、収入はプラスで統一）';
COMMENT ON COLUMN t_transactions.description IS '摘要';
COMMENT ON COLUMN t_transactions.category_id IS 'カテゴリID（m_categories参照、NULLは未分類）';
COMMENT ON COLUMN t_transactions.business_ratio IS '事業按分比率(%)。0より大きい値が事業取引を意味する（is_businessフラグは持たない）';
COMMENT ON COLUMN t_transactions.source_type IS '取得元種別（gmail_imap/moneyforward_csv/moneyforward_scraping/manual）';
COMMENT ON COLUMN t_transactions.source_hash IS '重複検知用SHA256ハッシュ（account_id+date+amount+description+ソース側一意ID[Message-ID等]から算出）';
COMMENT ON COLUMN t_transactions.raw_data IS '取得した生データ（JSON形式。メールのMessage-ID、カード番号下4桁の検証結果等を含む）';
COMMENT ON COLUMN t_transactions.created_at IS '作成日時';
COMMENT ON COLUMN t_transactions.updated_at IS '更新日時';

CREATE TABLE t_transfers (
    id SERIAL PRIMARY KEY,
    from_transaction_id INTEGER UNIQUE REFERENCES t_transactions(id) ON DELETE CASCADE,
    to_transaction_id INTEGER UNIQUE REFERENCES t_transactions(id) ON DELETE CASCADE,
    match_confidence VARCHAR(20) NOT NULL DEFAULT 'auto',
    linked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_t_transfers_distinct CHECK (from_transaction_id <> to_transaction_id)
);
COMMENT ON TABLE t_transfers IS '口座間振替の相殺リンク（二重計上防止。リンクされた取引は各種集計から除外する）';
COMMENT ON COLUMN t_transfers.id IS '振替リンクID';
COMMENT ON COLUMN t_transfers.from_transaction_id IS '出金側取引ID（t_transactions参照）';
COMMENT ON COLUMN t_transfers.to_transaction_id IS '入金側取引ID（t_transactions参照）';
COMMENT ON COLUMN t_transfers.match_confidence IS '検知方式（auto=自動検知/manual=手動紐付け）';
COMMENT ON COLUMN t_transfers.linked_at IS '紐付け日時';

CREATE TABLE t_asset_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    account_id INTEGER REFERENCES m_accounts(id) ON DELETE CASCADE,
    asset_class_id INTEGER NOT NULL REFERENCES m_asset_classes(id),
    ticker_or_name VARCHAR(255) NOT NULL,
    current_value NUMERIC(12, 2) NOT NULL,
    book_value NUMERIC(12, 2),
    source_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_t_asset_snapshots_date_account_ticker UNIQUE (snapshot_date, account_id, ticker_or_name)
);
COMMENT ON TABLE t_asset_snapshots IS '資産スナップショット（残高追跡対象口座の日次評価額。ローンはマイナス値で記録）';
COMMENT ON COLUMN t_asset_snapshots.id IS 'スナップショットID';
COMMENT ON COLUMN t_asset_snapshots.snapshot_date IS '評価基準日';
COMMENT ON COLUMN t_asset_snapshots.account_id IS '口座ID（m_accounts参照）';
COMMENT ON COLUMN t_asset_snapshots.asset_class_id IS '資産クラスID（m_asset_classes参照）';
COMMENT ON COLUMN t_asset_snapshots.ticker_or_name IS '銘柄コードまたは名称（現金・ローンは口座名をそのまま格納）';
COMMENT ON COLUMN t_asset_snapshots.current_value IS '評価額（時価）。ローンはマイナス値';
COMMENT ON COLUMN t_asset_snapshots.book_value IS '簿価（取得原価。証券のみ使用）';
COMMENT ON COLUMN t_asset_snapshots.source_type IS '取得元（cumulative=初期残高+取引累積/moneyforward=MF連携/manual=手動入力）';
COMMENT ON COLUMN t_asset_snapshots.created_at IS '作成日時';

CREATE TABLE t_batch_logs (
    id SERIAL PRIMARY KEY,
    run_date DATE NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL,
    new_transaction_count INTEGER NOT NULL DEFAULT 0,
    transfer_detected_count INTEGER NOT NULL DEFAULT 0,
    institution_results JSONB,
    error_message TEXT,
    discord_notified_at TIMESTAMP WITH TIME ZONE
);
COMMENT ON TABLE t_batch_logs IS '日次バッチ実行履歴';
COMMENT ON COLUMN t_batch_logs.id IS 'バッチ実行ID';
COMMENT ON COLUMN t_batch_logs.run_date IS '実行対象日';
COMMENT ON COLUMN t_batch_logs.started_at IS '開始日時';
COMMENT ON COLUMN t_batch_logs.finished_at IS '終了日時';
COMMENT ON COLUMN t_batch_logs.status IS '実行結果（success/partial_success/failed）';
COMMENT ON COLUMN t_batch_logs.new_transaction_count IS '新規取込件数';
COMMENT ON COLUMN t_batch_logs.transfer_detected_count IS '振替検知件数';
COMMENT ON COLUMN t_batch_logs.institution_results IS '機関ごとの成否内訳（JSON配列: 機関名/status/件数またはエラー内容）';
COMMENT ON COLUMN t_batch_logs.error_message IS 'バッチ全体レベルのエラー内容（発生時のみ）';
COMMENT ON COLUMN t_batch_logs.discord_notified_at IS 'Discord通知送信日時';

-- ============================================================
-- インデックス
-- ============================================================

CREATE INDEX idx_t_transactions_date ON t_transactions(transaction_date);
CREATE INDEX idx_t_transactions_account_id ON t_transactions(account_id);
CREATE INDEX idx_t_transactions_category_id ON t_transactions(category_id);
CREATE INDEX idx_t_transactions_raw_data ON t_transactions USING gin (raw_data);
CREATE INDEX idx_t_asset_snapshots_date ON t_asset_snapshots(snapshot_date);
```

## 7. フロントエンドUI要件
- **ダッシュボード画面（4主要ウィジェット）**
  1. 純資産額の推移（Line Chart / 時系列。投資性資産＋現金性資産－ローン残高）
  2. 今月の事業経費の進捗（Progress Bar / `m_budgets`に対する消化率。`business_ratio`按分後の金額で計算）
  3. 個人口座のキャッシュフロー（Bar Chart / 収入 vs 支出の比較。振替除外・`business_ratio`按分後）
  4. カテゴリ別の支出金額（Pie or Donut Chart / 割合表示。振替除外）
- **手動補正・トランザクション管理画面**
  - 自動分類の失敗、自動相殺ロジックから漏れた明細の手動紐づけ、事業按分比率の変更を行うためのデータグリッド画面。
  - 「未分類の取引にカテゴリルールを再適用」ボタン。
  - 新規手入力（現金払い等、自動取込元のない取引）は今回のスコープ外（9章参照）。

**実装状況**: Phase 6でバックエンドAPI（`backend/app/api/`）、Phase 7でフロントエンド（`frontend/`）を実装済み。
- ダッシュボード4ウィジェットに対応する`GET /api/dashboard/{net-worth-history,budget-progress,personal-cashflow,category-breakdown}`（`app/services/dashboard_queries.py`）。`budget-progress`/`personal-cashflow`は`business_ratio`按分後、`category-breakdown`は按分せず全額集計（設計判断はADR 0012参照）。いずれも`t_transfers`にリンクされた取引を除外する。
- 取引管理画面向けに`GET /api/transactions`（口座・カテゴリ・期間・未分類フィルタ、ページング、振替有無フラグ付き）、`PATCH /api/transactions/{id}`（category_id・business_ratioの部分更新、存在しないcategory_id指定時は400）、`POST /api/transactions/recategorize`（未分類[category_id IS NULL]の取引にのみカテゴリルールを再適用、`app/services/transaction_queries.py`）。
- 手動補正（振替の手動紐づけ）向けに`GET /api/transfers/unlinked-candidates`（直近7日以内・未リンク取引の候補一覧）、`POST /api/transfers`（金額完全一致・営業日0〜3日以内のみ検証し摘要一致は検証しない手動リンク、`app/services/transfer_management.py`）、`DELETE /api/transfers/{id}`（リンク解除）。手動紐づけが自動検知の条件3[摘要一致]を検証しない理由はADR 0012参照。
- ドロップダウン等の参照用に`GET /api/accounts`・`GET /api/categories`（`app/api/reference.py`）。
- APIリクエスト単位のDBセッションcommit/rollbackは`app/db/session.py`の`get_db()`に集約（正常終了時commit・例外時rollback、ADR 0012）。
- テスト: pytest 115件、カバレッジ97%（実PostgreSQLへSAVEPOINTロールバック方式で接続する既存の`db_session`フィクスチャに加え、FastAPI `TestClient`をDB依存関係ごとオーバーライドする`client`フィクスチャを追加）。

**フロントエンド実装（Phase 7、2026-07-08）**:
- `frontend/`にVite + React 19 + TypeScript 6構成で新規構築。Tailwind CSS v4（`@tailwindcss/vite`）＋shadcn/ui（`components.json`、`style: radix-nova`）でUIコンポーネント基盤を整備し、react-router-dom v7でルーティング（`/`＝ダッシュボード、`/transactions`＝取引管理）、TanStack Query v5でサーバー状態管理、TanStack Table v8で取引データグリッド、Rechartsでチャートを実装。
- APIクライアント層（`src/api/client.ts`・`src/api/types.ts`）を新規実装。**重要な設計判断**: バックエンドの`decimal.Decimal`フィールド（`amount`・`business_ratio`・`net_worth`・`budget_amount`等）は、FastAPIが`response_model`経由でシリアライズする際にJSON数値ではなく**JSON文字列**として返る（精度保持のためPydantic v2のデフォルト挙動）。実際に稼働中のAPIへ`curl`で確認し（例: `{"income":"0","expense":"0"}`）、フロントの型定義もすべて`string`とした上で、チャート描画・金額比較の直前に`Number()`変換するルールを徹底している（`lib/format.ts`の`formatCurrency`/`formatPercent`は`number | string`を受理）。
- ダッシュボード4ウィジェット（`src/features/dashboard/`）: 純資産推移（Line Chart）、予算消化率（Progress Bar、超過時は`--expense`色に切替）、個人キャッシュフロー（Bar Chart、収入=`--income`色/支出=`--expense`色）、カテゴリ別支出（Donut Chart）。いずれもローディング・エラー・空状態を個別に描画。
- 取引管理画面（`src/features/transactions/`）: 口座・カテゴリ・期間・未分類フィルタ、TanStack Tableによるデータグリッド（`getRowId`で取引IDを行キーに固定し、ページ送り・再フェッチ時に別取引へ誤って更新が飛ぶ不具合を防止）、カテゴリ・事業按分率のインライン編集（更新失敗時はエラーメッセージを表示し元の値へ復帰）、「未分類の取引にルールを再適用」ボタン。「振替の手動紐づけ」はタブで分離し、未紐づけ候補から出金側・入金側を選んで`POST /api/transfers`を呼ぶUIを実装（`src/features/transfers/`）。
- **既知の制約**: 振替リンクの解除（`DELETE /api/transfers/{id}`）はバックエンドに実装済みだが、既存リンクの`transfer_id`を取得できる一覧系APIが存在しないため、フロントエンドから解除する手段は未実装（今回のスコープでは新規リンク作成のみ）。将来的に解除UIを追加する場合は、リンク済み振替を一覧できるバックエンドAPIの追加が前提となる。
- 品質確認: `npx tsc -b`（型チェック）・`npx oxlint`・`npm run build`をいずれもクリーンな状態で通過。実際に起動したバックエンド（uvicorn）とフロントエンド（Vite dev server）に対しPlaywrightでダッシュボード・取引管理（両タブ）を操作確認し、コンソールエラー0件を確認。react-reviewer・typescript-reviewerエージェントによるレビューを実施し、指摘（Decimal/文字列型不一致、ページング時の行キー不整合によるミューテーション誤爆、ミューテーション失敗時のエラー握りつぶし、アクセシビリティラベル不足、未使用コード等）をすべて反映済み。
- DB内に実際の取引データがまだ存在しない（Phase 3〜5のバッチが未実行）ため、テーブル・振替候補・チャートはいずれも空状態表示で確認しており、実データでのインタラクション検証（ページング・フィルタ絞り込みの実値確認等）は次回バッチ実行後に別途行う必要がある。

## 8. セキュリティ・インフラ要件
- **環境変数**: `.env`ファイルを利用し、PostgreSQL認証情報、Discord Webhook URL、Gmail用アプリパスワード（個人用・事業用の2組）、MFログイン情報、口座名義文字列（振替検知用）、長期休暇期間の設定を管理（Git管理外とする）。
- **CORS設定**: FastAPI側でフロントエンドからのアクセスを許可するCORSミドルウェアを適切に設定する。
- **アクセス制限**: 簡易的なアクセス制限は不要とし、利便性を優先する（ローカルネットワーク内限定）。

## 9. 未確定・今後検討する拡張ポイント
- マネーフォワードMEスクレイピング自動化（第二段階）の具体的な実装方式・エラー時のリトライ/手動介入フロー。
- 正規表現パース失敗時の低コストLLMフォールバック（Claude Haiku等）導入要否。
- 各クレジットカード会社の実際の速報メールサンプル入手・フォーマット確認（パーサー実装の前提条件）。サンプル入手後は、対象金融機関の`m_institutions.card_alert_sender_email`に送信元アドレスを設定し、`app/services/card_parsers/`に会社別`CardEmailParser`実装を追加してレジストリへ登録する。
- マネーフォワードME資産評価CSVの実サンプル未入手のため、`app/services/mf_assets_csv.py`の列名エイリアスは一般的に知られている表記から推測している。実サンプル入手後に列名マッピングの検証・調整が必要（証券の銘柄種別[国内株式/投資信託]判定もキーワードヒューリスティックであり要検証、ADR 0009関連）。
- 外貨建て資産（米国株・海外ETF等）の原通貨・為替レート分解管理。
- 現金（財布）払いなど、自動取込元のない取引の手動新規登録機能。
- 過去データの遡及取込（現状は稼働開始日以降のみを対象とする）。
