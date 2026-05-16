# KUBERNETES_MASTER フィールドデフォルト調査 (Phase A)

調査日: 2026-05-14
対象ページ: docs/reference/config-db/kubernetes-master.md
ブランチ: chore/q67-f-phaseA-kubernetes-master

## ソース確認

### YANG 定義
ファイル: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-kubernetes_master.yang`
ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd

```yang
leaf port {
    type inet:port-number;
    default 6443;           // YANG L40-41
}
leaf disable {
    type stypes:boolean_type;
    default "false";        // YANG L47
}
leaf insecure {
    type stypes:boolean_type;
    default "true";         // YANG L53
}
```

`ip` は YANG に `default` 宣言なし (必須項目扱い)。

### ctrmgrd.py ランタイムデフォルト
ファイル: `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py` L72-77

```python
dflt_cfg_ser = {
    CFG_SER_IP:      "",        # 空文字列 — 未設定時
    CFG_SER_PORT:    "6443",    # 文字列 "6443"
    CFG_SER_DISABLE: "false",   # 文字列 "false"
    CFG_SER_INSECURE:"true"     # 文字列 "true"
}
```

### config/kube.py CLI ユーティリティ
ファイル: `sonic-utilities/config/kube.py` L27-32

```python
def_data = {
    KUBE_SERVER_IP:      "",       # 空文字列
    KUBE_SERVER_PORT:    "6443",   # 文字列
    KUBE_SERVER_INSECURE:"True",   # 先頭大文字 (CLIレイヤー)
    KUBE_SERVER_DISABLE: "False"   # 先頭大文字 (CLIレイヤー)
}
```

注: CLI レイヤーは `"True"/"False"` (先頭大文字)、YANG / ctrmgrd は `"true"/"false"` (小文字)。
ConfigDB 格納値は比較時に大文字小文字を区別しない処理になっている。

## デフォルト値まとめ

| フィールド | YANG default | ctrmgrd dflt_cfg_ser | CLI def_data | 格納型 |
|-----------|-------------|----------------------|--------------|--------|
| `ip`      | (なし)       | `""` (空文字)        | `""` (空文字) | inet:host |
| `port`    | `6443`      | `"6443"`             | `"6443"`      | inet:port-number (uint16) |
| `disable` | `"false"`   | `"false"`            | `"False"`     | boolean_type (文字列) |
| `insecure`| `"true"`    | `"true"`             | `"True"`      | boolean_type (文字列) |

## defaults ブロック用テキスト

```
<!-- defaults -->
## フィールドデフォルト

| フィールド | デフォルト値 | ソース |
|-----------|------------|--------|
| `ip` | (なし — 空文字) | ctrmgrd.py L73; `ip` は YANG に default 宣言なし |
| `port` | `6443` | sonic-kubernetes_master.yang L40-41; ctrmgrd.py L74 |
| `disable` | `"false"` | sonic-kubernetes_master.yang L47; ctrmgrd.py L75 |
| `insecure` | `"true"` | sonic-kubernetes_master.yang L53; ctrmgrd.py L76 |

> **注**: CLI レイヤー (`config/kube.py`) は `"True"/"False"` (先頭大文字) で書き込む場合がある。
> ConfigDB の比較ロジックは大文字小文字を区別せずに処理する。
<!-- /defaults -->
```
