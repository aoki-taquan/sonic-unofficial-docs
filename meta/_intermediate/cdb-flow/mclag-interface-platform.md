# mclag-interface / プラットフォーム差異 (Phase H 中間メモ)

対象: `docs/reference/config-db/mclag-interface.md`
（`MCLAG_INTERFACE` テーブル）

スコープ: ポート隔離（Port Isolation）メカニズムのプラットフォーム差、multi-ASIC / VoQ 非対応、MlagOrch の SAI 非依存設計を `mclagsyncd/mclaglink.cpp` / `mclagsyncd/mclaglink.h` / `orchagent/mlagorch.cpp` の master から抜き出してまとめる。

---

## 1. Port Isolation の 2 系統（プラットフォーム分岐）

### 1.1 分岐の起点: `setPortIsolate()` の platform ホワイトリスト

`mclaglink.cpp:190-380` の `MclagLink::setPortIsolate()` は、ICCP セッション経由で iccpd から受け取った port isolation 指示を APPL_DB に変換する。この関数の先頭でプラットフォーム文字列を `getenv("platform")` で取得し、ホワイトリストと照合する。

```cpp
// mclaglink.cpp:192-202
static const unordered_set<string> supported {
    BRCM_PLATFORM_SUBSTRING,   // "broadcom"
    BFN_PLATFORM_SUBSTRING,    // "barefoot"
    CTC_PLATFORM_SUBSTRING,    // "centec"
    CLX_PLATFORM_SUBSTRING,    // "clounix"
    MRVL_PRST_PLATFORM_SUBSTRING,  // "marvell-prestera"
    MRVL_TL_PLATFORM_SUBSTRING     // "marvell-teralynx"
};

const char *platform = getenv("platform");
if (platform != nullptr && supported.find(string(platform)) != supported.end())
{
    /* ISOLATION_GROUP_TABLE (bridge-port isolation) パス */
    ...
}
else
{
    /* ACL ベース隔離パス */
    ...
}
```

定数の宣言場所は `mclagsyncd/mclaglink.h:54-59`（`mclaglink.h` に直接定義）。

### 1.2 ホワイトリスト対応プラットフォーム: ISOLATION_GROUP_TABLE パス

| プラットフォーム文字列 | 代表 ASIC / ベンダー |
|---|---|
| `"broadcom"` | Broadcom XGS / DNX (StrataXGS, BCM56xxx, BCM88xxx) |
| `"barefoot"` | Intel Tofino / Tofino2 (P4 プログラマブル ASIC) |
| `"centec"` | Centec (CTC7132, CTC8096 等) |
| `"clounix"` | Clounix |
| `"marvell-prestera"` | Marvell Prestera (98CX/98DX 系) |
| `"marvell-teralynx"` | Marvell Teralynx |

これらのプラットフォームでは iccpd からの port isolation 指示を **APPL_DB `ISOLATION_GROUP_TABLE`** に書き込む:

```
APPL_DB:ISOLATION_GROUP_TABLE:MCLAG_ISO_GRP
  DESCRIPTION = "Isolation group for MCLAG"
  TYPE        = "bridge-port"
  PORTS       = <peer-link PortChannel>
  MEMBERS     = <リモート MCLAG PortChannel のカンマ区切りリスト>
```

`op_hdr->op_len == 0`（リモートインターフェース全断または ICCP セッション断）のとき:
- `is_iccp_up == true`: `MEMBERS` を空にして `MCLAG_ISO_GRP` を更新（グループは保持）
- `is_iccp_up == false`: `MCLAG_ISO_GRP` を DEL（グループごと削除）

### 1.3 ホワイトリスト非対応プラットフォーム: ACL ベース隔離パス

Mellanox/NVIDIA、VS、VPP、その他 SAI 実装では `ISOLATION_GROUP_TABLE` が未実装または非対応のため、ACL を代替手段として使用する。

```
APPL_DB:ACL_TABLE_TABLE:mclag
  policy_desc = "Mclag egress port isolate acl"
  type        = "L3"
  ports       = <peer-link PortChannel>

APPL_DB:ACL_RULE_TABLE:mclag:mclag
  IP_TYPE       = "ANY"
  OUT_PORTS     = <リモート MCLAG PortChannel のカンマ区切りリスト（Ethernet* 除外）>
  PACKET_ACTION = "DROP"
```

