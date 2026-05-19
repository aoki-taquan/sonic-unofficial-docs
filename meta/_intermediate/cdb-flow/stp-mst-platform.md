# STP_MST_INST / STP_MST_PORT — Phase H プラットフォーム差調査

## 結論

`stpmgrd` は SAI / ASIC SDK を一切経由しない純粋なソフトウェア STP デーモン。ASIC ベンダー固有の処理はなく、プラットフォーム差は主に以下の 2 点に集約される:
1. **`max_stp_instances`** — ASIC 能力に依存する最大 MST インスタンス数 (STATE_DB から取得)
2. **multi-asic / VoQ chassis 非対応** — `stpmgrd` はシングル namespace 専用。マルチ ASIC・VoQ シャーシ構成では stpmgrd が管理する MST 設定は host CONFIG_DB の単一スコープに限られる

## 根拠

### 1. max_stp_instances — ASIC 能力依存

`stpmgrd.cpp:77-78` は起動時に `getStpMaxInstances()` を呼んで stpd へ `STP_INIT_READY` メッセージを送信する:

```cpp
msg.max_stp_instances = stpmgr.getStpMaxInstances();
stpmgr.sendMsgStpd(STP_INIT_READY, sizeof(msg), (void *)&msg);
```

`getStpMaxInstances()` (`stpmgr.cpp:1381-1413`) は `STATE_STP_TABLE|GLOBAL.max_stp_inst` を最大 60 秒間ポーリングする。この値は ASIC・プラットフォームドライバが書き込むため、ハードウェア能力に依存する:

- Broadcom プラットフォーム: 実測で最大 64 インスタンスが一般的
- VS (virtual switch): STATE_STP_TABLE が書かれない場合が多く、フォールバック値 255 が使われる
- フォールバック: STATE_STP_TABLE 未書込またはタイムアウトの場合 `STP_DEFAULT_MAX_INSTANCES = 255`

`IS_INST_ID_AVAILABLE()` マクロ (`stpmgr.h:47`) がインスタンス新規作成の際に `max_stp_instances` 上限チェックを行う。MST インスタンス ID 0–62 の範囲は CLI でバリデーション済みだが、stpd 側での受入れは `max_stp_instances` に依存する。

### 2. multi-asic / VoQ chassis 非対応

`stpmgrd.cpp:35-37` は `DBConnector` を `DEFAULT_UNIXSOCKET` (host namespace) で生成するのみ:

```cpp
DBConnector conf_db(CONFIG_DB, DBConnector::DEFAULT_UNIXSOCKET, 0);
DBConnector app_db(APPL_DB, DBConnector::DEFAULT_UNIXSOCKET, 0);
DBConnector state_db(STATE_DB, DBConnector::DEFAULT_UNIXSOCKET, 0);
```

- `is_multi_npu()` / `gMySwitchType` / `isChassisDbInUse()` の参照なし
- CHASSIS_APP_DB / namespace 指定なし
- VOQ シャーシの line card 上で `stpmgrd` が動作する場合、そのカードのホスト CONFIG_DB のみを処理し、他カードとの MST 状態同期機構は存在しない

### 3. PortInitDone 依存 (APPL_DB APP_PORT_TABLE)

`stpmgrd.cpp:72` の `stpmgr.isPortInitDone(&app_db)` が APPL_DB `APP_PORT_TABLE|PortInitDone` を無限ループで待機する。PortsOrch がポートの SAI OID 取得完了を宣言するまで stpmgrd は実質的に処理を開始しない。プラットフォームによってポート初期化所要時間は異なるが、stpmgrd 自体の動作に差分はない（待機するだけ）。

### 4. warm-reboot サポート（宣言のみ）

`stpmgrd.cpp:39-40`:
```cpp
WarmStart::initialize("stpmgrd", "stpd");
WarmStart::checkWarmStart("stpmgrd", "stpd");
```

WarmStart を初期化・チェックしているが、stpmgr.cpp 内では `WarmStart::setWarmStartState()` による状態遷移や warm-reboot 固有のリストア処理は実装されていない。warm-reboot 後は全 CONFIG_DB エントリが再処理されてフラグ (`stpGlobalTask` 等) が再初期化される通常起動と同等の動作をする。FlexCounterOrch の 60 秒遅延のような特別なブロック機構は stpmgrd には存在しない。

### 5. STP_MST_PORT のポートタイプ差 (Ethernet vs PortChannel)

`stpmgr.cpp:1160` のガード条件と `isLagStateOk()` / `isLagEmpty()` の判定は PortChannel に固有:

| ポートタイプ | STP_MST_PORT SET 処理 |
|---|---|
| Ethernet | `isLagEmpty()` が false を返すため通常処理 |
| PortChannel | `isLagStateOk()` が true になるまで保留 (`stpmgr.cpp:791`) |

PortChannel の ready 状態は `STATE_LAG_TABLE` の存在で判断する。ASIC によって LAG 初期化タイミングが異なるが、stpmgrd の動作ロジック自体は同一（待機するだけ）。

## まとめ

stpmgrd は SAI 非依存・ASIC SDK 非依存のソフトウェア STP 実装。プラットフォーム差として意味があるのは `max_stp_instances` の上限値（STATE_DB 経由でプラットフォームドライバが設定）のみ。multi-asic / VoQ chassis 構成では stpmgrd がホスト単体スコープで動作するため、分散シャーシ全体での MST 制御は行わない。
