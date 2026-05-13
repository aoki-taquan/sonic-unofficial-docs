# RADIUS — 値依存挙動分析

## Phase 1: YANG フィールド全列挙

- `passkey`: 文字列 (1..65 chars、SPACE/`#`/`,` 不可)
- `auth_type`: enum `pap` / `chap` / `mschapv2`。デフォルト `pap`。
- `src_ip`: `inet:ip-address`
- `nas_ip`: `inet:ip-address`
- `statistics`: boolean
- `timeout`: uint16 (1..60)。デフォルト `5`。
- `retransmit`: uint8 (0..10)。デフォルト `3`。

## Phase 2: per-value 挙動

### `auth_type` 値別挙動
| 値 | 挙動 |
|----|------|
| `pap` | PAM に `pap` で展開。デフォルト。平文パスワード認証。 |
| `chap` | CHAP チャレンジ認証。NAS 側も CHAP 対応必要。 |
| `mschapv2` | MS-CHAPv2 認証。Active Directory 連携で主に使用。 |

### `statistics` 値別挙動
| 値 | 挙動 |
|----|------|
| `true` / `True` / `yes` / `1` | `is_true()` で True。AAA.authentication.login に `radius` が含まれる場合に統計サービス起動。 |
| その他 | False 扱い。統計サービス起動しない。 |

### `timeout` 範囲挙動
| 値 | 挙動 |
|----|------|
| 1..60 | 有効。pam_radius_auth.conf に反映。 |
| 0 または 61+ | YANG 制約違反。ロード拒否。 |

### `retransmit` 値別挙動
| 値 | 挙動 |
|----|------|
| 0..10 | 有効。再送回数として pam_radius_auth.conf に反映。 |
| 11+ | YANG 制約違反。ロード拒否。 |

## Phase 3: ソース確認

- `sonic-host-services/scripts/hostcfgd`: `RADIUS_SERVER_AUTH_TYPE_DEFAULT = "pap"`、`is_true()` で boolean 変換（`True/true/yes/1` が True）、`radius_global_update()` は key が `global` でない場合サイレントスキップ。

## enum 有無

- `auth_type`: YANG enum `pap` / `chap` / `mschapv2`
- `statistics`: YANG boolean（`is_true()` で処理）
