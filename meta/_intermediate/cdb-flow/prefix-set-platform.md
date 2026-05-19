# PREFIX_SET — Phase H プラットフォーム差 中間ファイル

生成日: 2026-05-19

## 調査対象

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/templates/bgpd/bgpd.conf.db.pref_list.j2`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-device_metadata.yang`

## 調査結果

### ASIC / SAI 経由なし

PREFIX_SET は FRR (`bgpd` / `zebra`) 制御プレーン上の prefix-list で SAI 非経由。
`orchagent` / `syncd` は一切関与しない。
Broadcom / Mellanox / Marvell / Innovium / VPP 等の ASIC 種別による分岐は存在しない。

### frrcfgd プロセス起動条件 (DEVICE_METADATA gate)

`DEVICE_METADATA|localhost|frr_mgmt_framework_config = true` が設定されていない環境では
sonic-frr-mgmt-framework パッケージ自体が有効化されず、frrcfgd が起動しない。
この場合 PREFIX_SET テーブルを購読するプロセスが存在せず、CONFIG_DB への書き込みは FRR に反映されない。

根拠: `sonic-device_metadata.yang:132-138`

```
leaf frr_mgmt_framework_config {
    type boolean;
    description "FRR configurations are handled by sonic-frr-mgmt-framework module when set to true,
        otherwise, sonic-bgpcfgd handles the FRR configurations based on the predefined templates.";
    default "false";
}
```

### アドレスファミリ別の適用デーモン (AF-based branching)

PREFIX テーブルのエントリ処理では、`PREFIX_SET.mode` に基づく AF で適用先 FRR デーモンが変わる。
これはプラットフォーム差ではなく AF の論理分岐だが、インフラとして記録する。

| AF | daemons 引数 | vtysh コマンド |
|----|------------|---------------|
| `IPv4` (AF_INET) | `None` (テーブルのデフォルト: bgpd+zebra+ospfd+pimd) | `ip prefix-list ...` |
| `IPv6` (AF_INET6) | `['bgpd', 'zebra']` | `ipv6 prefix-list ...` |

根拠: `frrcfgd.py:2931-2936`

```python
af = self.prefix_set_list[pfx_set_name].af
if af == socket.AF_INET:
    daemons = None  # use table default: ['zebra', 'bgpd', 'ospfd', 'pimd']
else:
    daemons = ['bgpd', 'zebra']
```

### multi-asic / VOQ / chassis-packet

frrcfgd は namespace 内で per-asic 起動される。PREFIX_SET / PREFIX ハンドラ
(`frrcfgd.py:2894-2995`) に `namespace` / `asic` / `switch_type` / `sub_role` / `chassis` 分岐なし。
全 namespace で同一ロジック。

### Jinja2 テンプレート (bgpd.conf.db.pref_list.j2)

起動時の初期 FRR 設定生成テンプレートにも platform / asic / switch_type 条件分岐なし。
`PREFIX_SET.mode` (`IPv4` / `IPv6`) のみを使用してコマンド種別を決定する。

## 結論

プラットフォーム固有の差異なし。唯一の運用上の注意点は
`DEVICE_METADATA|localhost|frr_mgmt_framework_config = true` が未設定の場合に
frrcfgd が非起動となり PREFIX_SET が FRR に反映されない点。
