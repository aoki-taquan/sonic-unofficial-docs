# KUBERNETES_MASTER テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/kubernetes-master.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py`。
`KUBERNETES_MASTER` テーブル変化時に `ctrmgrd` が間接的に読み書きする DB テーブルを列挙する。

## スキャン手順

```
grep -nE 'get_db_entry|mod_db_entry|set_db_entry|register_handler|SubscriberStateTable' \
    .cache/sonic-sources/sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py
```

## 検出された暗黙参照テーブル

### CONFIG_DB 参照

| テーブル | キー | 参照種別 | 用途 | evidence |
|---|---|---|---|---|
| `DEVICE_METADATA` | `localhost` | get_db_entry (起動時) | Kubernetes ノードラベル生成時に `type`（deployment_type）を読み出し `STATE_DB:KUBE_LABELS\|SET.deployment_type` に書き込む | ctrmgrd.py:297-299 |
| `FEATURE` | `<feature>` | subscribe (FeatureTransitionHandler) | `set_owner` フィールド変化でラベル add/drop とサービス再起動を判断 | ctrmgrd.py:471-472 |

### STATE_DB 参照 (読み出し)

| テーブル | キー | 参照種別 | 用途 | evidence |
|---|---|---|---|---|
| `KUBERNETES_MASTER` | `SERVER` | get_db_entry (起動時) | `update_time` 有無で JOIN_LATENCY 適用分岐（初回起動判定） | ctrmgrd.py:341-342 |
| `FEATURE` | `<feature>` | subscribe (FeatureTransitionHandler) | `ct_owner`/`remote_state` を読み出して handle_update() に渡す | ctrmgrd.py:473-474 |

### STATE_DB 書き込み (ctrmgrd が連動して更新)

| テーブル | キー | 書込元 | 内容 | evidence |
|---|---|---|---|---|
| `KUBERNETES_MASTER` | `SERVER` | RemoteServerHandler | `connected`, `update_time`, `ip`, `port` を反映 | ctrmgrd.py:413-414 |
| `KUBE_LABELS` | `SET` | set_node_labels() | `sonic_version`, `hwsku`, `deployment_type`, `worker.sonic/platform` を書き込み（join 成功後） | ctrmgrd.py:306-307 |
| `KUBE_LABELS` | `SET` | FeatureTransitionHandler | `<feat>_enabled` を true/false で書き込み（`set_owner=kube` 判断） | ctrmgrd.py:505-506 |
| `FEATURE` | `<feature>` | restart_systemd_service() | `restart=true` を書き込み（サービス再起動トリガー） | ctrmgrd.py:157-158 |

## YANG 上の leafref 参照

`sonic-kubernetes_master.yang` には `leafref` 宣言は存在しない。YANG レベルでの暗黙参照はなし。
フィールド型は `inet:host`（ip）、`inet:port-number`（port）、`stypes:boolean_type`（disable/insecure）のみ。

## まとめ — `kubernetes-master.md` Phase C 記載対象

| カテゴリ | テーブル / キー |
|---|---|
| CONFIG_DB 読み出し（起動時 get） | `DEVICE_METADATA\|localhost` (`.type`) |
| CONFIG_DB subscribe 連動 | `FEATURE` (全キー — `set_owner` フィールド) |
| STATE_DB 読み出し（起動時 get） | `STATE_DB:KUBERNETES_MASTER\|SERVER` (`.update_time`) |
| STATE_DB subscribe 連動 | `STATE_DB:FEATURE` (全キー — `ct_owner` / `remote_state`) |
| STATE_DB 書き込み（副作用） | `STATE_DB:KUBE_LABELS\|SET`, `STATE_DB:KUBERNETES_MASTER\|SERVER`, `STATE_DB:FEATURE` |
