# DEVICE_NEIGHBOR 処理順序 (Phase B)

ソース:
- `sonic-net/sonic-buildimage` `src/sonic-config-engine/minigraph.py` @ 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
- `sonic-net/sonic-buildimage` `src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` @ (same repo)
- `sonic-net/sonic-utilities` `pfcwd/main.py` / `scripts/ecnconfig`

## DEVICE_NEIGHBOR 書き込み先行要件

DEVICE_NEIGHBOR は minigraph.py (sonic-cfggen) が書き込む。書き込み前提:
1. `port_config.ini` 内に存在するインターフェイス名のみキーとして採用 (minigraph.py:2631-2636)
2. DEVICE_NEIGHBOR_METADATA は DEVICE_NEIGHBOR と同一 `sonic-cfggen -m` 呼び出しで生成される (minigraph.py:2637-2641)

## Consumer ごとの依存順序

### bgpcfgd (BGP セッション確立)

`bgpcfgd/managers_bgp.py:140` で `deps` に `CFG_DEVICE_NEIGHBOR_METADATA_TABLE_NAME` を登録しており、DEVICE_NEIGHBOR_METADATA が揃うまで BGP セッション追加を defer する。DEVICE_NEIGHBOR は直接 subscribe されていないが、`name` フィールドが DEVICE_NEIGHBOR_METADATA のキーと一致する必要がある。順序:

```
1. DEVICE_NEIGHBOR_METADATA (bgpcfgd deps として登録)
2. DEVICE_NEIGHBOR (BGP_NEIGHBOR 設定で name を参照)
```

### pfcwd (start_default)

`pfcwd/main.py:413` で起動時に `DEVICE_NEIGHBOR.keys()` を外部ポート一覧として一括読み取る。PORT テーブルとの明示的な順序制約はなく、`pfcwd start_default` 実行時点で DEVICE_NEIGHBOR に期待するポートが存在していれば足りる。

### ecnconfig

`scripts/ecnconfig:282-287` で `DEVICE_NEIGHBOR` テーブルのキー一覧をポートとして取得。テーブルが空の場合は `Exception("No active ports detected")` を送出するため、**DEVICE_NEIGHBOR が空でない状態で `ecnconfig` を実行する必要がある**。

### lldpmgrd (dead consumer)

lldpmgrd は DEVICE_NEIGHBOR を subscribe しない（TODO コメントのみ, lldpmgrd:12-14）。DEVICE_METADATA と MGMT_INTERFACE のみを subscribe するため、DEVICE_NEIGHBOR の書き込みタイミングは lldpmgrd の動作に影響しない。

## warm-reboot 挙動

DEVICE_NEIGHBOR は static topology 情報であり、warm-reboot 時は `config reload` または `sonic-cfggen` 再実行での全件上書きが前提。Consumer (pfcwd, ecnconfig) は再起動時に再度 `get_table` で全件読み取るため、warm-reboot 時の incremental 適用は考慮されていない。
