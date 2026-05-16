# BGP_PEER_RANGE — Phase H: プラットフォーム差分調査メモ

調査日: 2026-05-16  
調査対象:
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/dynamic/policies.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/dynamic/instance.conf.j2`

---

## 結論: switch_type / sub_role 分岐は存在しない

`BGP_PEER_RANGE` の処理経路（`BGPPeerMgrBase` / dynamic テンプレート群）には
`switch_type`、`sub_role`、`DEVICE_METADATA.localhost.type` を**条件分岐として使用する箇所は存在しない**。

---

## 根拠詳細

### managers_bgp.py における `localhost/type` の扱い

```python
# managers_bgp.py:120
("CONFIG_DB", swsscommon.CFG_DEVICE_METADATA_TABLE_NAME, "localhost/type"),
```

`localhost/type` は deps リストに**依存キーとして登録**されているが、
`managers_bgp.py` 内のいかなる分岐条件・テンプレート変数としても参照されていない。
これは swsscommon の deps ガード機構が「そのキーが DB に存在するまで handler をブロック」する
ために使うものであり、値による動作切り替えではない。

grep 検索:
- `switch_type` → ヒットなし
- `sub_role` → ヒットなし
- `"type"` (引用符付き参照) → ヒットなし（`peer_type` 変数のみ、これは内部 enum）
- `localhost\["type"\]` 形式 → ヒットなし

### dynamic/policies.conf.j2 の内容

```
route-map FROM_BGP_SPEAKER permit 10
route-map TO_BGP_SPEAKER deny 1
```

条件分岐なし。全プラットフォームで同一内容。

### dynamic/instance.conf.j2 の条件分岐

```jinja2
{% if bgp_session['peer_asn'] is defined %}
  neighbor {{ bgp_session['name'] }} remote-as {{ bgp_session['peer_asn'] }}
{% else %}
  neighbor {{ bgp_session['name'] }} remote-as {{ constants.deployment_id_asn_map[...deployment_id] }}
{% endif %}

{% if bgp_session['src_address'] is defined %}
  neighbor {{ bgp_session['name'] }} update-source {{ bgp_session['src_address'] | ip }}
{% else %}
  neighbor {{ bgp_session['name'] }} update-source {{ get_ipv4_loopback_address(... "Loopback1") | ip }}
{% endif %}
```

これらは CONFIG_DB フィールドの有無による分岐であり、プラットフォーム種別（switch_type / sub_role）
による分岐ではない。すべてのプラットフォームで同一ロジック。

---

## プラットフォーム非依存の根拠まとめ

| 検索対象 | 結果 |
|---------|------|
| `switch_type` in managers_bgp.py | ヒットなし |
| `sub_role` in managers_bgp.py | ヒットなし |
| `localhost/type` の分岐利用 | deps 登録のみ、分岐なし |
| dynamic/policies.conf.j2 の分岐 | なし |
| dynamic/instance.conf.j2 の platform 分岐 | なし |

`BGP_PEER_RANGE` は peer_type="dynamic" の固定ロール。
FRR 経路（bgpcfgd + dynamic テンプレート）は switch_type / sub_role に依存せず、
全 SONiC プラットフォームで同一動作をする。
