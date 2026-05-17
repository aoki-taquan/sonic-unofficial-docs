# SRV6_MY_SIDS — Phase E 定数・上限値スキャンノート

対象テーブル: `SRV6_MY_SIDS|<locator_name>|<ip_prefix>`
Consumer (bgpcfgd): `SRv6Mgr` (`sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py`)
Consumer (orchagent): `Srv6Orch` (`sonic-swss/orchagent/srv6orch.cpp`)
スキャン範囲:
  - `srv6orch.cpp:19-27` (マクロ定数)
  - `srv6orch.cpp:41-79` (エンドポイント動作マップ)
  - `srv6orch.cpp:81-96` (DSCP mode 変換関数)
  - `srv6orch.cpp:490-540` (IPinIP トンネル作成)
  - `srv6orch.h:30, 151-152` (ヘッダ定数)
  - `managers_srv6.py:6-11` (bgpcfgd 定数)
Evidence: sonic-buildimage sha `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`, sonic-swss sha `4305596156d70e9797e8a881b3d19b46de0bce0d`

---

## 検出した定数・マジックナンバー・ハードコード値

### srv6orch.cpp — #define マクロ

| 定数名 | 値 | 意味 | 参照箇所 |
|--------|-----|------|---------|
| `ADJ_DELIMITER` | `','` (カンマ) | adjacency フィールドの区切り文字。現在 ECMP は未サポートのため複数指定は即 return false | `srv6orch.cpp:19`, `srv6orch.cpp:1515` |
| `OVERLAY_RIF_DEFAULT_MTU` | `9100` | IPinIP トンネル用オーバーレイ RIF（ループバック型）に設定する固定 MTU 値（バイト） | `srv6orch.cpp:20`, `srv6orch.cpp:502` |
| `LOCATOR_DEFAULT_BLOCK_LEN` | `"32"` | ロケータのブロック長デフォルト（ビット）。APPL_DB エントリのビット長未指定時に `getLocatorCfgFromDb()` で使用 | `srv6orch.cpp:21`, `srv6orch.cpp:347` |
| `LOCATOR_DEFAULT_NODE_LEN` | `"16"` | ロケータのノード長デフォルト（ビット） | `srv6orch.cpp:22`, `srv6orch.cpp:348` |
| `LOCATOR_DEFAULT_FUNC_LEN` | `"16"` | ロケータの関数長デフォルト（ビット） | `srv6orch.cpp:23`, `srv6orch.cpp:349` |
| `LOCATOR_DEFAULT_ARG_LEN` | `"0"` | ロケータの引数長デフォルト（ビット） | `srv6orch.cpp:24`, `srv6orch.cpp:350` |
| `SRV6_FLEX_COUNTER_UPDATE_TIMER` | `1` | FlexCounter タイマー間隔（秒）。カウンタ有効時に統計更新を駆動する | `srv6orch.cpp:26`, `srv6orch.cpp:138` |
| `SRV6_STAT_COUNTER_POLLING_INTERVAL_MS` | `10000` | FlexCounter ポーリング間隔（ミリ秒 = 10 秒）。カウンタ有効時の実測サイクル | `srv6orch.cpp:27`, `srv6orch.cpp:108` |

### srv6orch.h — ヘッダ定数

| 定数名 | 値 | 意味 | 参照箇所 |
|--------|-----|------|---------|
| `SRV6_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"SRV6_STAT_COUNTER"` | COUNTERS_DB の FlexCounter グループ名 | `srv6orch.h:30` |
| `SID_LIST_DELIMITER` | `','` | SID リスト（SRv6 tunnel）の区切り文字 | `srv6orch.h:151` |
| `MY_SID_KEY_DELIMITER` | `':'` | `sai_my_sid_entry_t` の key 組み立てに使う区切り文字（block_len:node_len:func_len:arg_len:IPv6） | `srv6orch.h:152` |

### managers_srv6.py — Python 定数

| 定数名 | 値 | 意味 | 参照箇所 |
|--------|-----|------|---------|
| `DEFAULT_VRF` | `"default"` | `decap_vrf` フィールドのデフォルト値・比較基準文字列 | `managers_srv6.py:11`, `:150` |
| `SRV6_MY_SIDS_TABLE_NAME` | `"SRV6_MY_SIDS"` | bgpcfgd が監視するテーブル名文字列 | `managers_srv6.py:12` |
| `supported_SRv6_behaviors` | `{'uN', 'uDT46'}` | bgpcfgd が受理する action 値の集合（FRR 経由通知対象）。それ以外は `log_err` + `return False` | `managers_srv6.py:6-8` |

### IPinIP トンネル作成時のハードコード属性（srv6orch.cpp:490-540）

`decap_dscp_mode` が指定されていると `createMySidIpInIpTunnel()` が呼ばれ、以下の値が SAI に直接渡される:

