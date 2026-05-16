# bfdorch — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-net/sonic-swss/orchagent/bfdorch.cpp` (マクロ定義、SAI 属性マッピング、`bfd_src_port()` ロジック)
- `sonic-net/sonic-swss/orchagent/bfdorch.h` (型宣言、外部 API)

---

## 1. BFD セッションパラメータデフォルト (bfdorch.cpp L15-22)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `BFD_SESSION_DEFAULT_TX_INTERVAL` | `1000` | TX 間隔のデフォルト (ms)。`tx_interval` 未指定時に適用。SAI 投入時に ×1000 して μs 変換 | `bfdorch.cpp:15` |
| `BFD_SESSION_DEFAULT_RX_INTERVAL` | `1000` | 最小 RX 間隔のデフォルト (ms)。`rx_interval` 未指定時に適用。SAI 投入時に ×1000 して μs 変換 | `bfdorch.cpp:16` |
| `BFD_SESSION_DEFAULT_DETECT_MULTIPLIER` | `10` | 検知乗数 (detect multiplier) のデフォルト。`multiplier` 未指定時に適用 | `bfdorch.cpp:17` |
| `BFD_SESSION_DEFAULT_TOS` | `192` | IP TOS のデフォルト (= DSCP 48 << 2 \| ECN 0 = 0xC0)。コメントで明示: "default 6-bit DSCP value 48, default 2-bit ecn value 0. 48<<2 = 192" | `bfdorch.cpp:18-19` |
| `BFD_SESSION_MILLISECOND_TO_MICROSECOND` | `1000` | ms → μs 変換係数。SAI `MIN_TX` / `MIN_RX` 属性に渡す際に乗じる | `bfdorch.cpp:20` |

---

## 2. UDP ソースポート範囲とリトライ (bfdorch.cpp L21-23)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `BFD_SRCPORTINIT` | `49152` | BFD UDP src port のローテーション開始値 (IANA ephemeral port 開始値) | `bfdorch.cpp:21` |
| `BFD_SRCPORTMAX` | `65536` | UDP src port ローテーションの上限値 (実際にこの値に達すると `BFD_SRCPORTINIT` にリセット)。よって有効範囲は `49152 ≤ port < 65536` (= 49152–65535) | `bfdorch.cpp:22` |
| `NUM_BFD_SRCPORT_RETRIES` | `3` | SAI `create_bfd_session()` が失敗した場合に UDP src port を更新して最大何回リトライするか | `bfdorch.cpp:23` |

> `bfd_src_port()` は `static uint32_t port = BFD_SRCPORTINIT;` を保持し、呼ばれるたび `port++` を返す。`port >= BFD_SRCPORTMAX` で `BFD_SRCPORTINIT` にラップ。`retry_create_bfd_session()` は `NUM_BFD_SRCPORT_RETRIES (=3)` 回ループして `update_port_number()` で `SAI_BFD_SESSION_ATTR_UDP_SRC_PORT` を新しい値で上書きする。<!-- evidence: bfdorch.cpp:580-606, 647-655 -->

---

## 3. BFD セッション種別マッピング (bfdorch.cpp L33-46)

`session_type_map` (string → SAI enum) と `session_type_lookup` (SAI enum → string) の双方向 lookup テーブル。`type` フィールドの文字列値と SAI 列挙の対応:

| `type` 文字列 | SAI 列挙 |
|--------------|----------|
| `"demand_active"` | `SAI_BFD_SESSION_TYPE_DEMAND_ACTIVE` |
| `"demand_passive"` | `SAI_BFD_SESSION_TYPE_DEMAND_PASSIVE` |
| `"async_active"` | `SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE` |
| `"async_passive"` | `SAI_BFD_SESSION_TYPE_ASYNC_PASSIVE` |

未指定時のデフォルトは `SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE` (`bfdorch.cpp:340`)。<!-- evidence: bfdorch.cpp:33-46, 340 -->

---

## 4. BFD セッション状態マッピング (bfdorch.cpp L48-54)

`session_state_lookup` (SAI enum → string)。STATE_DB `BFD_SESSION_TABLE` の `state` フィールドにそのまま書かれる文字列値:

