# PREFIX_LIST — Phase H: プラットフォーム差異

> 調査日: 2026-05-16  
> ソース: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_prefix_list.py`

## 1. FRR バージョン差

`managers_prefix_list.py` および bgpcfgd コード全体に FRR バージョン条件分岐は存在しない。`ip prefix-list` / `ipv6 prefix-list` コマンド構文は FRR 7.x 以降で安定しており、SONiC が対象とする FRR バージョン範囲 (7.5+) 内で差異はない。テンプレート (`bgpd/radian/add_radian.conf.j2`、`bgpd/suppress_prefix/add_suppress_prefix.conf.j2`) もバージョン分岐なし。

**結論**: FRR バージョン差による挙動差異なし。

## 2. IPv4 / IPv6 差

`get_ip_type()` (L138-143) が `netaddr.IPNetwork.version` を判定し、`data["ipv"]` に `"ip"` または `"ipv6"` をセットする。その後 `generate_prefix_list_config()` でテンプレートと prefix list 名が分岐する。

| 条件 | FRR コマンド種別 | デフォルト prefix list 名 (SUPPRESS_PREFIX) | テンプレート |
|---|---|---|---|
| IPv4 (`prefix.version == 4`) | `ip prefix-list` | `SUPPRESS_IPV4_PREFIX` | `add_suppress_prefix.conf.j2` |
| IPv6 (`prefix.version == 6`) | `ipv6 prefix-list` | `SUPPRESS_IPV6_PREFIX` | `add_suppress_prefix.conf.j2` |

ANCHOR_PREFIX の場合: prefix list 名は IPv4/IPv6 とも `ANCHOR_CONTRIBUTING_ROUTES` (固定)。ただし FRR コマンド種別は同様に `ip` / `ipv6` で分岐する。

constants にて `bgp.prefix_list.<type>.ipv4_name` / `ipv6_name` を定義すれば、デフォルト名をプラットフォーム（デプロイ）ごとに上書き可能。この上書きは IPv4/IPv6 で独立して設定できる。

**コード証跡** (`managers_prefix_list.py:89-91`):
```python
pl_overrides = self.constants.get("bgp", {}).get("prefix_list", {}).get(prefix_type, {})
name_key = "ipv4_name" if data["ipv"] == "ip" else "ipv6_name"
data["prefix_list_name"] = pl_overrides.get(name_key, type_cfg["prefix_list_name"](data["ipv"]))
```

## 3. デバイスタイプ (DEVICE_METADATA.type) 差

`ANCHOR_PREFIX` は SpineRouter/UpstreamLC および UpperSpineRouter 専用。その他デバイス (ToRRouter、LeafRouter 等) では `log_warn` してスキップされる。`SUPPRESS_PREFIX` は全デバイスで有効 (`allowed_devices: None`)。

| prefix_type | 対応デバイス | 非対応デバイスの挙動 |
|---|---|---|
| `ANCHOR_PREFIX` | SpineRouter/UpstreamLC、UpperSpineRouter | `log_warn` + スキップ (FRR 設定生成なし) |
| `SUPPRESS_PREFIX` | 全デバイス | 制限なし |

この差異は ASIC/NIC の種類ではなく SONiC の論理ロール（デバイスタイプ）に基づく。ベンダー固有の分岐はない。

## 4. 非対応プラットフォーム / スコープ外

- **ASIC ベンダー差 (Broadcom / Mellanox / Cisco 等)**: コード上の条件分岐なし。PREFIX_LIST はコントロールプレーン (FRR bgpd) のみで処理され SAI を経由しないため、ASIC 依存性ゼロ
- **arm / aarch64 / x86 アーキテクチャ差**: 条件分岐なし
- **SmartSwitch / DPU**: 専用ロジックなし。DEVICE_METADATA.type が SpineRouter 等でなければ ANCHOR_PREFIX がスキップされるのみ
- **ベンダー固有**: スコープ外 (コミュニティ版 master のみ対象)

## 引用

- `src/sonic-bgpcfgd/bgpcfgd/managers_prefix_list.py:6-26,49-99,138-143`
- `src/sonic-bgpcfgd/tests/test_prefix_list.py`
