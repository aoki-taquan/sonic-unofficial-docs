# MACSEC_PROFILE 暗黙参照分析 (Phase C)

ソース: `sonic-swss/cfgmgr/macsecmgr.cpp`

## 概要

`MACSEC_PROFILE` テーブルは名前参照の受け側であり、CONFIG_DB 内の複数テーブルおよびコンテナ外プロセスから暗黙的に参照される。

## 暗黙参照元

### 1. PORT テーブル（`macsec` フィールド）

- **参照箇所**: `macsecmgr.cpp` L480 `get_value(port_attr, "macsec", profile_name)`
- **参照方法**: `CFG_PORT_TABLE_NAME` (SET) イベントを受けた `enableMACsec()` が `port_attr` の `macsec` フィールドを読み、`m_profiles.find(profile_name)` でプロファイルを検索
- **依存関係**: `PORT` エントリの `macsec` フィールドに記載されたプロファイル名が `MACSEC_PROFILE` に存在しない場合、`task_need_retry` が返却されポートの MACsec は有効化されない（L489-495）
- **タスクマップ登録**:
  ```cpp
  { { CFG_PORT_TABLE_NAME, SET_COMMAND }, &MACsecMgr::enableMACsec},
  { { CFG_PORT_TABLE_NAME, DEL_COMMAND }, &MACsecMgr::disableMACsec},
  ```

### 2. MACSEC_SC テーブル（間接参照）

- **参照経路**: `configureMACsec()` が `wpa_supplicant` に `interface_add` → `add_network` → `enable_network` を送信後、`wpa_supplicant` が MKA セッションを確立し、`macsecorch` が APPL_DB 経由で MACsec SC (Secure Channel) オブジェクトを SAI に作成
- **SC への影響フィールド**:
  - `send_sci` → `macsec_include_sci` (SCI を SC フレームに含めるか)
  - `policy` → `macsec_integ_only` (SC の暗号化モード)
  - `cipher_suite` → `macsec_ciphersuite` (SC で使用するアルゴリズム)

## wpa_supplicant 連携

`macsecmgr` は MACsec のコントロールプレーンとして `wpa_supplicant` を外部プロセスとして起動・管理する。

### 起動フロー

1. `startWPASupplicant(sock)`: `fork()` → 子プロセスで `/sbin/wpa_supplicant -g <sock>` を実行
2. 親プロセスは `wpa_cli_exec(sock, "", "", "status")` でソケット疎通を確認（最大 `retry_time` 回ポーリング）
3. 疎通確認成功後、`configureMACsec()` で `wpa_cli` コマンドを逐次送信

### `wpa_cli` に渡す MACSEC_PROFILE フィールドのマッピング

| MACSEC_PROFILE フィールド | wpa_cli パラメータ | 備考 |
|--------------------------|-------------------|------|
| `primary_cak` | `mka_cak` | `decodeKey()` でデコード後に設定 |
| `primary_ckn` | `mka_ckn` | そのまま設定 |
| `priority` | `mka_priority` | MKA アクター優先度 |
| `rekey_period` | `mka_rekey_period` | 0 の場合は設定しない |
| `cipher_suite` | `macsec_ciphersuite` | enum 文字列をそのまま渡す |
| `send_sci` | `macsec_include_sci` | bool → 0/1 変換 |
| `enable_replay_protect` | `macsec_replay_protect` | bool → 0/1 変換 |
| `replay_window` | `macsec_replay_window` | `enable_replay_protect=true` 時のみ |
| `policy` | `macsec_integ_only` | `INTEGRITY_ONLY` → 1, `security` → 0 |

### 停止フロー

`stopWPASupplicant(pid)` で `SIGTERM` → `unconfigureMACsec()` が `interface_remove` を送信。失敗時は最大 3 回リトライ（`MAX_INTERFACE_REMOVE_RETRIES = 3`）。

## 依存グラフ（暗黙参照）

```
CONFIG_DB:PORT (macsec フィールド)
  └─ 名前参照 ──▶ CONFIG_DB:MACSEC_PROFILE
                       │
                       │ (macsecmgrd が読み取り)
                       ▼
                  wpa_supplicant (外部プロセス)
                       │ MKA セッション確立
                       ▼
                  APPL_DB:APP_MACSEC_TABLE
                       │
                       ▼
                  macsecorch → SAI sai_macsec_api
                       │ SC (Secure Channel) オブジェクト作成
                       ▼
                  CONFIG_DB:MACSEC_SC (間接生成)
```

## 注意事項

- `MACSEC_PROFILE` エントリを削除しようとしたとき、同名プロファイルを使用中のポートが存在する場合は `task_failed` が返却され削除は拒否される
- プロファイル更新時（`loadProfile` の `update()` 呼び出し）は、当該プロファイルを使用中の全ポートに対して MACsec を再設定する