`op_hdr->op_len == 0`（メンバー全断）の場合は `ACL_TABLE_TABLE:mclag` を DEL（ACL ルールごと削除）。

`Ethernet` プレフィックスのポートは `OUT_PORTS` から除外される（`mclaglink.cpp:354-362`）。`PortChannel` プレフィックスで始まるポートのみが実効 OUT_PORTS として残る。

### 1.4 `platform` 環境変数未設定時の挙動

`platform` が `nullptr`（環境変数未設定）の場合、`supported.find()` が呼ばれず `else` ブランチ（ACL パス）に落ちる。VS / VPP 環境で `platform` を未設定のまま起動した場合も ACL パスが使われる。

---

## 2. MlagOrch は SAI 非依存でプラットフォーム差なし

`orchagent/mlagorch.cpp` は SAI API を**一切呼び出さない**。`addMlagInterface()` / `delMlagInterface()` は内部 set (`m_mlagIntfs`) の更新と Observer 通知 (`SUBJECT_TYPE_MLAG_INTF_CHANGE`) のみを行う。プラットフォーム文字列参照 (`MLNX_PLATFORM_SUBSTRING` 等) も存在しない。

```cpp
// mlagorch.cpp:193-213
bool MlagOrch::addMlagInterface(string if_name)
{
    // SAI 呼出なし。m_mlagIntfs に追加して Observer を notify するのみ
    m_mlagIntfs.insert(if_name);
    update.if_name = if_name;
    update.is_add = true;
    notify(SUBJECT_TYPE_MLAG_INTF_CHANGE, static_cast<void *>(&update));
    return true;
}
```

FdbOrch が Observer として `SUBJECT_TYPE_MLAG_INTF_CHANGE` を受け取り、FDB フラッシュ制御を行うが、FdbOrch 側にも MCLAG_INTERFACE 処理でのプラットフォーム分岐はない。

---

## 3. multi-ASIC / VoQ chassis 非対応

MCLAG 機能（`docker-iccpd` / `mclagsyncd` / `MlagOrch`）は **multi-ASIC** や **VoQ chassis** 環境を考慮していない。

- `mlagorch.cpp` に `gMySwitchType == "voq"` 等の分岐は一切なし
- `mclaglink.cpp` / `mclagsyncd.cpp` に `CHASSIS_APP_DB` 参照なし
- SONiC コミュニティ HLD では「MCLAG は single-ASIC single-box 構成を前提」とされており、multi-ASIC での動作は明示的にサポートされていない

実装上、`docker-iccpd` は単一 swss namespace の CONFIG_DB / STATE_DB / APPL_DB のみを参照するため、multi-ASIC 構成でも asic0 の名前空間にのみ接続する（iccpd 起動コマンドが namespace 引数を取らないため）。

---

## 4. VS プラットフォームでの挙動

| 機能 | VS (libsaivs) |
|---|---|
| `MlagOrch` 動作 | 問題なし（SAI 非依存） |
| Port isolation | ACL パス（`platform` が `"broadcom"` 等でないため） |
| `ISOLATION_GROUP_TABLE` 書込 | 発生しない |
| ACL (`mclag` / `mclag:mclag`) | APPL_DB に書き込まれるが orchagent (AclOrch) の SAI コールは VS SAI で処理 |
| FDB フラッシュ | FdbOrch Observer 経由で `FLUSHFDBREQUEST` 通知は送信されるが SAI は VS |

VS では ICCP セッションが実際に確立しないため、`setPortIsolate()` 自体が通常呼ばれない。

---

## 5. ドキュメント反映方針

`docs/reference/config-db/mclag-interface.md` の `<!-- /pubsub -->` の直後に `<!-- platform -->` ブロックを差し込み、以下の見出しで構成する:

1. Port Isolation の 2 系統: ISOLATION_GROUP_TABLE パス vs ACL ベース隔離パス
2. ホワイトリスト一覧（broadcom / barefoot / centec / clounix / marvell-prestera / marvell-teralynx）
3. Mellanox 等: ACL ベース隔離の動作
4. `platform` 未設定時は ACL パス
5. MlagOrch は SAI 非依存でプラットフォーム差なし
6. multi-ASIC / VoQ chassis 非対応