| SAI 属性 | ハードコード値 | 意味 |
|---------|--------------|------|
| `SAI_ROUTER_INTERFACE_ATTR_TYPE` | `SAI_ROUTER_INTERFACE_TYPE_LOOPBACK` | オーバーレイ RIF 種別（ループバック固定） |
| `SAI_ROUTER_INTERFACE_ATTR_MTU` | `9100` (`OVERLAY_RIF_DEFAULT_MTU`) | オーバーレイ RIF の MTU（固定値、設定変更不可） |
| `SAI_TUNNEL_ATTR_TYPE` | `SAI_TUNNEL_TYPE_IPINIP` | トンネル種別（IP-in-IP 固定） |
| `SAI_TUNNEL_ATTR_PEER_MODE` | `SAI_TUNNEL_PEER_MODE_P2MP` | ピアモード（P2MP 固定） |
| `SAI_TUNNEL_ATTR_DECAP_TTL_MODE` | `SAI_TUNNEL_TTL_MODE_PIPE_MODEL` | TTL モード（pipe 固定・設定変更不可） |
| `SAI_TUNNEL_ATTR_DECAP_DSCP_MODE` | `decap_dscp_mode` フィールドの値 | DSCP モード（`uniform` / `pipe` を設定値から決定） |
| `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE` | `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2MP` | トンネルターミネーション種別（P2MP 固定） |

**注意**: TTL モードは `SAI_TUNNEL_TTL_MODE_PIPE_MODEL` にハードコードされており、CONFIG_DB フィールドでは制御できない。`decap_dscp_mode` のみがユーザーが制御可能なトンネルパラメータである。

### action → SAI エンドポイント動作マッピング（end_behavior_map）

`srv6orch.cpp:41-62` に定義された完全なマッピング。CONFIG_DB の `SRV6_MY_SIDS.action` に設定できる値と SAI 定数の対応:

| CONFIG_DB action 値 | SAI 定数 |
|--------------------|---------|
| `end` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_E` |
| `end.x` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_X` |
| `end.t` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_T` |
| `end.dx6` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_DX6` |
| `end.dx4` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_DX4` |
| `end.dt4` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_DT4` |
| `end.dt6` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_DT6` |
| `end.dt46` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_DT46` |
| `end.b6.encaps` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_B6_ENCAPS` |
| `end.b6.encaps.red` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_B6_ENCAPS_RED` |
| `end.b6.insert` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_B6_INSERT` |
| `end.b6.insert.red` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_B6_INSERT_RED` |
| `udx6` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UDX6` |
| `udx4` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UDX4` |
| `udt6` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UDT6` |
| `udt4` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UDT4` |
| `udt46` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UDT46` |
| `un` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UN` |
| `ua` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UA` |

**重要**: bgpcfgd は `supported_SRv6_behaviors = {'uN', 'uDT46'}` のみを受理する（大文字 `uN`、`uDT46`）。Srv6Orch は `end_behavior_map` の 19 種全てを受理するが、CONFIG_DB 経由の bgpcfgd パスでは事実上 `uN`/`uDT46` のみが通過する。APPL_DB 直接書込みの場合はより多くの action が利用可能。

### action → SAI フレーバーマッピング（end_flavor_map）

`srv6orch.cpp:64-71` に定義。フレーバー未定義の action は `NONE`（`if (end_flavor != SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_FLAVOR_NONE)` で属性未設定）:

| action 値 | SAI フレーバー |
|-----------|-------------|
| `end` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_FLAVOR_PSP_AND_USD` |
| `end.x` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_FLAVOR_PSP_AND_USD` |
| `end.t` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_FLAVOR_PSP_AND_USD` |
| `un` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_FLAVOR_NONE` |
| `ua` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_FLAVOR_PSP_AND_USD` |
| `udt46` (トンネル経由時) | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_FLAVOR_USD`（`srv6orch.cpp:1575` でハードコード上書き） |
| その他 (`udx4` 等) | フレーバー属性なし（`NONE` ⇒ SAI 属性未送信） |

---

## 定数利用サマリ

1. **Overlay RIF MTU 9100**: IPinIP トンネル用ループバック RIF は必ず 9100 バイト MTU で作成される。ジャンボフレーム対応済みのハードウェアでは問題ないが、MTU が低い環境では断片化が生じる可能性がある。CONFIG_DB からの変更手段は現在存在しない。
2. **TTL mode は pipe 固定**: `decap_dscp_mode` で DSCP は制御できるが、TTL は常に `PIPE_MODEL`（内部 TTL を外側ヘッダに伝播しない）。
3. **FlexCounter 間隔 10 秒**: カウンタ有効時の統計ポーリングは 10 秒固定。高頻度カウンタ取得が必要な場合は FlexCounter の設定変更が必要（CONFIG_DB フィールドではなく、flex counter orch 側の設定）。
4. **bgpcfgd の supported_SRv6_behaviors は 2 種のみ**: Srv6Orch は 19 種の action を SAI にマップできるが、bgpcfgd は `uN`/`uDT46` 以外を拒否する。追加 action が必要な場合は APPL_DB 直書き（fpmsyncd 経由）が必要。
