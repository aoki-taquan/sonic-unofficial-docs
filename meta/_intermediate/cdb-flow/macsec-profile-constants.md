# MACSEC_PROFILE — ハードコード定数分析 (Phase E)

<!-- source: sonic-swss/cfgmgr/macsecmgr.cpp -->

## 調査対象

- ソース: `sonic-swss/cfgmgr/macsecmgr.cpp`
- 調査日: 2026-05-16

## 抽出定数一覧

### コンパイル時定数 (constexpr / #define)

```cpp
// CAK hex 文字列長制約
constexpr std::size_t AES_LEN_128_BYTE = 66;   // 128-bit CAK (GCM-AES-128 / GCM-AES-XPN-128)
constexpr std::size_t AES_LEN_256_BYTE = 130;  // 256-bit CAK (GCM-AES-256 / GCM-AES-XPN-256)

// リトライ制御
constexpr std::uint64_t RETRY_TIME     = 30;   // 上限 tick [ms]
constexpr std::uint64_t RETRY_INTERVAL = 100;  // ポーリング間隔 [ms]

// インターフェース削除リトライ
static constexpr int MAX_INTERFACE_REMOVE_RETRIES = 3;
```

### ランタイムデフォルト (loadProfile 内)

```cpp
// rekey_period フィールドが存在しない場合
if (!GetValue(ta, rekey_period))
    rekey_period = 0;

// priority フィールドが存在しない場合
if (!GetValue(ta, priority))
    priority = 255;

// policy フィールドが存在しない場合
if (!GetValue(ta, policy))
    policy = Policy::SECURITY;
```

## policy enum マッピング

| 文字列 (CONFIG_DB 値) | 内部 enum | wpa_cli 値 (`macsec_integ_only`) |
|----------------------|-----------|----------------------------------|
| `security` | `Policy::SECURITY` | `0` |
| `integrity_only` | `Policy::INTEGRITY_ONLY` | `1` |

比較: `boost::iequals` (大小文字非感受)

## CAK 長制約とエラー処理

`decodeKey()` 内で以下のチェックが行われる:

```
GCM-AES-128 / GCM-AES-XPN-128 → cipher_str.length() == 66 (AES_LEN_128_BYTE)
GCM-AES-256 / GCM-AES-XPN-256 → cipher_str.length() == 130 (AES_LEN_256_BYTE)
```

不一致時: `throw std::invalid_argument("Invalid length for cipher_string : " + cipher_str)` → caller で catch → `task_invalid_entry`

## priority range

- 型: `uint8_t` (0–255)
- デフォルト: **255**（キーサーバーになりにくい側）
- 小さいほど MKA キーサーバー選出で優先される（IEEE 802.1X-2020 準拠）

## rekey_period 動作

```cpp
if (profile.rekey_period)  // 0 は falsy → wpa_supplicant に設定しない
{
    wpa_cli_cmd(..., "mka_rekey_period", profile.rekey_period);
}
```

デフォルト `0` の場合、`mka_rekey_period` は `wpa_supplicant` に渡されず、MKA の自然な鍵更新サイクルのみ動作する。

## 関連ドキュメント

- 本番ページ: `docs/reference/config-db/macsec-profile.md`
- 参照ページ: `meta/_intermediate/cdb-flow/macsec-profile-cross-refs.md`
- 値依存挙動: `meta/_intermediate/cdb-flow/macsec-profile-values.md`
