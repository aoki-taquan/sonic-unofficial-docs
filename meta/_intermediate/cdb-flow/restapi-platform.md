# RESTAPI — Platform Phase (Phase H)

## 調査概要

- **対象ファイル**: `sonic-buildimage/dockers/docker-sonic-mgmt-framework/rest-server.sh`, `mgmt_vars.j2`, `supervisord.conf`, `sonic-buildimage/src/sonic-config-engine/minigraph.py:2689-2701`
- **調査日**: 2026-05-19

## 結論: プラットフォーム差なし

RESTAPI テーブルは管理プレーン専用機能であり、SAI を経由しないため ASIC 種別・ベンダー・multi-asic / VOQ chassis 構成による動作差は存在しない。

### 各観点の確認結果

| 観点 | 結果 | 根拠 |
|------|------|------|
| ASIC 種別 (Broadcom / Mellanox / Marvell 等) | 影響なし | `rest-server.sh` は `sonic-cfggen -d -t mgmt_vars.j2` で CONFIG_DB を読み取るのみ。SAI 非経由 |
| multi-asic (`is_multi_npu()`) | 影響なし | `mgmt_vars.j2` に namespace 分岐なし。`rest-server.sh` も `SONIC_ASIC_ID` / `SONIC_ASIC_COUNT` 参照なし |
| VOQ chassis (supervisor + line cards) | 各 host で独立適用 | RESTAPI テーブルは host scope。`mgmt_vars.j2` に chassis 分岐なし |
| ベンダー固有 hook | なし | `docker-sonic-mgmt-framework/` 配下にベンダー条件分岐なし (`grep -r vendor/broadcom/mellanox` が 0 ヒット) |
| minigraph プラットフォーム分岐 | なし | `minigraph.py:2689-2701` で RESTAPI テーブルは無条件に同一値を投入。`platform` / `hwsku` 条件分岐なし |
| テンプレート内プラットフォーム分岐 | なし | `mgmt_vars.j2` (4 行) に条件分岐なし。`rest-server.sh` に `platform` / `asic` / `vendor` 分岐なし |

## 参考: minigraph.py による固定値 (L2689-2701)

```python
results['RESTAPI'] = {
    'config': {
        'client_auth': 'true',
        'allow_insecure': 'false',
        'log_level': 'info'
    },
    'certs': {
        'server_crt': '/etc/sonic/credentials/restapiserver.crt',
        'server_key': '/etc/sonic/credentials/restapiserver.key',
        'ca_crt': '/etc/sonic/credentials/restapica.crt',
        'client_crt_cname': 'client.restapi.sonic'
    }
}
```

全プラットフォーム共通の固定値が投入される。`hwsku` / `platform` の条件分岐なし。