| SAI 列挙 | 文字列 |
|---------|--------|
| `SAI_BFD_SESSION_STATE_ADMIN_DOWN` | `"Admin_Down"` |
| `SAI_BFD_SESSION_STATE_DOWN` | `"Down"` |
| `SAI_BFD_SESSION_STATE_INIT` | `"Init"` |
| `SAI_BFD_SESSION_STATE_UP` | `"Up"` |

セッション作成直後の初期状態は `SAI_BFD_SESSION_STATE_DOWN` (`bfdorch.cpp:544, 567, 571, 679`)。<!-- evidence: bfdorch.cpp:48-54 -->

---

## 5. SAI 属性 ID 一覧 (bfdorch.cpp L415-530)

`create_bfd_session()` が SAI に投入する属性 ID:

| SAI 属性 ID | 用途 | ソース |
|------------|------|--------|
| `SAI_BFD_SESSION_ATTR_TYPE` | セッション種別 | `bfdorch.cpp:415` |
| `SAI_BFD_SESSION_ATTR_LOCAL_DISCRIMINATOR` | ローカル discriminator (`bfd_gen_id()` で 1 から単調増加) | `bfdorch.cpp:421` |
| `SAI_BFD_SESSION_ATTR_UDP_SRC_PORT` | UDP src port (`bfd_src_port()` の戻り値) | `bfdorch.cpp:426-427` |
| `SAI_BFD_SESSION_ATTR_REMOTE_DISCRIMINATOR` | リモート discriminator (`0` 固定で開始) | `bfdorch.cpp:430` |
| `SAI_BFD_SESSION_ATTR_BFD_ENCAPSULATION_TYPE` | カプセル化種別 (`NONE` 固定) | `bfdorch.cpp:434` |
| `SAI_BFD_SESSION_ATTR_IPHDR_VERSION` | IP ヘッダバージョン (4 or 6) | `bfdorch.cpp:438` |
| `SAI_BFD_SESSION_ATTR_SRC_IP_ADDRESS` | 送信元 IP | `bfdorch.cpp:442` |
| `SAI_BFD_SESSION_ATTR_DST_IP_ADDRESS` | 宛先 IP | `bfdorch.cpp:447` |
| `SAI_BFD_SESSION_ATTR_MIN_TX` | 最小 TX 間隔 (μs) | `bfdorch.cpp:451-452` |
| `SAI_BFD_SESSION_ATTR_MIN_RX` | 最小 RX 間隔 (μs) | `bfdorch.cpp:456-457` |
| `SAI_BFD_SESSION_ATTR_MULTIPLIER` | 検知乗数 | `bfdorch.cpp:461-462` |
| `SAI_BFD_SESSION_ATTR_TOS` | IP TOS | `bfdorch.cpp:466` |
| `SAI_BFD_SESSION_ATTR_MULTIHOP` | マルチホップフラグ | `bfdorch.cpp:472` |
| `SAI_BFD_SESSION_ATTR_HW_LOOKUP_VALID` | HW lookup 有効/無効 (`interface == "default"` で `true`) | `bfdorch.cpp:505` |
| `SAI_BFD_SESSION_ATTR_PORT` | 出力ポート OID (`interface != "default"` 時) | `bfdorch.cpp:509` |
| `SAI_BFD_SESSION_ATTR_SRC_MAC_ADDRESS` | 送信元 MAC (`interface != "default"` 時、ポート MAC) | `bfdorch.cpp:513` |
| `SAI_BFD_SESSION_ATTR_DST_MAC_ADDRESS` | 宛先 MAC (`interface != "default"` 時、`dst_mac` フィールド) | `bfdorch.cpp:517` |
| `SAI_BFD_SESSION_ATTR_VIRTUAL_ROUTER` | VRF OID (`interface == "default"` 時のみ) | `bfdorch.cpp:530` |
| `SAI_BFD_SESSION_ATTR_OFFLOAD_TYPE` | offload 種別判定 (capability check で `!= NONE` のとき hardware offload とみなす) | `bfdorch.cpp:787` |
| `SAI_BFD_SESSION_OFFLOAD_TYPE_NONE` | offload 無効値 (capability 比較用) | `bfdorch.cpp:787` |

---

## 6. その他のリテラル / 初期値

