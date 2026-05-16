# PORT.macsec フィールド — Phase A コード由来デフォルト調査

## 調査対象

`PORT` テーブルの `macsec` フィールド — ポートに適用する `MACSEC_PROFILE` 名を指定する leafref フィールド。

## 調査ソース

| ソース | パス | 備考 |
|--------|------|------|
| Manager ソース | `sonic-swss/cfgmgr/macsecmgr.cpp` | `enableMACsec()` 実装 |
| CLI プラグイン | `sonic-buildimage/dockers/docker-macsec/cli/config/plugins/macsec.py` | `add_port` / `del_port` |
| YANG モデル | `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-port.yang` | `leaf macsec` 定義 |

## YANG 定義 (sonic-port.yang 行 233-238)

```yang
leaf macsec {
    description "MACsec profile name applied to the port.";
    type leafref {
        path "/macsec:sonic-macsec/macsec:MACSEC_PROFILE/macsec:MACSEC_PROFILE_LIST/macsec:name";
    }
}
```

- `default` ステートメント: **なし**
- `mandatory`: **なし** (省略可)

## C++ コード (macsecmgr.cpp enableMACsec 行 479-485)

```cpp
std::string profile_name;
if (!get_value(port_attr, "macsec", profile_name)
    || profile_name.empty())
{
    SWSS_LOG_DEBUG("MACsec field of port '%s' is empty", port_name.c_str());
    return disableMACsec(port_name, port_attr);
}
```

- フィールドが存在しない、または空文字 → `disableMACsec()` を呼ぶ = MACsec 無効
- コードデフォルト: **省略時 = MACsec 無効** (明示的なデフォルト値は存在しない)

## CLI (macsec.py add_port / del_port)

```python
# add: PORT.macsec にプロファイル名を書き込む
port_entry['macsec'] = profile
config_db.set_entry("PORT", port, port_entry)

# del: PORT.macsec フィールドを削除する
del port_entry['macsec']
config_db.set_entry("PORT", port, port_entry)
```

- `add_port` は `profile` 引数が必須 (required=True) — デフォルト値なし
- `del_port` は `macsec` フィールドを削除する = MACsec 無効に戻す

## まとめ

| フィールド | デフォルト値 | 根拠 |
|-----------|------------|------|
| `macsec` | — (省略可) | YANG `default` なし / C++ フィールド不在時 `disableMACsec()` / CLI mandatory 引数 |

**discrepancy なし**: YANG・C++・CLI いずれも「省略時 = MACsec 無効」という挙動で一致。
明示的なデフォルト値（文字列）は存在せず、フィールドの有無が MACsec の有効/無効を制御する。
