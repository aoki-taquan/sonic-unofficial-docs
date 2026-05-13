# VLAN_MEMBER テーブル — 例外条件・特殊挙動

## スキーマ検証

- **キー形式**: `Vlan<id>|<port>` 形式であること。`Vlan` プレフィクスがない、またはポート名が含まれない場合 `vlanmgr` はエラーを記録してエントリを破棄する[^e1]。
- **`tagging_mode`**: `untagged` / `tagged` / `priority_tagged` 以外の値は `SWSS_LOG_ERROR("Wrong tagging_mode")` で破棄される[^e1]。

## ignore / skip

- **VLAN / ポート未 ready**: `isVlanStateOk()` または `isMemberStateOk()` が false の場合リトライ待ち（"not ready, delaying"）[^e1]。
- **重複エントリ**: STATE_DB に既存の場合は `m_vlanMemberReplay` から削除のみ（"already set"）[^e1]。
- **重複キー**: consumer pipe 内の重複キーは `SWSS_LOG_WARN("Duplicate key found")` でスキップ[^e1]。

## デフォルト補完

- `tagging_mode` 省略時: `"untagged"` が補完される[^e1]。

[^e1]: `sonic-swss/cfgmgr/vlanmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/vlanmgr.cpp>
