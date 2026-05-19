# MCLAG_INTERFACE — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-19 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/mclag-interface.md` で扱う CONFIG_DB `MCLAG_INTERFACE` テーブルの
変更時に、主購読者 `MlagOrch` (orchagent) および `mclagsyncd` が、主の CONFIG_DB 処理に
**副次して** STATE_DB / COUNTERS_DB / APPL_DB / その他副次 DB へ書き込みを行うかどうか。

## 走査範囲

- `.cache/sonic-sources/sonic-swss/orchagent/mlagorch.cpp` (MlagOrch)
- `.cache/sonic-sources/sonic-swss/mclagsyncd/mclaglink.cpp` (mclagsyncd)
- `.cache/sonic-sources/sonic-swss/mclagsyncd/mclaglink.h`
- `.cache/sonic-sources/sonic-swss-common/common/schema.h` (テーブル名定数)

## 走査コマンドと結果

### 1. MlagOrch 内の副次 DB アクセス

```bash
grep -n -E "state_db|STATE_DB|appl_db|APPL_DB|counters_db|COUNTERS_DB" \
  .cache/sonic-sources/sonic-swss/orchagent/mlagorch.cpp
```

結果: **マッチ 0 件**。`MlagOrch` は CONFIG_DB の `MCLAG_INTERFACE` を購読して
`addMlagInterface()` / `delMlagInterface()` を呼び出すが、これらのメソッドは
`m_mlagIntfs` の内部マップ更新と Observer 通知 (`SUBJECT_TYPE_MLAG_INTF_CHANGE`)
を broadcast するのみ。STATE_DB / APPL_DB / COUNTERS_DB への直接書込は存在しない。

### 2. mclagsyncd 内の STATE_DB 書込

```bash
grep -n -E "p_mclag_local_intf_tbl|p_mclag_remote_intf_tbl" \
  .cache/sonic-sources/sonic-swss/mclagsyncd/mclaglink.cpp
```

検出された STATE_DB 書込 (set / del):

| 行 | 関数 | テーブル | 操作 | キー形式 | 書込フィールド |
|---|---|---|---|---|---|
| L1520 | `setLocalIfPortIsolate()` | `STATE_MCLAG_LOCAL_INTF_TABLE` (`MCLAG_LOCAL_INTF_TABLE`) | `set` | `<if_name>` | `port_isolate_peer_link = true|false` |
| L1533 | `deleteLocalIfPortIsolate()` | `STATE_MCLAG_LOCAL_INTF_TABLE` | `del` | `<if_name>` | — |
| L1584 | `mclagsyncdSetRemoteIfState()` | `STATE_MCLAG_REMOTE_INTF_TABLE` (`MCLAG_REMOTE_INTF_TABLE`) | `set` | `<mlag_id>|<if_name>` | `oper_status = up|down` |
| L1633 | `mclagsyncdDelRemoteIfInfo()` | `STATE_MCLAG_REMOTE_INTF_TABLE` | `del` | `<mlag_id>|<if_name>` | — |

これらは MCLAG_INTERFACE の直接 SET/DEL 後ではなく、ICCP セッション確立後の
iccpd ネゴシエーション完了を受けて mclagsyncd が呼び出す。

### 3. COUNTERS_DB アクセス

```bash
grep -n "p_counters_db" .cache/sonic-sources/sonic-swss/mclagsyncd/mclaglink.cpp
```

検出:
- `mclaglink.cpp:66` `auto hash = p_counters_db->hgetall("COUNTERS_PORT_NAME_MAP");`

`hgetall` は **読取専用**。`COUNTERS_PORT_NAME_MAP` はオブジェクト OID 解決のために
ポート名 → OID マッピングを読み出すのみ。COUNTERS_DB への書込は **0 件**。

### 4. APPL_DB への通知 (FLUSHFDBREQUEST)

```bash
grep -n "FLUSHFDBREQUEST\|flushFdb" \
  .cache/sonic-sources/sonic-swss/mclagsyncd/mclaglink.cpp
```

検出:
- `mclaglink.cpp:423` `swss::NotificationProducer flushFdb(p_appl_db.get(), "FLUSHFDBREQUEST");`
- `mclaglink.cpp:429` `flushFdb.send("ALL", "ALL", values);`

宛先は `p_appl_db` (APPL_DB) の `FLUSHFDBREQUEST` チャネル (NotificationProducer)。
これは ICCP セッション確立直後の FDB フラッシュ要求であり、
MCLAG_INTERFACE SET/DEL への直接応答ではなく、iccpd からの ICCP 状態変化通知に
連動する。

### 5. スキーマ定数の確認

```bash
grep -n "STATE_MCLAG" .cache/sonic-sources/sonic-swss-common/common/schema.h
```

- `schema.h:440` `#define STATE_MCLAG_TABLE_NAME "MCLAG_TABLE"`
- `schema.h:441` `#define STATE_MCLAG_LOCAL_INTF_TABLE_NAME "MCLAG_LOCAL_INTF_TABLE"`
- `schema.h:442` `#define STATE_MCLAG_REMOTE_INTF_TABLE_NAME "MCLAG_REMOTE_INTF_TABLE"`
- `schema.h:443` `#define STATE_MCLAG_REMOTE_FDB_TABLE_NAME "MCLAG_REMOTE_FDB_TABLE"`

## 結論

CONFIG_DB `MCLAG_INTERFACE` の変更に伴う副次 DB 書込は以下の通り:

| 副次 DB | テーブル | 書込有無 | トリガ | 根拠 |
|---|---|---|---|---|
| STATE_DB | `MCLAG_LOCAL_INTF_TABLE` | **あり** | iccpd からポート分離設定受信時 | `mclaglink.cpp:L1520,L1533` |
| STATE_DB | `MCLAG_REMOTE_INTF_TABLE` | **あり** | iccpd からリモートIF oper 状態受信時 | `mclaglink.cpp:L1584,L1633` |
| COUNTERS_DB | — | なし (読取のみ) | `hgetall("COUNTERS_PORT_NAME_MAP")` での OID 解決 | `mclaglink.cpp:L66` |
| APPL_DB | `FLUSHFDBREQUEST` (通知チャネル) | **あり** (通知のみ) | iccpd ICCP セッション確立時に FDB フラッシュ要求 | `mclaglink.cpp:L423,L429` |
| ASIC_DB | — | なし (直接) | `MlagOrch` から SAI 呼出なし。FdbOrch Observer 経由で間接 | `mlagorch.cpp:L193-234` |
| FLEX_COUNTER_DB | — | なし | MCLAG_INTERFACE には FlexCounter 登録なし | — |

**重要**: STATE_DB への書込は MCLAG_INTERFACE SET 直後ではなく、ICCP セッション確立後の
iccpd ネゴシエーション完了を待って行われる。CONFIG_DB 書込直後に STATE_DB を確認しても
空の場合がある（`show mclag interface` で確認可能）。
