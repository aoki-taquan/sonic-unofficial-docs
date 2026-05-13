# TACPLUS_SERVER — 値依存挙動調査メモ

## ソース

- `sonic-system-tacacs.yang` (sonic-buildimage@9ea932ec)
- `sonic-host-services/scripts/hostcfgd` (TacacsPlusCfg)

## enum 値

### `auth_type` (auth_type_enumeration typedef)

- `pap`: Password Authentication Protocol — パスワードを平文で送信 (default)
- `chap`: Challenge Handshake Authentication Protocol — ハッシュ利用
- `mschap`: Microsoft CHAP — Windows 互換の CHAP 変形
- `login`: ログインシーケンスでの認証

### `vrf` (TACPLUS_SERVER)

- `mgmt`: 管理 VRF 経由で TACACS+ サーバにアクセス
- `default`: デフォルト VRF 経由

### `key_encrypt` (key_encrypt_type typedef)

- `false` (default): passkey を平文で保存
- `true`: passkey を暗号化して保存

## 値依存挙動

| フィールド | 値 | 挙動 |
|-----------|-----|-----|
| `auth_type` | `pap` | PAM pam_tacplus でパスワード平文送信。最も広くサポートされる |
| `auth_type` | `chap` | PAM pam_tacplus が CHAP でネゴシエーション |
| `auth_type` | `mschap` | PAM pam_tacplus が MS-CHAP でネゴシエーション |
| `auth_type` | `login` | PAM ASCII ログインシーケンス |
| `vrf` | `mgmt` | pam_tacplus が管理 VRF デバイス (`eth0` 相当) を bind |
| `vrf` | `default` | データプレーン VRF を使用 |
| `key_encrypt` | `true` | passkey は暗号化保存。`hostcfgd` が復号してテンプレートに展開 |
| `priority` | 大きい値 | `hostcfgd` がソートして PAM 設定に先に記載（高優先度） |
| `passkey` (per-server) | 設定あり | per-server の値が `TACPLUS|global` の `passkey` より優先 |
| `passkey` (per-server) | 未設定 | `TACPLUS|global.passkey` にフォールバック |
| `timeout` (per-server) | 設定あり | per-server timeout が global timeout より優先 |
