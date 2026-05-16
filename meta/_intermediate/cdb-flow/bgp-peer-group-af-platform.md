# BGP_PEER_GROUP_AF — Phase H: プラットフォーム差分調査

## 調査対象

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/*/policies.conf.j2`（sentinels / monitors / dynamic / internal / voq_chassis）

## 調査方法

1. `frrcfgd.py` 全体で `platform` / `hwsku` / `asic_type` / `sonic_platform` キーワードを grep → ヒットなし
2. `frrcfgd.py` の `DEVICE_METADATA` 参照箇所（L2162–2170）を確認 → `bgp_asn` と `docker_routing_config_mode` のみ読み出し。platform 固有分岐なし
3. 全 `policies.conf.j2` バリアント（sentinels / dynamic / monitors / internal / voq_chassis）で `peer_group` / `PEER_GROUP` キーワードを grep → `BGP_PEER_GROUP_AF` 関連の分岐なし（peer-group 名参照も皆無）
4. `bgp_table_handler_common()` の分岐条件を確認 → `data is None`（DELETE）/ `data あり`（SET）のみ。hardware / platform 条件なし

## 結論

**`BGP_PEER_GROUP_AF` の処理に platform 分岐は存在しない。**

根拠:
- `frrcfgd` は FRR (bgpd) の汎用デーモンであり、ハードウェアアクセラレーション（ASIC）と無関係な純粋なコントロールプレーン処理
- `BGP_PEER_GROUP_AF` → FRR vtysh コマンド変換は全プラットフォーム共通コードパスのみ
- `policies.conf.j2` の voq_chassis / sentinels / monitors / dynamic / internal の各バリアントに peer-group AF の差分テンプレートなし
- DEVICE_METADATA 読み出しは `bgp_asn` / `docker_routing_config_mode` のみ。`platform` / `hwsku` は一切参照されない

## grep 証跡

```
grep -n "platform|hwsku|asic_type|sonic_platform" frrcfgd.py
→ 0 件

grep -n "peer.group|PEER_GROUP" policies.conf.j2 (全バリアント)
→ 0 件
```

## 参照 evidence

- `frrcfgd.py:2162–2170` — DEVICE_METADATA 読み出し（bgp_asn, docker_routing_config_mode のみ）
- `frrcfgd.py:2305` — BGP_PEER_GROUP_AF 購読（条件なし）
- `frrcfgd.py:3918,3930` — bgp_table_handler_common() の分岐（DELETE/SET のみ）
