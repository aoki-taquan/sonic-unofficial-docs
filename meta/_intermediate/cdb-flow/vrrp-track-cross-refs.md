# VRRP_TRACK テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/vrrp-track.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/SONiC/doc/vrrp/sonic-vrrp.yang` および `sonic-net/sonic-utilities/config/main.py`。

## スキャン手順

```bash
# YANG leafref 解析 (VRRP_TRACK コンテナ)
grep -n "leafref\|path\|trackifname\|baseifname\|idkey" \
    .cache/sonic-sources/SONiC/doc/vrrp/sonic-vrrp.yang | sed -n '130,180p'

# CLI 存在確認コード
grep -n "get_interface_table_name\|get_table\|get_entry\|ctx.fail" \
    .cache/sonic-sources/sonic-utilities/config/main.py | grep -A2 -B2 "track"
```

## 検出された参照テーブル

### YANG leafref (VRRP_TRACK_LIST)

`sonic-vrrp.yang` の `VRRP_TRACK` コンテナ (L135-183) に定義された leafref。
`sonic-yang-mgmt` / gNMI 経路でバリデーションされる。

| フィールド | 参照先テーブル | YANG path (抜粋) | evidence |
|---|---|---|---|
| `baseifname` | `VRRP/VRRP_LIST/ifname` (親 VRRP インスタンス) | `../../../VRRP/VRRP_LIST/ifname` | `sonic-vrrp.yang` L144-146 |
| `idkey` | `VRRP/VRRP_LIST/idkey` (親 VRRP インスタンス) | `../../../VRRP/VRRP_LIST/idkey` | `sonic-vrrp.yang` L150-152 |
| `trackifname` (PORT) | `PORT/PORT_LIST/ifname` | `/sonic-port/PORT/PORT_LIST/ifname` | `sonic-vrrp.yang` L158-160 |
| `trackifname` (PortChannel) | `PORTCHANNEL/PORTCHANNEL_LIST/name` | `/sonic-portchannel/PORTCHANNEL/PORTCHANNEL_LIST/name` | `sonic-vrrp.yang` L161-163 |
| `trackifname` (VLAN) | `VLAN/VLAN_LIST/name` | `/sonic-vlan/VLAN/VLAN_LIST/name` | `sonic-vrrp.yang` L164-166 |
| `trackifname` (Sub-IF) | `VLAN_SUB_INTERFACE/VLAN_SUB_INTERFACE_LIST/id` | `/sonic-interface/VLAN_SUB_INTERFACE/…` | `sonic-vrrp.yang` L167-169 |

### CLI 実行時存在確認 (config/main.py)

`add_track_interface()` (L6993-7040) が YANG バリデーションとは独立して実行する存在チェック。

| 確認対象テーブル | 確認タイミング | 失敗時の挙動 | evidence |
|---|---|---|---|
| `INTERFACE` / `PORTCHANNEL_INTERFACE` / `VLAN_INTERFACE` (base) | VRRP_TRACK 追加時 (ベースインタフェース確認) | `ctx.fail("Router Interface '{}' not found")` で永続拒絶 | `config/main.py:7000-7006` |
| `INTERFACE` / `PORTCHANNEL_INTERFACE` / `VLAN_INTERFACE` (track) | VRRP_TRACK 追加時 (追跡インタフェース確認) | `ctx.fail("Router Interface '{}' not found")` で永続拒絶 | `config/main.py:7007-7015` |
| `VRRP` (親インスタンス) | VRRP_TRACK 追加時 | `ctx.fail("vrrp instance {} not found on interface {}")` で永続拒絶 | `config/main.py:7017-7019` |

### データ流出先

VRRP_TRACK への書き込みは直接 APPL_DB / ASIC_DB には流れない。
FRR `vrrpd` が CONFIG_DB.VRRP_TRACK を読み込み、zebra 経由のインタフェース状態変化通知と組み合わせて priority を再計算。その結果は VRRP Advertisement パケットとして送出される（DB 書き込みではなくパケット送出）。

| 流出先 | 経路 |
|---|---|
| FRR vrrpd 内部メモリ (priority 計算) | CONFIG_DB.VRRP_TRACK → vrrpd track 設定読み込み |
| VRRP Advertisement パケット (priority フィールド更新) | vrrpd priority 再計算 → パケット送出 |
