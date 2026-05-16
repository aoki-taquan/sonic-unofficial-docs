# MACSEC_PROFILE — Phase E ハードコード定数

生成日: 2026-05-16 (task F Phase E)

<!-- constants -->
## Phase E: ハードコード定数抽出

### macsecmgr.cpp 固定値

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `AES_LEN_128_BYTE` | `66` | CAK 文字列長チェック: GCM-AES-128 / GCM-AES-XPN-128 の場合に要求される hex 文字数 | `cfgmgr/macsecmgr.cpp:48` |
| `AES_LEN_256_BYTE` | `130` | CAK 文字列長チェック: GCM-AES-256 / GCM-AES-XPN-256 の場合に要求される hex 文字数 | `cfgmgr/macsecmgr.cpp:49` |
| `RETRY_TIME` | `30` | wpa_supplicant 起動失敗時のリトライ最大回数 | `cfgmgr/macsecmgr.cpp:32` |
| `RETRY_INTERVAL` | `100` ms | wpa_supplicant リトライ間隔 (ミリ秒) | `cfgmgr/macsecmgr.cpp:35` |
| `rekey_period` デフォルト | `0` | `GetValue(ta, rekey_period)` 失敗時のフォールバック値。0 は能動的 SAK 再生成なしを意味する | `cfgmgr/macsecmgr.cpp:377-379` |
| `WPA_SUPPLICANT_CMD` | `"/sbin/wpa_supplicant"` | wpa_supplicant バイナリパス (ハードコード) | `cfgmgr/macsecmgr.cpp:27` |
| `WPA_CLI_CMD` | `"/sbin/wpa_cli"` | wpa_cli バイナリパス (ハードコード) | `cfgmgr/macsecmgr.cpp:28` |
| `WPA_CONF` | `"/etc/wpa_supplicant.conf"` | wpa_supplicant 設定ファイルパス | `cfgmgr/macsecmgr.cpp:29` |
| `SOCK_DIR` | `"/var/run/"` | wpa_supplicant Unix ソケットディレクトリ | `cfgmgr/macsecmgr.cpp:30` |

### cipher_suite 文字列 → SAI enum マッピング (macsecmgr.cpp)

| CONFIG_DB 文字列 | SAI enum / 内部 enum | CAK hex 長 |
|----------------|---------------------|-----------|
| `"GCM-AES-128"` | `CipherSuite::GCM_AES_128` | 66 文字 |
| `"GCM-AES-256"` | `CipherSuite::GCM_AES_256` | 130 文字 |
| `"GCM-AES-XPN-128"` | `CipherSuite::GCM_AES_XPN_128` | 66 文字 |
| `"GCM-AES-XPN-256"` | `CipherSuite::GCM_AES_XPN_256` | 130 文字 |
| その他 | `throw std::invalid_argument("Invalid cipher_suite : ...")` | — |

<!-- evidence: cfgmgr/macsecmgr.cpp:69-91, 113-135 -->

### macsecorch.cpp 固定値

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `DEFAULT_ENABLE_ENCRYPT` | `true` | 新規ポート初期化時の暗号化有効フラグ | `orchagent/macsecorch.cpp:40` |
| `DEFAULT_SCI_IN_SECTAG` | `false` | 新規ポート初期化時の SCI in SecTAG フラグ (`send_sci` フィールドとは逆向き注意) | `orchagent/macsecorch.cpp:41` |
| `DEFAULT_CIPHER_SUITE` | `SAI_MACSEC_CIPHER_SUITE_GCM_AES_128` | 新規ポート初期化時のデフォルト cipher suite。CONFIG_DB の `cipher_suite` デフォルト `GCM-AES-128` と対応 | `orchagent/macsecorch.cpp:42` |
| `EAPOL_ETHER_TYPE` | `0x888E` | EAPOL フレーム識別用 EtherType。ACL バイパスルールに使用 | `orchagent/macsecorch.cpp:25` |
| `PAUSE_ETHER_TYPE` | `0x8808` | PAUSE フレーム識別用 EtherType。ACL バイパスルールに使用 | `orchagent/macsecorch.cpp:26` |
| `MACSEC_STAT_XPN_POLLING_INTERVAL_MS` | `1000` ms | XPN cipher suite 使用時の SA 統計ポーリング間隔 (1 秒) | `orchagent/macsecorch.cpp:27` |
| `MACSEC_STAT_POLLING_INTERVAL_MS` | `10000` ms | 通常 cipher suite 使用時の SA 統計ポーリング間隔 (10 秒) | `orchagent/macsecorch.cpp:28` |
| `AVAILABLE_ACL_PRIORITIES_LIMITATION` | `32` | MACsec ACL ルールに使用可能な優先度数の上限 | `orchagent/macsecorch.cpp:24` |
| `PFC_MODE_DEFAULT` | `"bypass"` | PFC モードのデフォルト値 (暗号化をバイパス) | `orchagent/macsecorch.cpp:32` |

### PFC mode 文字列定数 (macsecorch.cpp)

| 定数 | 値 | 意味 |
|-----|-----|------|
| `PFC_MODE_BYPASS` | `"bypass"` | PFC フレームを MACsec 暗号化対象から除外 (デフォルト) |
| `PFC_MODE_ENCRYPT` | `"encrypt"` | PFC フレームも MACsec 暗号化対象に含める |
| `PFC_MODE_STRICT_ENCRYPT` | `"strict_encrypt"` | 厳格モード: MACsec 有効ポートでは PFC を必ず暗号化 |

<!-- evidence: orchagent/macsecorch.cpp:29-32 -->
<!-- /constants -->
