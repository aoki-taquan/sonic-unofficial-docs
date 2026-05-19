# STP — Phase F: 副次 DB 書込・システム副作用

## 調査対象ソース

- `sonic-net/sonic-swss` — `cfgmgr/stpmgr.cpp` (1493 行)
- `sonic-net/sonic-swss` — `orchagent/stporch.cpp`
- `sonic-net/sonic-swss` — `cfgmgr/stpmgrd.cpp`

## 調査サマリ

STP CONFIG_DB テーブル (`STP|GLOBAL`, `STP_VLAN`, `STP_PORT`, `STP_VLAN_PORT`, `STP_MST`, `STP_MST_INST`, `STP_MST_PORT`) への書き込みは、**DB への副次書き込みではなく Unix ドメインソケット IPC と kernel の ebtables** を主な副作用経路として使用する。

## 副作用 1: `stpd` への IPC メッセージ (`stpmgr.cpp`)

`StpMgr` は CONFIG_DB 変更を検知すると、`sendMsgStpd()` 経由で `stpd` プロセスに Unix ドメインソケット (`/var/run/stpipc.sock`) 宛て `STP_IPC_MSG` を送信する。

| CONFIG_DB テーブル | ハンドラ | 送信メッセージ型 | コード参照 |
|---|---|---|---|
| `STP\|GLOBAL` (SET) | `processGlobalStp()` | `STP_BRIDGE_CONFIG` | `stpmgr.cpp:171` |
| `STP\|GLOBAL` (SET, MST モード) | `processMstGlobal()` | `STP_MST_GLOBAL_CONFIG` | `stpmgr.cpp:402` |
| `STP_VLAN` (SET) | `processStpVlan()` | `STP_VLAN_CONFIG` | `stpmgr.cpp:332` |
| `STP_VLAN_PORT` (SET) | `processStpVlanPort()` | `STP_VLAN_PORT_CONFIG` | `stpmgr.cpp:441` |
| `STP_PORT` (SET) | `processStpPort()` | `STP_PORT_CONFIG` | `stpmgr.cpp:624` |
| VLAN メンバー追加（STATE_DB 経由） | `processVlanMem()` | `STP_VLAN_MEM_CONFIG` | `stpmgr.cpp:753` |
| `STP_MST_INST` (SET) | `processMstInst()` | `STP_MST_INST_CONFIG` | `stpmgr.cpp:1108` |
| `STP_MST_PORT` (SET) | `processMstInstPort()` | `STP_MST_INST_PORT_CONFIG` | `stpmgr.cpp:1152` |

これらは SAI や ASIC_DB への直接書き込みではなく、`stpd` デーモンへの通知。`stpd` が BPDU 送受信と STP ステートマシンを管理し、port state 変更結果を APP_DB (`APP_STP_PORT_STATE_TABLE` 等) に書き戻す。

## 副作用 2: `ebtables` ルールの追加・削除 (`stpmgr.cpp`)

PVST (`mode=pvst`) の有効・無効切替時に `stpmgr` が `ebtables` をシステムコールで直接操作する。

| CONFIG_DB 変化 | 副作用 | コード参照 |
|---|---|---|
| `STP\|GLOBAL.mode = "pvst"` が設定される | `ebtables -A FORWARD -d 01:00:0c:cc:cc:cd -j DROP` を実行 | `stpmgr.cpp:113-117` |
| `STP\|GLOBAL` の DELETE または STP 無効化 | `ebtables -D FORWARD -d 01:00:0c:cc:cc:cd -j DROP` を実行 (PVST 起動時は DEL も実行) | `stpmgr.cpp:47, 157-167` |

この `01:00:0c:cc:cc:cd` は Cisco PVST+ BPDU のマルチキャスト MAC アドレス。カーネルの ebtables ブリッジングレイヤーでドロップすることで、PVST+ BPDU がサードパーティスイッチにリークしないようにする。CONFIG_DB への書き込みとは独立したカーネル状態変更であり、DB を介さない。

## 副作用 3: STATE_DB `STP_TABLE|GLOBAL` への `max_stp_inst` 書込 (`stporch.cpp`)

`StpOrch` は初期化時に SAI から `sai_switch_attr_max_stp_instance` を取得し、`STATE_STP_TABLE` (`"STP_TABLE"`) の `"GLOBAL"` キーに `max_stp_inst` フィールドを書き込む。

```
STATE_DB: STP_TABLE|GLOBAL.max_stp_inst = <SAI 取得値>
```

- 書込タイミング: orchagent 起動時 (`StpOrch::init()` 完了後)
- 読み手: `stpmgr.cpp:1391` — `m_stateStpTable.get("GLOBAL", ...)` で `max_stp_inst` を取得し PVST インスタンス数上限として使用
- SAI 取得失敗時は `255` (デフォルト) を STATE_DB に書く

**CONFIG_DB の STP 設定変更による再書込みはなし**。この値は orchagent 起動時の 1 回のみ。

## CONFIG_DB / APP_DB への直接書込みなし

`stpmgr.cpp` は CONFIG_DB への書き込みを行わない (`setEntry` / `del` 呼び出しゼロ件)。APP_DB へも `APP_PORT_TABLE` の読み取り (`isPortInitDone()`) のみで書き込みはなし。

STP の CONFIG_DB 変化が間接的に引き起こす APP_DB への書き込み（port state 変更等）はすべて `stpd` → `StpOrch` 経路を介し、`StpOrch` が `sai_stp_api` / `sai_vlan_api` を呼び出す形をとる。

## スキャン証跡

- `stpmgr.cpp` 1493 行をキーワード検索 (`setEntry`, `.set(`, `->set(`, `hset`, `APP_DB`, `APPL_DB`, `STATE_DB`, `ProducerState`) → DB 書き込み: ゼロ件
- `stporch.cpp` の `m_stpTable->set("GLOBAL", ...)` (L612) を確認: STATE_STP_TABLE へ `max_stp_inst` を 1 回書込
- `stpmgrd.cpp` で `app_db` / `state_db` のコネクション作成を確認。`stpd_fd` を `socket(AF_UNIX)` で生成し `sendMsgStpd()` 経由で IPC
- `ebtables` 呼び出し: `stpmgr.cpp:47, 113, 161` — PVST モード変更時のみ
