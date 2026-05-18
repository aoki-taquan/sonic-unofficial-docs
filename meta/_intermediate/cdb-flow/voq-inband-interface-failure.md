# VOQ_INBAND_INTERFACE — Phase D 失敗挙動調査ノート

調査日: 2026-05-18
調査対象:
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`
- `sonic-swss/orchagent/portsorch.cpp`

## 概要

`VOQ_INBAND_INTERFACE` の処理は以下の 2 経路に分かれる:

1. **単一キー SET** (`|<name>`): `intfmgr.cpp:1195-1204` で `doIntfGeneralTask()` をバイパスし APP_DB へ直接 relay。
2. **2-key SET** (`|<name>|<ip-prefix>`): 通常の `doIntfAddrTask()` パス。

## 失敗ポイント

### intfmgr.cpp 側

**単一キー SET** は `m_appIntfTableProducer.set()` + `m_stateIntfTable.hset()` を呼んで即 erase する。
この経路では **失敗分岐がない**（エラーチェックなし）。
- APP_DB へのメッセージ送信は Redis write であり、通常失敗しない。
- STATE_DB への `vrf=""` 書き込みも同様。

**2-key SET** (`doIntfAddrTask`):
- `isIntfStateOk(alias)` が false → `return false` → `it++` (retry 待ち)
- `isIntfCreated(alias)` が false → `return false` → `it++` (retry 待ち)
- 単一キー SET が先行して STATE_DB に `vrf=""` を書くまで `isIntfCreated()` は false

### portsorch.cpp 側 (orchagent 内)

`setVoqInbandIntf()` (`portsorch.cpp:11110-11134`):
- `getPort(alias, port)` が false (ポートが orchagent 内部マップ未登録) → `SWSS_LOG_ERROR` + `return false`
  → `intfsorch.cpp:897-900` で `it++; continue;` → APPL_DB エントリが retry キューに残存
- `type == "port"` かつ `port.m_hif_id == 0` (host interface 未作成) → `SWSS_LOG_ERROR` + `return false`
  → 同様に retry キュー滞留
- 同名で既登録の場合は NOTICE ログのみで `return true` (idempotent)

### intfsorch.cpp 側

`doTask()` (`intfsorch.cpp:897-901`):
```cpp
if(!gPortsOrch->setVoqInbandIntf(alias, inband_type))
{
    it++;
    continue;
}
```
`setVoqInbandIntf()` が false を返すと `m_toSync` に残留し次回ループで再試行。
外部に STATE_DB/APPL_DB の変化なし（silent retry）。

## retry の解消条件

| 失敗ケース | 解消トリガー |
|-----------|------------|
| `getPort()` false (ポート未登録) | `portsyncd` が `PORT_TABLE` を APPL_DB に書き → `portsorch` がポートを登録した時点 |
| `m_hif_id == 0` (host IF 未作成) | `portsorch` が host interface (`sai_create_hostif`) を完了した時点 |
| 2-key の `isIntfCreated()` false | 単一キー SET が先行して `STATE_INTF_TABLE` に `vrf=""` を書いた時点 |

## STATE_DB / エラーログ

- `portsorch.cpp:11121`: `SWSS_LOG_ERROR("Port/Vlan configured for inband intf %s is not ready!", alias.c_str())`
- `portsorch.cpp:11129`: `SWSS_LOG_ERROR("Host interface is not available for port %s", alias.c_str())`
- syslog の swss プロセス: `journalctl -u swss | grep -i "inband"`
- STATE_DB への障害記録はなし（VOQ 系は ACL・QoS と異なり STATE_DB ステータスを書かない）
