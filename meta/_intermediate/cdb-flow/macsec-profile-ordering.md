# macsec-profile — Phase B 順序依存調査メモ

ソース: `sonic-swss/cfgmgr/macsecmgr.cpp`

## 抽出した順序依存

### 1. MACSEC_PROFILE が先に存在しなければならない

`enableMACsec()` (CFG_PORT_TABLE_NAME SET_COMMAND ハンドラ) は PORT の `macsec` フィールドを読み取った後、
`m_profiles.find(profile_name)` でプロファイルの存在を確認する (行 488–495)。

```cpp
auto itr = m_profiles.find(profile_name);
if (itr == m_profiles.end())
{
    SWSS_LOG_DEBUG("The MACsec profile '%s' for the port '%s' isn't ready", ...);
    return task_need_retry;
}
```

プロファイルが未ロードの場合は `task_need_retry` を返し、ハンドラキューに再投入される。
`MACSEC_PROFILE` エントリが存在しないまま `PORT.macsec` を SET すると、
タスクがリトライキューに留まり続け、MACsec は有効化されない。

### 2. PORT.macsec がプロファイル名を参照する（参照方向）

`PORT` テーブルの `macsec` フィールドがプロファイル名文字列を保持し、`MACSEC_PROFILE|<name>` を参照する。
逆参照はない。削除時は `removeProfile()` が `m_macsec_ports` を走査して使用中のポートを確認し、
使用中であれば `task_need_retry` を返す (行 452–466)。

### 3. wpa_supplicant の起動順序

プロファイルとポート両方が ready になった後、`startWPASupplicant()` を呼び出す (行 543)。
起動失敗時は `task_need_retry` または `task_failed`。
ポートが STATE_DB の `STATE_PORT_TABLE_NAME` で up 状態になっていることも前提 (`isPortStateOk()`, 行 500–504)。

```
MACSEC_PROFILE 設定
  ↓ loadProfile() → m_profiles に格納
PORT.macsec = <profile_name> 設定
  ↓ enableMACsec()
    → m_profiles 確認（未ロードなら task_need_retry）
    → isPortStateOk() 確認（ポート未 up なら task_need_retry）
    → startWPASupplicant()
    → configureMACsec()
```

## 結論

- `MACSEC_PROFILE|<name>` を先に設定してから `PORT.macsec = <name>` を設定する必要がある。
- ポートが物理的に up である必要がある（STATE_DB 確認）。
- 逆順（PORT 先）にした場合はタスクがリトライキューに入り、MACSEC_PROFILE ロード後に自動再試行される（最終的には成功するが遅延が生じる）。
