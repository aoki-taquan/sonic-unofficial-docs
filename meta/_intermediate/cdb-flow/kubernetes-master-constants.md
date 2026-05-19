# KUBERNETES_MASTER — ハードコード定数調査ノート (Phase E)

## 調査対象ファイル

- `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py`

---

## タイマー定数 (ctrmgrd.py:112-118)

```python
remote_ctr_config = {
    JOIN_LATENCY: 10,   # ctrmgrd.py:112
    JOIN_RETRY: 10,     # ctrmgrd.py:113
    LABEL_RETRY: 2,     # ctrmgrd.py:114
    TAG_IMAGE_LATEST: 5,# ctrmgrd.py:115
    TAG_RETRY: 5,       # ctrmgrd.py:116
    CLEAN_IMAGE_RETRY: 5,# ctrmgrd.py:117
    USE_K8S_PROXY: ""   # ctrmgrd.py:118
}
```

これらは `/etc/sonic/remote_ctr.config.json` で上書き可能だが、ファイルが存在しない場合はコード埋め込みのデフォルト値がそのまま使われる。

## CONFIG_DB フィールド名定数 (ctrmgrd.py:30-45)

| 変数名 | 値 (文字列) | 用途 |
|--------|------------|------|
| `SERVER_KEY` | `"SERVER"` | KUBERNETES_MASTER テーブルの単一 key |
| `CFG_SER_IP` | `"ip"` | CONFIG_DB フィールド名 |
| `CFG_SER_PORT` | `"port"` | CONFIG_DB フィールド名 |
| `CFG_SER_DISABLE` | `"disable"` | CONFIG_DB フィールド名 |
| `CFG_SER_INSECURE` | `"insecure"` | CONFIG_DB フィールド名 |

## STATE_DB フィールド名定数 (ctrmgrd.py:36-39)

| 変数名 | 値 (文字列) | 用途 |
|--------|------------|------|
| `ST_SER_IP` | `"ip"` | STATE_DB フィールド名 |
| `ST_SER_PORT` | `"port"` | STATE_DB フィールド名 |
| `ST_SER_CONNECTED` | `"connected"` | join 成否フラグ |
| `ST_SER_UPDATE_TS` | `"update_time"` | 最終 join タイムスタンプ |

## 所有者モード定数 (ctrmgrd.py:59-62)

| 変数名 | 値 | 用途 |
|--------|----|------|
| `MODE_KUBE` / `OWNER_KUBE` | `"kube"` | K8s モード識別 |
| `MODE_LOCAL` / `OWNER_LOCAL` | `"local"` | ローカルモード識別 |

## KUBE_LABELS テーブル名定数 (ctrmgrd.py:56-57)

| 変数名 | 値 | 用途 |
|--------|----|------|
| `KUBE_LABEL_TABLE` | `"KUBE_LABELS"` | STATE_DB テーブル名 |
| `KUBE_LABEL_SET_KEY` | `"SET"` | テーブル内の単一 key |

## SELECT_TIMEOUT 定数 (ctrmgrd.py:181)

```python
SELECT_TIMEOUT = 1000  # ms
```

メインループの swsscommon `Select.select()` タイムアウト値。1000ms 間隔でイベント待機する。

## 設定ファイルパス定数 (ctrmgrd.py:23)

```python
SONIC_CTR_CONFIG = "/etc/sonic/remote_ctr.config.json"
```

タイマー定数の外部上書き用 JSON ファイルパス。ハードコードされているため、このパス以外にファイルを置いても読み込まれない。

## デフォルトポート定数 (ctrmgrd.py:74)

`CFG_SER_PORT` のデフォルト値 `"6443"` は YANG の `default` 宣言 (`sonic-kubernetes_master.yang:40-41`) とも一致している。
