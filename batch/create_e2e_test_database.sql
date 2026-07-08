-- Playwright E2Eテスト専用データベースの一度きりのセットアップ用SQL。
-- postgresスーパーユーザー(pgAdmin等)で一度だけ実行してください。
-- cash_mgmt_userはCREATEDB権限を持たないため、専用データベースの作成のみ
-- 管理者権限で行い、以降のスキーマ作成・破棄・再作成はcash_mgmt_userの
-- オーナー権限でPlaywrightのglobal setupが自動的に行う。
--
-- 実行方法: pgAdmin等でpostgresデータベースに接続し、このファイルの内容を実行する。

CREATE DATABASE cash_management_test OWNER cash_mgmt_user;
