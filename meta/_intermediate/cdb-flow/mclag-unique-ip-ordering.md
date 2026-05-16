# MCLAG_UNIQUE_IP ordering 調査ノート (Phase B)

## 調査対象ファイル

- `sonic-swss/mclagsyncd/mclaglink.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mclag.yang` @ 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
- `sonic-utilities/config/mclag.py` @ 39732bceb8bdefe706518ab40623bbbba6ff33b9

## YANG 制約

`sonic-mclag.yang:132-134`:
```yang
must "count(../../MCLAG_DOMAIN/MCLAG_DOMAIN_LIST/domain_id) != 0" {
    error-message "mclag not configured";
    error-app-tag mclag-invalid;
}
```
→ MCLAG_DOMAIN が 0 件の場合 YANG バリデーション段階で MCLAG_UNIQUE_IP 書込み拒否。

`sonic-mclag.yang:144-152`: `if_name` は `Vlan<id>` パターンの plain string (leafref は libyang back-links 制約でコメントアウト)。

## CLI チェック (config/mclag.py L327-351)

`config mclag unique-ip add <if>`:
1. `MCLAG_DOMAIN` テーブルが 0 件 → `ctx.fail("MCLAG not configured.")`
2. `if_name` が "Vlan" プレフィックスを持たない → `ctx.fail()`
3. 対象 VLAN IF に非デフォルト VRF バインド済み → `ctx.fail()`
4. 対象 VLAN IF に IP アドレス設定済み → `ctx.fail()`
5. 上記をパスした場合のみ `db.set_entry('MCLAG_UNIQUE_IP', ..., {'unique_ip':'enable'})`

## mclagsyncd 購読タイミング

`addDomainCfgDependentSelectables()` (L910-950):
- MCLAG_DOMAIN の**初回 SET 成功後に呼ばれる** (L903-907: `if (add_cfg_dependent_selectables)`)
- この関数内で `p_mclag_unique_ip_cfg_tbl = new SubscriberStateTable(...)` を生成し `m_select->addSelectable()` する
- 逆に `delDomainCfgDependentSelectables()` (L952-969) は MCLAG_DOMAIN DEL 時に購読停止 + テーブル削除

→ **MCLAG_DOMAIN の初回 SET 完了前に MCLAG_UNIQUE_IP を書いても mclagsyncd は購読しておらず iccpd に通知が届かない**。

## 削除順序

`config/mclag.py` `del_mclag_unique_ip` (L353-377):
- VLAN IF に VRF または IP が存在する状態での DEL も CLI がチェックして拒否する（VRF/IP を先に外す必要あり）
- MCLAG_DOMAIN DEL 前に MCLAG_UNIQUE_IP DEL を実行するのが推奨。YANG `must` は DEL 操作には適用されないが mclagsyncd が購読停止するため iccpd 側での削除通知が届かなくなるリスクあり。

## バッファフラッシュ条件

`mclagsyncdSendMclagUniqueIpCfg()` (L1088-1181):
- `MCLAG_MAX_SEND_MSG_LEN - infor_len < sizeof(mclag_unique_ip_cfg_info)` の場合、途中フラッシュしてから残りを送信。
- `infor_len <= sizeof(mclag_msg_hdr_t)` の場合（entries 全て空 / key parse 失敗のみ）は送信不要として return。

## 結論

順序依存関係:
1. VLAN IF に IP/VRF が存在する → MCLAG_UNIQUE_IP 設定不可 (CLI 拒否)
2. MCLAG_DOMAIN が 0 件 → YANG must 制約 + CLI チェックで拒否
3. MCLAG_DOMAIN 初回 SET 後 → mclagsyncd が MCLAG_UNIQUE_IP を購読開始
4. MCLAG_UNIQUE_IP DEL → MCLAG_DOMAIN DEL の順序が推奨
