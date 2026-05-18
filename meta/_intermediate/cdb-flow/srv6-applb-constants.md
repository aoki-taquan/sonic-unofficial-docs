# APPL_DB SRV6 テーブル — Phase E ハードコード定数スキャンノート

対象テーブル: `SRV6_MY_SID_TABLE` / `SRV6_SID_LIST_TABLE` (APPL_DB)
Consumer: `Srv6Orch` (`sonic-swss/orchagent/srv6orch.cpp`)
スキャン範囲: `srv6orch.cpp` L19-27 (#define 群) および全関数の定数利用箇所精読

---

## 検出したハードコード定数

### 1. ADJ_DELIMITER = ',' (srv6orch.cpp:19)

```cpp
#define ADJ_DELIMITER ','
```

`createUpdateMysidEntry()` (srv6orch.cpp:1515) は `adj` フィールドをカンマ区切りでトークン化する。
`adjv.size() > 1` の場合は ECMP adjacency として拒否される (srv6orch.cpp:1516-1519)。
現バージョンでは ECMP adjacency は非対応で、`adj` には単一 IP アドレスのみ指定可能。

**影響**: `adj` フィールドに複数 IP をカンマ区切りで指定しても SAI 登録失敗し、ECMP 非対応エラーになる。

evidence: `srv6orch.cpp:19`, `srv6orch.cpp:1515-1519`

### 2. OVERLAY_RIF_DEFAULT_MTU = 9100 (srv6orch.cpp:20)

```cpp
#define OVERLAY_RIF_DEFAULT_MTU 9100
```

`mySidTunnelRequired()` が真の行動（DSCP モード設定が必要な MySID）に対して
`createMySidIpInIpTunnel()` がオーバーレイ RIF を作成する際に使用する固定 MTU 値 (srv6orch.cpp:502)。
この値は CONFIG_DB や APPL_DB から取得されず、コードに埋め込まれている。

**影響**: IP-in-IP トンネルを伴う MySID エントリ（特定 DSCP モード設定時）は、オーバーレイ RIF が常に MTU 9100 bytes で作成される。MTU 変更は不可。

evidence: `srv6orch.cpp:20`, `srv6orch.cpp:502`

### 3. LOCATOR_DEFAULT_{BLOCK,NODE,FUNC,ARG}_LEN (srv6orch.cpp:21-24)

```cpp
#define LOCATOR_DEFAULT_BLOCK_LEN "32"
#define LOCATOR_DEFAULT_NODE_LEN  "16"
#define LOCATOR_DEFAULT_FUNC_LEN  "16"
#define LOCATOR_DEFAULT_ARG_LEN   "0"
```

`getLocatorCfgFromDb()` (srv6orch.cpp:347-350) が CONFIG_DB `SRV6_MY_LOCATORS` のフィールドを読む際、
フィールドが欠落している場合に `get_value_or()` のデフォルト引数として使用する。
`SRV6_MY_SID_TABLE` key のパース時にも関連する（key 内のビット長フィールドが 0 の場合のフォールバック）。

**影響**: `SRV6_MY_LOCATORS` でビット長を省略すると、Orch 内部では 32+16+16+0=64 ビットとして処理される。
カウンタキー生成（`getMySidCounterKey()`）も同一定数を使用するため、COUNTERS_DB のプレフィックスキーに影響する。

evidence: `srv6orch.cpp:21-24`, `srv6orch.cpp:347-350`

---

## 定数サマリ

| 定数名 | 値 | 利用箇所 | 設定変更可否 |
|--------|-----|---------|------------|
| `ADJ_DELIMITER` | `','` | `createUpdateMysidEntry()` adj トークン化 | 不可（コード変更必須） |
| `OVERLAY_RIF_DEFAULT_MTU` | `9100` | `createMySidIpInIpTunnel()` RIF 作成時 | 不可（コード変更必須） |
| `LOCATOR_DEFAULT_BLOCK_LEN` | `"32"` | `getLocatorCfgFromDb()` フォールバック | `SRV6_MY_LOCATORS` で上書き可 |
| `LOCATOR_DEFAULT_NODE_LEN` | `"16"` | `getLocatorCfgFromDb()` フォールバック | `SRV6_MY_LOCATORS` で上書き可 |
| `LOCATOR_DEFAULT_FUNC_LEN` | `"16"` | `getLocatorCfgFromDb()` フォールバック | `SRV6_MY_LOCATORS` で上書き可 |
| `LOCATOR_DEFAULT_ARG_LEN` | `"0"` | `getLocatorCfgFromDb()` フォールバック | `SRV6_MY_LOCATORS` で上書き可 |
