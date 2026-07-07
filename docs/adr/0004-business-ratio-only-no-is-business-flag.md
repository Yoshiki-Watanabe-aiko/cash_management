# 事業性は取引ごとの business_ratio のみで表現し、is_business フラグは廃止する

当初案では `t_transactions.is_business`（真偽値）と `business_ratio`（0〜100%）を両方持っていたが、両者が矛盾しうる（例: `is_business=false`かつ`business_ratio=50`）。事業性は`business_ratio > 0`として導出できるため、取引レベルの`is_business`は廃止し`business_ratio`一本に統一した。同じ理由で`m_categories.is_business`（カテゴリを事業専用/個人専用に固定するフラグ）も廃止し、カテゴリは個人・事業どちらの取引にも使える中立的な分類とした。`business_ratio`はNULLを許容せず、取引作成時に口座の`m_accounts.default_business_ratio`を必ず継承する（未判定という第3の状態は持たない）。`m_accounts.is_business`（口座自体の分類）と`m_budgets.is_business`（予算の区分）は別概念として残す。