| 項目 | 値 | 用途 | ソース |
|------|----|------|--------|
| `bfd_session_type` 初期値 | `SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE` | `type` フィールド未指定時 | `bfdorch.cpp:340` |
| `encapsulation_type` 初期値 | `SAI_BFD_ENCAPSULATION_TYPE_NONE` | エンキャプ未対応 (固定) | `bfdorch.cpp:341` |
| `multihop` 初期値 | `false` | `multihop` フィールド未指定時 | `bfdorch.cpp:347` |
| `bfd_gen_id()` 開始値 | `1` (`static uint32_t session_id = 1;` を post-increment) | ローカル discriminator 単調増加カウンタ | `bfdorch.cpp:643-645` |
| 初期セッション state | `"Down"` | STATE_DB 投入時の初期 `state` | `bfdorch.cpp:544` |
| Remote discriminator 初期値 | `0` | SAI `REMOTE_DISCRIMINATOR` 属性初期値 (BFD ピア発見前) | `bfdorch.cpp:430` |
| VRF 既定値 | `"default"` | `vrf_name == "default"` のとき `gVirtualRouterId` を直接使用 | `bfdorch.cpp:520-528` |
| Interface 既定値 | `"default"` | `alias == "default"` で hardware lookup 有効モード | `bfdorch.cpp:471 以降` |

---

## 特記事項

1. **`BFD_SRCPORTMAX = 65536` は exclusive 上限**: `port >= BFD_SRCPORTMAX` でラップなので、実際に SAI に渡される値域は `49152–65535` (UDP 16bit max まで)。これは BFD RFC 5881 §4 が要求する src port 範囲 (49152–65535) と一致。
2. **`TOS = 192` の出所**: ソースコードのコメント (L18) に明記。DSCP 48 (Network Control) を ToS フィールド (上位 6bit) にシフトし、下位 2bit (ECN) を 0 にした値。`tos` フィールド未指定時に常に 0xC0 が SAI に渡される。
3. **`tx_interval` / `rx_interval` 単位変換**: テーブル上はミリ秒、SAI 上はマイクロ秒。`BFD_SESSION_MILLISECOND_TO_MICROSECOND (=1000)` を乗じて変換 (`bfdorch.cpp:452, 457`)。よって `tx_interval=1000` は SAI に `1,000,000 μs = 1 秒` として渡される。
4. **`NUM_BFD_SRCPORT_RETRIES = 3` のリトライは UDP port 競合用**: SAI が `SAI_STATUS_FAILURE` で返した場合に、UDP src port を `bfd_src_port()` で次の値に進めて再試行する。最初の失敗 + リトライ 3 回 = 計 4 回の `create_bfd_session()` 呼び出しが理論上の上限。
5. **`bfd_src_port()` の static state は orchagent プロセス内グローバル**: 全 BFD セッションで同じカウンタを共有。プロセス再起動で `49152` から再開し、UDP port の再利用が発生しうる (リモート peer 側が古い session を即解放しない場合に競合の可能性)。
6. **`bfd_gen_id()` の `session_id = 1` 開始**: BFD ローカル discriminator は RFC 5880 §6.8.1 で「0 以外の一意の non-zero 値」が要求される。`session_id = 1` 初期値 + post-increment で `1, 2, 3, ...` を生成。プロセス再起動で 1 に戻る点に注意 (リモート側からは古い discriminator の再利用に見える)。
7. **`SAI_BFD_SESSION_TYPE_DEMAND_*` は実装上 lookup には存在するが、現実の SONiC 用途は `async_active` がほぼ唯一**: BGP や static route の BFD 連携は `async_active` を使う。`demand_*` を CLI 経由で設定する経路は確認されていない (純粋に SAI 経由のテストモード用)。
8. **`bfdorch.cpp` に `multihop` のデフォルト false 以外の SAI 値関連定数は存在しない**: SAI 側で `SAI_BFD_SESSION_ATTR_MULTIHOP` は boolean。

---

## スキャン証跡

- `bfdorch.cpp` L1-60, L33-54, L340-475, L505-530, L580-655, L780-800 を読了
- マクロ定数 7 件、SAI 列挙文字列マップ 4+4=8 件、状態マップ 4 件、SAI 属性 ID 約 20 件、初期値リテラル 7 件を抽出

---

## 出典

- `sonic-net/sonic-swss/orchagent/bfdorch.cpp` L15-23, L33-54, L340-347, L415-530, L580-606, L643-655
- `sonic-net/sonic-swss/orchagent/bfdorch.h` (型宣言)
