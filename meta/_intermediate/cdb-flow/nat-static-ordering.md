# nat-static — Phase B 書込み順依存

調査対象: `sonic-swss/cfgmgr/natmgr.cpp`

## 依存 1: NAT_GLOBAL.admin_mode が enabled 必須

`addStaticNatEntry()` (`natmgr.cpp:1557`) と `addStaticSingleNatEntry()` (`natmgr.cpp:2003`) の先頭で `isNatEnabled()` を呼ぶ。
`isNatEnabled()` は `natAdminMode == ENABLED` のみ true を返す (`natmgr.cpp:150-157`)。

- `NAT_GLOBAL.admin_mode = disabled`（デフォルト）のままでは `addStaticNatEntry()` が即 return する。
- STATIC_NAT エントリはキャッシュ (`m_staticNatEntry`) に保持される。
- `doNatGlobalTask()` で `admin_mode → enabled` に変わると `addStaticNatEntries()` が全キャッシュを処理する。
- エントリは失われないが **APPL_DB への書込みが遅延する**。

## 依存 2: DNAT エントリはインタフェースの IP 設定が先行必須

`addStaticNatEntry()` (`natmgr.cpp:1564`):

```cpp
if ((m_staticNatEntry[key].nat_type == DNAT_NAT_TYPE) and (!getIpEnabledIntf(key, interface)))
{
    SWSS_LOG_INFO("L3 Interface is not yet enabled for %s, skipping NAT entry addition to APPL_DB", key.c_str());
    return;
}
```

`getIpEnabledIntf()` は `m_natIpInterfaceInfo` を検索し、`global_ip` がいずれかのインタフェースのサブネット内に入ることを確認する (`natmgr.cpp:236-254`)。

`m_natIpInterfaceInfo` は `doNatIpInterfaceTask()` (`natmgr.cpp:7377`) が `INTERFACE|<port>|<ip/prefix>` を受信したときに更新される。ただし `STATE_DB:STATE_INTERFACE_TABLE:<key>` の ready チェックをパスした後のみ (`natmgr.cpp:7593`)。

- SNAT エントリ (`nat_type = snat`) は `getIpEnabledIntf()` チェックをスキップ → インタフェース設定不要。
- DNAT エントリは `INTERFACE|<port>|<global_ip_prefix>` が書き込まれ、かつ `STATE_DB` で port が ready になるまで APPL_DB 反映が保留。
- インタフェースが ready になると `addStaticNatEntries()` がリアクティブに呼ばれキャッシュを再処理する (`natmgr.cpp:7640`)。

## 依存 3: STATIC_NAPT との IP 重複チェック（準共存制約）

`addStaticNatEntry()` (`natmgr.cpp:1571`) が `isMatchesWithStaticNapt()` で `m_staticNaptEntry` を走査。
`STATIC_NAT` と `STATIC_NAPT` で同一 `global_ip` + 同一 `local_ip` の組み合わせが存在すると APPL_DB 書込みをスキップする。

→ 書込み順というよりキャッシュに STATIC_NAPT エントリが存在するかどうかの問題。SET 順が先でも後でも最終的には一方がスキップされる。

## 安全な SET 順序

```
SET NAT_GLOBAL|Values          admin_mode=enabled          # NAT 有効化 (必須1)
SET INTERFACE|Ethernet0|<global_ip>/24                     # DNAT のみ: インタフェース IP 割当 (必須2)
(STATE_DB:STATE_INTERFACE_TABLE ready を待つ)
SET STATIC_NAT|<global_ip>     local_ip=... nat_type=dnat  # DNAT エントリ書込み
```

SNAT の場合はインタフェース IP 設定不要:

```
SET NAT_GLOBAL|Values          admin_mode=enabled
SET STATIC_NAT|<global_ip>     local_ip=... nat_type=snat
```

## 安全な DEL 順序

```
DEL STATIC_NAT|<global_ip>     # エントリ削除 (APPL_DB からも除去)
DEL NAT_GLOBAL|Values          # 必要に応じて NAT 無効化
```

インタフェース削除先行でも `removeStaticNatEntry()` はキャッシュから削除するのみ。

## 依存関係サマリ

| 依存関係 | 方向 | 緩和策 |
|----------|------|--------|
| `NAT_GLOBAL.admin_mode=enabled` → STATIC_NAT APPL_DB 書込み | 必須 | キャッシュ保持→ admin_mode 有効化で自動再処理 |
| `INTERFACE\|<port>\|<prefix>` + STATE_DB ready → DNAT APPL_DB 書込み | 必須 (DNAT のみ) | キャッシュ保持→インタフェース ready で自動再処理 |
| STATIC_NAPT との global_ip 重複排除 | 論理制約 | 重複時は後着がスキップ (APPL_DB に反映されない) |
| STATIC_NAT DEL → INTERFACE DEL | 推奨 | 強制ではないがキャッシュ整合のため推奨 |

> スキャン証跡: `addStaticNatEntry()` L1548-1590、`isNatEnabled()` L150-157、`getIpEnabledIntf()` L236-254、`doNatIpInterfaceTask()` L7377-7720、`addStaticSingleNatEntry()` L1992-2064 精読。
