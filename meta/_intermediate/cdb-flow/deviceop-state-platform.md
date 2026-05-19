# DEVICE_NEIGHBOR (device op state) — Phase H: プラットフォーム差異

Generated: 2026-05-19
Target doc: docs/reference/config-db/deviceop-state.md

調査済みファイル（`deviceop-state-constants.md` の §2 を参照）:
- `sonic-utilities/scripts/ecnconfig:92-95,264-293`
- `sonic-utilities/pfcwd/main.py:36-42,111-119,405-444`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:100`

---

## 1. ecnconfig — `voq` switch_type 分岐 (`ecnconfig:264-293`)

```python
switch_type = device_info.get_localhost_info('switch_type', self.config_db)
if switch_type == 'voq':
    # QUEUE テーブルからポートを導出 (DEVICE_NEIGHBOR は参照しない)
    q_table = self.config_db.get_table(QUEUE_TABLE_NAME)
    ...
else:
    # 非 voq: DEVICE_NEIGHBOR からポートを取得
    port_table = self.config_db.get_table(DEVICE_NEIGHBOR_TABLE_NAME)
    self.ports_key = list(port_table.keys())
    if len(self.ports_key) == 0:
        raise Exception("No active ports detected in table 'DEVICE_NEIGHBOR'")
```

- `voq` 環境（`DEVICE_METADATA.localhost.switch_type == 'voq'`）では `DEVICE_NEIGHBOR` は一切参照されない
- 非 voq 環境（デフォルト）では `DEVICE_NEIGHBOR` が必須入力。テーブルが空だと Exception で停止
- `voq` 環境では `QUEUE` テーブルのキー集合がポート一覧として使われる

| `switch_type` | ポート決定元 | DEVICE_NEIGHBOR 参照 | 空テーブル時 |
|---------------|------------|---------------------|------------|
| `voq` | `QUEUE` テーブル | なし | 影響なし |
| それ以外（default） | `DEVICE_NEIGHBOR` | あり | Exception で停止 |

## 2. ecnconfig — multi-ASIC バックエンドポート (`ecnconfig:289-293`)

非 voq 環境では取得したポートキーを `int(k[8:])` または `int(k[11:]) + 1024` でソートする。

- 通常ポート `Ethernetxy`: `int(k[8:])` で数値ソート
- バックエンドポート `Ethernet-BPxy` (multi-ASIC 環境のみ): `int(k[11:]) + 1024` で末尾に配置

シングル ASIC 環境では `BP` を含むポート名が存在しないためソート結果に差異は生じない。
multi-ASIC 環境ではバックエンドポートが通常ポートの後ろにまとめて配置される。

## 3. pfcwd — multi-ASIC ネームスペース対応

`PfcwdCmd.start_default` は `@multi_asic_util.run_on_multi_asic` デコレータで修飾されており、
multi-ASIC 環境では各ネームスペース（`asic0` / `asic1` / ...）の `ConfigDBConnector` に対して
独立して実行される。

- 各ネームスペース内の `DEVICE_NEIGHBOR` テーブルを個別に参照する
- ネームスペース間でポートスコープは独立（asic0 の DEVICE_NEIGHBOR が asic1 のスコープに影響しない）
- バックプレーンポート（`get_bp_ports`; `PORT.role == 'Int'` かつ `admin_status == 'up'`）は
  multi-ASIC 環境ではネームスペース内の ASIC 間接続ポートとして存在する
- シングル ASIC 環境では `role == 'Int'` のポートは通常存在しないため `bp_ports = []`

## 4. bgpcfgd — プラットフォーム非依存

`bgpcfgd` は DEVICE_NEIGHBOR_METADATA を参照するが、環境変数 `platform` による分岐は存在しない。
`check_neig_meta` フラグは DEVICE_METADATA の設定値やコード内で制御されるものであり、
プラットフォーム種別とは独立している。

---

## プラットフォーム差異サマリ

| 環境 / プラットフォーム | 差異 |
|------------------------|------|
| `voq` switch_type | `ecnconfig` が `DEVICE_NEIGHBOR` を参照しない（`QUEUE` テーブル使用） |
| multi-ASIC (非 voq) | バックエンドポート `Ethernet-BPxy` がソート末尾に配置される |
| multi-ASIC pfcwd | ネームスペースごとに独立した `DEVICE_NEIGHBOR` スキャン + bp_ports 追加 |
| シングル ASIC | `Ethernet-BPxy` 不存在・`bp_ports = []`。`voq` でなければ DEVICE_NEIGHBOR が必須 |

---

## Evidence

- `sonic-utilities` `pfcwd/main.py:36-42,111-119,405-444`
- `sonic-utilities` `scripts/ecnconfig:92-95,264-293`
- `sonic-buildimage` `src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:100`
