# HARDWARE — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-19 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/hardware.md` 配下の CONFIG_DB `HARDWARE|ACCESS_LIST` テーブル変更時に、
購読コンポーネントが APPL_DB / STATE_DB / COUNTERS_DB / その他副次 DB へ何らかの書き込みを行うか。

## 走査範囲

- `.cache/sonic-sources/sonic-swss/orchagent/` 全体 (consumer 探索)
- `.cache/sonic-sources/sonic-swss/cfgmgr/` 全体
- `.cache/sonic-sources/sonic-swss/fpmsyncd/` 全体
- `.cache/sonic-sources/sonic-host-services/` 全体
- `.cache/sonic-sources/sonic-utilities/` 全体
- `.cache/sonic-sources/sonic-gnmi/` 本番コード (testdata 除外)
- `.cache/sonic-sources/sonic-mgmt-common/` 本番コード (test 除外)

## 走査コマンドと結果

### 1. sonic-swss 全体で HARDWARE テーブル関連フィールド参照

```bash
grep -rn "COUNTER_MODE\|LOOKUP_MODE\|TCAM_SHARING\|HARDWARE|ACCESS_LIST" \
  .cache/sonic-sources/sonic-swss/ 2>/dev/null | grep -v ".pyc|Binary"
```

結果: **マッチ 0 件**。orchagent (aclorch.cpp 含む)、cfgmgr、fpmsyncd のいずれにも
`COUNTER_MODE` / `LOOKUP_MODE` / `TCAM_SHARING` の参照は存在しない。

### 2. sonic-swss で "HARDWARE" テーブルキーのパターン検索

```bash
grep -rn '"HARDWARE"' .cache/sonic-sources/sonic-swss/ 2>/dev/null
```

結果: **マッチ 0 件**。`HARDWARE|ACCESS_LIST` を SubscriberStateTable / ConsumerStateTable /
ConfigDBConnector で受信するコードは存在しない。

### 3. sonic-gnmi 本番コード (testdata 除外)

```bash
grep -rn "HARDWARE\|ACCESS_LIST\|COUNTER_MODE\|LOOKUP_MODE" \
  .cache/sonic-sources/sonic-gnmi/ 2>/dev/null | grep -v "testdata|.pyc"
```

結果: **マッチ 0 件** (testdata/db_dump.json のみにヒット。本番コードには参照なし)。

### 4. sonic-mgmt-common 本番コード (test 除外)

```bash
grep -rn "HARDWARE\b" .cache/sonic-sources/sonic-mgmt-common/ 2>/dev/null \
  | grep -v ".pyc|test|testdata"
```

結果: **マッチ 0 件** (tools/test/dbinit.py のみにヒット)。

### 5. sonic-utilities / sonic-host-services

```bash
grep -rn "HARDWARE\|COUNTER_MODE\|LOOKUP_MODE\|TCAM_SHARING" \
  .cache/sonic-sources/sonic-utilities/ \
  .cache/sonic-sources/sonic-host-services/ 2>/dev/null | grep -v ".pyc|Binary"
```

結果: **マッチ 0 件**。

## Phase F 結論: 副次 DB 書込なし

`HARDWARE|ACCESS_LIST` は community SONiC の **dead consumer** テーブルである。
購読者が存在しないため、SET/DEL 操作に伴って APPL_DB / STATE_DB / COUNTERS_DB /
ASIC_DB / FLEX_COUNTER_DB のいずれへも副次書き込みは発生しない。

## Phase G 結論: 通信メカニズムなし

community SONiC コードパス全体を通じて `HARDWARE|ACCESS_LIST` を購読する
SubscriberStateTable / ConsumerStateTable / ConfigDBConnector.subscribe() が 0 件。
通知パス・pub-sub メカニズムは存在しない。

## Phase H 結論: プラットフォーム差なし

HARDWARE テーブルは dead consumer のため、ASIC 種別 / multi-asic / chassis 構成を問わず
一切の動作差異が生じない。SAI API も呼ばれない。

## 根拠サマリ

| 検証項目 | 対象コード | 結果 |
|---|---|---|
| COUNTER_MODE / LOOKUP_MODE / TCAM_SHARING の参照 | sonic-swss 全体 | 0 件 |
| "HARDWARE" テーブルキーの購読 | sonic-swss 全体 | 0 件 |
| APPL_DB / STATE_DB / COUNTERS_DB への書込 | 全 consumer (存在しない) | 0 件 |
| gNMI 本番コードでの参照 | sonic-gnmi (testdata 除く) | 0 件 |
| mgmt-common 本番コードでの参照 | sonic-mgmt-common (test 除く) | 0 件 |
| プラットフォーム/ASIC 差分 | buildimage / platform-daemons | 0 件 |
