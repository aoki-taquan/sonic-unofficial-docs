# VLAN テーブル — 例外条件・特殊挙動

## スキーマ検証

- **キー形式**: `Vlan<2..4094>` パターン。`Vlan` プレフィクスがない場合 `vlanmgr` は `SWSS_LOG_ERROR("Invalid key format. No 'Vlan' prefix")` を出力してエントリを破棄する[^e1]。
- **ID 数値検証**: `Vlan` 以降が数値でない場合同様に破棄[^e1]。
- **`vlanid` 整合性**: YANG `must "substring-after(../name, 'Vlan') = current()"` — `name` 末尾と `vlanid` フィールドが不一致の場合 YANG バリデーションが `The vlanid must correspond to the VLAN name` エラーで reject する[^e2]。

## ignore / skip

- **warm-restart 時の重複**: VLAN が STATE_DB に既存かつ `m_vlans` セットにも登録済みの場合、`vlanmgr` は再作成をスキップして `m_vlanReplay` から削除のみ行う（"already created" デバッグログ）[^e1]。
- **MTU**: `mtu` フィールドはホスト VLAN への適用が TODO 扱い。`vlanmgr` は受け取るが `SWSS_LOG_DEBUG("Host VLAN mtu setting to be supported.")` のみ出力し実際の netdev MTU は変更しない[^e1]。

## デフォルト補完

- `mtu` 省略時: `DEFAULT_MTU_STR`（通常 `9100`）が使われる[^e1]。
- `mac` 省略時: `gMacAddress`（スイッチ MAC）が自動補完される[^e1]。

[^e1]: `sonic-swss/cfgmgr/vlanmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/vlanmgr.cpp>
[^e2]: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang` <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vlan.yang>
