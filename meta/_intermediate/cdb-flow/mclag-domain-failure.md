# mclag-domain — Phase D 失敗挙動 中間調査

対象: `docs/reference/config-db/mclag-domain.md` (MCLAG_DOMAIN / MCLAG_INTERFACE テーブル群)

ソース ref:
- sonic-swss `orchagent/mlagorch.cpp` @ HEAD (sonic-swss master)

## スキャン方法

```bash
grep -n -E 'SWSS_LOG_ERROR|SWSS_LOG_WARN|return|throw|invalid|fail|peer_ip|PORTCHANNEL|bridge_port|SAI' \
  .cache/sonic-sources/sonic-swss/orchagent/mlagorch.cpp
```

全行確認: `mlagorch.cpp` L1-250 をスキャン。

## 失敗パス一覧

### 1. 不正テーブル名 → SWSS_LOG_ERROR + 処理なし

- 箇所: `mlagorch.cpp:62-65` (`doTask()`)
- トリガー: `table_name` が `CFG_MCLAG_TABLE_NAME` でも `CFG_MCLAG_INTF_TABLE_NAME` でもない
- 動作: `SWSS_LOG_ERROR("MLAG receives invalid table %s", table_name.c_str())` + erase なし
- 結果: 当該エントリは処理されずキューに残る
- retry: Consumer がエントリを保持し続ける（次の doTask() 呼び出しで再試行されるが table_name は変わらないため永続エラー）

### 2. peer_link フィールドが空 → エントリを erase してスキップ

- 箇所: `mlagorch.cpp:91-99` (`doMlagDomainTask()`)
- トリガー: SET_COMMAND 時に `peer_link` フィールドが存在しないまたは空文字列
- 動作: `it = consumer.m_toSync.erase(it)` でエントリをドロップ。ログなし
- 結果: `addIslInterface()` は呼ばれず、ISL 登録が行われない。**サイレント失敗**
- retry: なし（erase で消費される）

### 3. addIslInterface() が false を返す → retry

- 箇所: `mlagorch.cpp:93-96` (`doMlagDomainTask()`)
- トリガー: `addIslInterface(peer_link)` が false を返した場合
- 動作: `it++` で次のイテレーションへ（erase しない = キューに残す）
- 結果: 次の doTask() 呼び出しで再試行
- 注: 現在の実装 (`mlagorch.cpp:156-172`) では `addIslInterface()` は常に `true` を返すため、このパスは実質的に到達不可能

### 4. MLAG インターフェースの重複 ADD → SWSS_LOG_ERROR + 強行挿入はスキップ

- 箇所: `mlagorch.cpp:198-201` (`addMlagInterface()`)
- トリガー: `m_mlagIntfs` に既に存在する `if_name` を再度 SET
- 動作: `SWSS_LOG_ERROR("MLAG adds duplicate MLAG interface %s", if_name.c_str())`。notify は呼ばれない
- 結果: ログのみ。重複エントリは無視され、既存の登録は保持される
- retry: なし（`addMlagInterface()` は true を返し、erase される）

### 5. 未知の MLAG インターフェースの DEL → SWSS_LOG_ERROR + スキップ

- 箇所: `mlagorch.cpp:220-223` (`delMlagInterface()`)
- トリガー: `m_mlagIntfs` に存在しない `if_name` を DEL
- 動作: `SWSS_LOG_ERROR("MLAG deletes unknown MLAG interface %s", if_name.c_str())`。notify は呼ばれない
- 結果: ログのみ。erase も observer 通知も行われない
- retry: なし（`delMlagInterface()` は true を返し、erase される）

### 6. 不明な op_type → SWSS_LOG_ERROR + erase

- 箇所: `mlagorch.cpp:108-112` (`doMlagDomainTask()`), `mlagorch.cpp:149-152` (`doMlagInterfaceTask()`)
- トリガー: SET でも DEL でもない操作コマンド
- 動作: `SWSS_LOG_ERROR("MLAG receives unknown operation type %s", op.c_str())` + `it = consumer.m_toSync.erase(it)`
- 結果: エントリを消費してドロップ。処理は継続
- retry: なし

### 7. peer_ip バリデーションなし（mlagorch.cpp レベル）

- 箇所: `mlagorch.cpp` 全体
- `MlagOrch` は `peer_ip` フィールドを **直接参照しない**。`peer_link` のみを抽出して `addIslInterface()` を呼ぶ
- `peer_ip` のバリデーションは YANG (`sonic-mclag.yang` `inet:ipv4-address` 型) のみ
- 不正 peer_ip は YANG バリデーション段階（`sonic-yang-mgmt` / `config mclag` CLI）で拒否される
- orchagent (`mlagorch.cpp`) レベルには到達しない

### 8. PORTCHANNEL 未解決（peer_link が存在しない Port の場合）

- 箇所: `mlagorch.cpp:156-172` (`addIslInterface()`)
- `addIslInterface()` は Port オブジェクトを解決しない（`gPortsOrch->getPort()` を呼ばない）
- `m_isl_name` に文字列を記録し、`SUBJECT_TYPE_MLAG_ISL_CHANGE` を notify するだけ
- つまり **orchagent 側では PORTCHANNEL の存在チェックは行わない**
- PORTCHANNEL が未設定の場合でも `addIslInterface()` は成功し、downstream observer (SAI bridge_port 操作等) がエラーを検知する
- SAI bridge_port 失敗は下流 observer 依存（本ファイル範囲外）

### 9. SAI bridge_port 失敗

- `MlagOrch` 自体は SAI を直接呼ばない（SAI API コールなし）
- `addIslInterface()` / `delIslInterface()` は `notify(SUBJECT_TYPE_MLAG_ISL_CHANGE, ...)` で observer を呼ぶ
- SAI bridge_port 操作は下流の observer（例: `BridgePortsOrch` 等）が担当
- `mlagorch.cpp` 内に SAI 失敗パスは存在しない

## STATE_DB / ERROR_TABLE への記録

`MlagOrch` は STATE_DB や ERROR_TABLE への書き込みを行わない。失敗は syslog (`SWSS_LOG_ERROR`) のみ。

```bash
docker exec swss grep -i "MLAG" /var/log/syslog
```

## 確認コマンド

```bash
# MlagOrch エラーログ確認
docker exec swss cat /var/log/swss/orchagent.log | grep -i "MLAG"
# MCLAG インターフェース一覧
sonic-db-cli CONFIG_DB keys 'MCLAG_INTERFACE|*'
# peer_link 設定確認
sonic-db-cli CONFIG_DB hgetall 'MCLAG_DOMAIN|1'
```
