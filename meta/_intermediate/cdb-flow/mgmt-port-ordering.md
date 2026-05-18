# MGMT_PORT テーブル — 書込み順依存調査メモ (Phase B)

調査日: 2026-05-18
調査対象:
- `sonic-buildimage/files/image_config/monit/mgmt_oper_status.py`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py`
- `sonic-buildimage/files/image_config/config-setup/config-setup.conf`
- `sonic-swss/cfgmgr/portmgrd.cpp`

---

## 1. Consumer と処理経路

`MGMT_PORT` の Consumer は orchagent / portmgrd ではなく、以下の 2 つに限られる。

| Consumer | 処理内容 | 証跡 |
|---------|---------|------|
| `mgmt_oper_status.py` (monit スクリプト) | CONFIG_DB `MGMT_PORT|*` を列挙 → STATE_DB `MGMT_PORT_TABLE|*` へフィールドを同期。`/sys/class/net/<port>/operstate` を読み oper_status も更新 | `mgmt_oper_status.py:16-51` |
| `lldpd.conf.j2` | `alias` フィールドを参照し LLDP portidsubtype を設定 | `dockers/docker-lldp/lldpd.conf.j2:17-18` |

`portmgrd.cpp:28` が購読するのは `CFG_PORT_TABLE_NAME`（= `"PORT"` データポート）のみ。`MGMT_PORT` は orchagent / SAI に到達しない。

---

## 2. 他テーブル先行必須

### MGMT_PORT → STATE_DB MGMT_PORT_TABLE

`mgmt_oper_status.py` は CONFIG_DB に MGMT_PORT エントリが存在することを前提に動作する。エントリが存在しない場合は `syslog LOG_DEBUG` を出力してスクリプトを終了する（`mgmt_oper_status.py:17-19`）。

この場合、STATE_DB `MGMT_PORT_TABLE` は更新されない（STATE_DB への書き込みが発生しない）。

### MGMT_PORT とその他 mgmt テーブルの同期書き込み

minigraph.py は `parse_device_desc_xml()` / `parse_xml()` で MGMT_PORT, MGMT_INTERFACE, MGMT_VRF_CONFIG を**同一関数内で**`results` 辞書に格納する。CONFIG_DB への書き込みは一括で実行されるため、実運用上 3 テーブルの書き込みはほぼ同時に行われる。

```python
# minigraph.py:2281-2308
results['MGMT_PORT'] = {}
results['MGMT_INTERFACE'] = {}
# ... (各エントリの populate)
results['MGMT_VRF_CONFIG'] = mvrf
```

### config-setup による保持

`config-setup.conf:4` の `KEEP_BASIC_TABLES` リストに `MGMT_PORT` が含まれており、factory reset 時も MGMT_PORT・MGMT_INTERFACE・MGMT_VRF_CONFIG の 3 テーブルがまとめて保持される。

---

## 3. 書込み順依存一覧

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | CONFIG_DB 利用可能 → MGMT_PORT 書込み | 強制先行 | minigraph / 手動投入は CONFIG_DB 起動後のみ実行される |
| 2 | MGMT_PORT エントリ存在 → STATE_DB MGMT_PORT_TABLE 更新 | **強制先行** | MGMT_PORT が存在しない場合 mgmt_oper_status.py は STATE_DB を更新せず終了 |
| 3 | MGMT_PORT と MGMT_INTERFACE の同時書込み | minigraph 内で同期（実質アトミック） | REST/gNMI は MGMT_PORT を書込まないため、非 minigraph 経路では別々に書き込まれる可能性あり |
| 4 | orchagent / SAI 依存 | **なし** | MGMT_PORT は SAI 経由なし。portmgrd は MGMT_PORT を購読しない |

---

## 4. まとめ

- MGMT_PORT に対する orchagent・SAI 経路は存在しない。完全にカーネル側処理（monit / lldpd）。
- 唯一の注意点は「MGMT_PORT エントリが CONFIG_DB に存在しないと STATE_DB MGMT_PORT_TABLE が更新されない」という点。
- minigraph 経由では MGMT_PORT と MGMT_INTERFACE が同時に書かれるため実質的な順序問題は発生しない。REST/gNMI での個別書込みには注意が必要。
