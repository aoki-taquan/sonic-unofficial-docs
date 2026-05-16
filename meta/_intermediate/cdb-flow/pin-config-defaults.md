# Phase A: pin-config (P4RT テーブル) フィールドデフォルト調査

調査日: 2026-05-15

## 調査対象

CONFIG_DB テーブル: `P4RT`
サブキー: `P4RT|certs`, `P4RT|p4rt_app`

## ソースコード調査

### 1. p4rt.sh (主要デフォルト判定ロジック)

ソース: `sonic-buildimage/dockers/docker-sonic-p4rt/p4rt.sh`

起動スクリプトが CONFIG_DB から `P4RT|p4rt_app` を読み込み、各フィールドを `jq -r '.field // empty'` で取得する。
フィールドが未設定（空文字）の場合、対応する `--flag` が `p4rt` バイナリに渡されず、
バイナリ内でコンパイル時デフォルト値が使用される。

| 行 | フィールド | fallback 動作 |
|----|-----------|----------------|
| L66-69 | `port` | 未設定 → `--p4rt_grpc_port` 引数なし → バイナリ default (9559) |
| L72-75 | `use_genetlink` | 未設定 → `--use_genetlink` 引数なし → バイナリ default (false) |
| L78-81 | `use_port_ids` | 未設定 → `--use_port_ids` 引数なし → バイナリ default (false) |
| L84-87 | `save_forwarding_config_file` | 未設定 → `--save_forwarding_config_file` 引数なし → 保存しない |
| L60-63 | `authz_policy` | 未設定 → `--authz_policy_enabled` / `--authorization_policy_file` 引数なし → authz 無効 |
| L90-97 | `p4rt_unix_socket` | 未設定 → `--p4rt_unix_socket` 引数なし → UNIX socket リスナーなし |

### 2. 証明書 (P4RT|certs)

| 行 | フィールド | fallback 動作 |
|----|-----------|----------------|
| L22-27 | `server_crt` / `server_key` | 両方または片方が空 → `--use_insecure_server_credentials` |
| L30-37 | `ca_crt` | 未設定 → mTLS なし |
| L33-37 | `cert_crl_dir` | 未設定 → CRL チェックなし |

`P4RT|certs` エントリが存在しない場合、DEVICE_METADATA|localhost の `x509` エントリを代わりに参照する
（`p4rt_vars.j2` L4）。両方とも存在しない場合 `--use_insecure_server_credentials` が適用される（L56）。

### 3. YANG モデル

`sonic-buildimage/src/sonic-yang-models/yang-models/` に P4RT 専用 YANG モデルなし。
スキーマ強制なし。フィールドは `p4rt.sh` 内の `jq` 参照のみで定義される。

### 4. HLD 記述値 (p4rt_app_hld.md)

```json
"P4RT": {
  "certs": {
    "server_crt": "/keys/server_cert.lnk",
    "server_key": "/keys/server_key.lnk",
    "ca_crt": "/keys/ca_cert.lnk",
    "cert_crl_dir": "/keys/crl"
  },
  "p4rt_app": {
    "port": "9559",
    "use_genetlink": "false",
    "use_port_ids": "false",
    "save_forwarding_config_file": "/etc/sonic/p4rt_forwarding_config.pb.txt",
    "authz_policy": "/keys/authorization_policy.json"
  }
}
```

出典: `SONiC/doc/pins/p4rt_app_hld.md` L174-189

## 結論: フィールドデフォルト表

### P4RT|p4rt_app

| フィールド | 記述デフォルト | コード動作 | 乖離 |
|-----------|--------------|------------|------|
| `port` | `"9559"` (HLD) | 未設定→バイナリ側デフォルト (9559) | なし |
| `use_genetlink` | `"false"` (HLD) | 未設定→バイナリ側 false | なし |
| `use_port_ids` | `"false"` (HLD) | 未設定→バイナリ側 false | なし |
| `save_forwarding_config_file` | パス指定 (HLD) | 未設定→保存しない | なし (optional) |
| `authz_policy` | パス指定 (HLD) | 未設定→authz 無効 | なし (optional) |
| `p4rt_unix_socket` | (HLD 未記載) | 未設定→UNIX socket なし | — |

### P4RT|certs

| フィールド | 記述デフォルト | コード動作 | 乖離 |
|-----------|--------------|------------|------|
| `server_crt` | パス指定 (HLD) | 未設定→insecure モード | なし (optional) |
| `server_key` | パス指定 (HLD) | 未設定→insecure モード | なし (optional) |
| `ca_crt` | パス指定 (HLD) | 未設定→mTLS なし | なし (optional) |
| `cert_crl_dir` | パス指定 (HLD) | 未設定→CRL なし | なし (optional) |

**隠れデフォルト**: `certs` エントリが存在しない場合、`DEVICE_METADATA|localhost|x509` へのフォールバックが発生
（`p4rt_vars.j2` L4）。これは YANG 未定義の動作でドキュメント化が必要。

## evidence refs

- `sonic-buildimage/dockers/docker-sonic-p4rt/p4rt.sh`
- `sonic-buildimage/dockers/docker-sonic-p4rt/p4rt_vars.j2`
- `SONiC/doc/pins/p4rt_app_hld.md` L168-194
