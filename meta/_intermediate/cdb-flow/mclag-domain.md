# CONFIG_DB 例外条件分析: MCLAG_DOMAIN

## Consumer

- `mclagsyncd` / `MclagLink` (`sonic-swss/mclagsyncd/mclaglink.cpp`): `MCLAG_DOMAIN` テーブルを購読し、iccpd プロセスへ CFG メッセージを転送。

## 例外条件

### 1. domain_id が 1-4095 の範囲外 → YANG が拒否
- ソース: `sonic-mclag.yang` — `range "1..4095"` / `error-message "MCLAG Domain ID out of range"`。
- YANG バリデーション段階で弾かれる。

### 2. keepalive_interval が 1-60 の範囲外 → YANG が拒否
- ソース: `sonic-mclag.yang` — `range "1..60"` / `default 1`。

### 3. session_timeout が 1-3600 の範囲外 → YANG が拒否
- ソース: `sonic-mclag.yang` — `range "1..3600"` / `default 30`。

### 4. `keepalive_interval * 3 > session_timeout` → YANG must 制約違反
- ソース: `sonic-mclag.yang` — `must "(keepalive_interval * 3) <= session_timeout"` / `error-message "(keepalive interval * 3) <= session_timeout value"`。
- 違反はバリデーション段階で拒否される。

### 5. 変更差分なし → mclagsyncd が重複更新を無視
- ソース: `mclaglink.cpp` L812 付近 — `!attrBmap && !attrDelBmap` の場合 `"no change - duplicate update"` を SWSS_LOG_NOTICE してリターン。

### 6. 存在しないドメインの DEL → SWSS_LOG_WARN + return
- ソース: `mclaglink.cpp` L836 — `"Domain [%d] deletion - domain not found"` を WARN ログし処理を終了。iccpd へは送信されない。

### 7. 既存エントリへの SET 時: source_ip / peer_ip / peer_link は差分のみ反映
- ソース: `mclaglink.cpp` L749-L795 — 既存エントリとの比較で変化があるフィールドのみ `attrBmap` に立て、変化がない場合は iccpd への通知を省略。
- 空文字列でフィールドを上書きした場合は `attrDelBmap` に立てて `MCLAG_CFG_OPER_ATTR_DEL` を発行。
