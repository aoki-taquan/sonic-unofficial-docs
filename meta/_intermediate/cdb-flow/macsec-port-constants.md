# PORT.macsec フィールド — Phase E ハードコード定数スキャンノート

対象テーブル: `PORT` (macsec フィールド)
Consumer: `MACsecMgr` (`sonic-swss/cfgmgr/macsecmgr.cpp`)、`MACsecOrch` (`sonic-swss/orchagent/macsecorch.cpp`)
スキャン範囲: macsecmgr.cpp L27-49, L32-35, L853 / macsecorch.cpp L24-42 全行精読

---

## macsecmgr.cpp 定数

### プロセス起動パス定数

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `WPA_SUPPLICANT_CMD` | `"/sbin/wpa_supplicant"` | `startWPASupplicant()` で fork/exec する wpa_supplicant のフルパス | `macsecmgr.cpp:27` |
| `WPA_CLI_CMD` | `"/sbin/wpa_cli"` | `wpa_cli_exec()` / `wpa_cli_exec_and_check()` で呼び出す wpa_cli のフルパス | `macsecmgr.cpp:28` |
| `WPA_CONF` | `"/etc/wpa_supplicant.conf"` | wpa_supplicant 設定ファイルパス (起動引数として使用) | `macsecmgr.cpp:29` |
| `SOCK_DIR` | `"/var/run/"` | wpa_supplicant のソケットディレクトリ。`SOCK_DIR + port_name` でソケットパスを構成 | `macsecmgr.cpp:30` |

### wpa_supplicant 起動ポーリング定数

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `RETRY_TIME` | `30` (回) | `startWPASupplicant()` 内で wpa_supplicant ソケット接続を試みる最大回数。0 になるとタイムアウト判定して `stopWPASupplicant()` へ | `macsecmgr.cpp:32` |
| `RETRY_INTERVAL` | `100` (ms) | 各ポーリング試行間の待機時間 (ミリ秒)。合計最大待機 = 30 × 100 = **3000 ms** | `macsecmgr.cpp:35` |

### interface_remove リトライ定数

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `MAX_INTERFACE_REMOVE_RETRIES` | `3` | `unconfigureMACsec()` 内で wpa_cli `interface_remove` コマンドがタイムアウトした場合の最大リトライ回数。各リトライ間は 10 秒待機。FAIL応答は即時成功扱い | `macsecmgr.cpp:853` |

### AES キー長検証定数

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `AES_LEN_128_BYTE` | `66` bytes | AES-128 暗号スイートの CAK エンコード済み文字列長。先頭 2 bytes = magic salt index、残り 64 bytes = 32 byte CAK のエンコード | `macsecmgr.cpp:48` |
| `AES_LEN_256_BYTE` | `130` bytes | AES-256 暗号スイートの CAK エンコード済み文字列長。先頭 2 bytes = magic salt index、残り 128 bytes = 32 byte CAK のエンコード | `macsecmgr.cpp:49` |

---

## macsecorch.cpp 定数

### MACsec Port オブジェクト初期値 (SAI 属性デフォルト)

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `DEFAULT_ENABLE_ENCRYPT` | `true` | MACsec Port 作成時の暗号化有効フラグ初期値。`SAI_MACSEC_PORT_ATTR_ENABLE_ENCRYPT` に使用 | `macsecorch.cpp:40, 1424` |
| `DEFAULT_SCI_IN_SECTAG` | `false` | SecTAG 内 SCI フィールド包含フラグの初期値。`SAI_MACSEC_PORT_ATTR_VLAN_TPID` 関連 | `macsecorch.cpp:41, 1425` |
| `DEFAULT_CIPHER_SUITE` | `SAI_MACSEC_CIPHER_SUITE_GCM_AES_128` | MACsec オブジェクト作成時のデフォルト暗号スイート。実際の値は `MACSEC_PROFILE` の `cipher_suite` フィールドで上書きされる | `macsecorch.cpp:42, 1426` |

### SA / SC 数制限

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `MAX_SA_NUMBER` | `3` | 1 SC あたりの最大 SA 番号 (0〜3)。`an > MAX_SA_NUMBER` でバリデーション | `macsecorch.h:24` |
| `m_max_sa_per_sc` SAI デフォルト | `4` | SAI が `SAI_MACSEC_ATTR_MAX_SECURE_ASSOCIATIONS_PER_SC` をサポートしない場合の fallback 値 | `macsecorch.cpp:1330-1331` |

### ACL 優先度制限

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `AVAILABLE_ACL_PRIORITIES_LIMITATION` | `32` | MACsec ポートに割り当て可能な ACL 優先度エントリの最大数 | `macsecorch.cpp:24` |

### Ethertype ハードコード値

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `EAPOL_ETHER_TYPE` | `0x888e` | EAPOL フレームの Ethertype。MKA ネゴシエーションパケット識別に使用 | `macsecorch.cpp:25` |
| `PAUSE_ETHER_TYPE` | `0x8808` | PAUSE フレームの Ethertype。PFC フレームのバイパス/暗号化制御で参照 | `macsecorch.cpp:26` |

### FlexCounter ポーリング間隔

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `MACSEC_STAT_XPN_POLLING_INTERVAL_MS` | `1000` ms (1 秒) | XPN (Extended Packet Number) カウンタのポーリング間隔。XPN ロールオーバー検出のため短めに設定 | `macsecorch.cpp:27, 646, 659` |
| `MACSEC_STAT_POLLING_INTERVAL_MS` | `10000` ms (10 秒) | 通常の MACsec 統計カウンタのポーリング間隔 | `macsecorch.cpp:28, 650, 654, 664, 669` |

### PFC モード文字列

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `PFC_MODE_BYPASS` | `"bypass"` | PFC フレームを暗号化せずにバイパスする | `macsecorch.cpp:29` |
| `PFC_MODE_ENCRYPT` | `"encrypt"` | PFC フレームを暗号化する | `macsecorch.cpp:30` |
| `PFC_MODE_STRICT_ENCRYPT` | `"strict_encrypt"` | 厳格暗号化モード | `macsecorch.cpp:31` |
| `PFC_MODE_DEFAULT` | `"bypass"` (= `PFC_MODE_BYPASS`) | PFC モード未指定時のデフォルト。APPL_DB `MACSEC_PORT_TABLE` の `pfc_mode` フィールドが空の場合に使用 | `macsecorch.cpp:32, 2714` |

---

## まとめ

- **wpa_supplicant 接続タイムアウト**: 合計最大 3000 ms (30 回 × 100 ms)
- **interface_remove リトライ**: 最大 3 回、各間隔 10 秒
- **SAI デフォルト**: 暗号化=有効、SCI=SecTAGなし、暗号スイート=GCM-AES-128
- **統計カウンタ**: XPN は 1 秒、通常カウンタは 10 秒ポーリング
- **PFC デフォルト**: バイパス (暗号化なし)
- discrepancy なし: すべてコードに記載の通り
