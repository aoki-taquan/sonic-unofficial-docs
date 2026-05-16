# TUNNEL テーブル — Phase E: ハードコード定数調査

## 調査対象ソース

- `sonic-swss/cfgmgr/tunnelmgr.cpp` (tunnelmgrd)
- `sonic-swss/orchagent/tunneldecaporch.cpp` (tunneldecaporch)
- `sonic-swss/orchagent/tunneldecaporch.h`

---

## ハードコード定数一覧

| 定数名 | 値 | 定義場所 | 用途 |
|--------|----|---------|------|
| `IPINIP` | `"IPINIP"` | `tunnelmgr.cpp` L17 | `tunnel_type` 比較用マクロ。`tunnel_type != IPINIP` でエラー判定 |
| `TUNIF` | `"tun0"` | `tunnelmgr.cpp` L18 | Linux kernel IPinIP トンネル IF 名。固定・変更不可。`ip tunnel add tun0 ...` で作成 |
| `LOOPBACK_SRC` | `"Loopback3"` | `tunnelmgr.cpp` L19 | カーネルトンネルのローカル IP を取得する Loopback IF 名。ハードコードにより、`LOOPBACK_INTERFACE|Loopback3` が存在しない環境ではトンネルが動作しない |
| `OVERLAY_RIF_DEFAULT_MTU` | `9100` | `tunneldecaporch.cpp` L14 | Overlay loopback ルータインターフェースの MTU。`SAI_ROUTER_INTERFACE_ATTR_MTU` として SAI に渡す |
| `MUX_TUNNEL` | `"MuxTunnel0"` | `tunneldecaporch.h` L21 | MuxOrch が参照する Dual-ToR 用トンネル名。TUNNEL テーブルのキーは通常この値 |
| `SubnetDecapConfig.tunnel` | `"IPINIP_SUBNET"` | `tunneldecaporch.h` L101 | サブネット decap 用 IPv4 トンネル名。`TUNNEL` テーブルへ書かれる値ではなく、内部識別子 |
| `SubnetDecapConfig.tunnel_v6` | `"IPINIP_SUBNET_V6"` | `tunneldecaporch.h` L102 | サブネット decap 用 IPv6 トンネル名。同上 |

---

## 影響範囲と運用上の注意

### `TUNIF = "tun0"` の影響

- `ip tunnel add tun0 mode ipip local <dst_ip> remote <peer_ip>` でカーネルトンネルを作成
- `ip tunnel del tun0` で削除
- 複数のトンネルを同一ホストで動かすことはできない（`tun0` 固定のため）
- CONFIG_DB の TUNNEL テーブルエントリ名（例: `MuxTunnel0`）とは無関係に `tun0` が使われる

### `LOOPBACK_SRC = "Loopback3"` の影響

- Dual-ToR 環境では `LOOPBACK_INTERFACE|Loopback3|<ip/prefix>` が存在しないとカーネルトンネルの local IP を設定できない
- `LOOPBACK_INTERFACE|Loopback3` の SET が `TUNNEL` SET より後に来ると、トンネル IF へのアドレス付与が遅延する
  - ただし後から届いた場合でも `m_tunnelCache` にエントリが残っていれば付与される（`tunnelmgr.cpp` L339 のキャッシュ確認ロジック）

### `OVERLAY_RIF_DEFAULT_MTU = 9100` の影響

- tunneldecaporch が Overlay RIF を作成する際に `SAI_ROUTER_INTERFACE_ATTR_MTU = 9100` を設定
- Jumbo frame 対応のデフォルト値（通常の 1500 より大きい）
- CONFIG_DB の設定値で上書きする仕組みはなく、変更には tunneldecaporch のコード変更が必要

### `MUX_TUNNEL = "MuxTunnel0"` の影響

- `tunneldecaporch.h` L21 で定義され、MuxOrch が `getDstIpAddresses()` 等を呼ぶ際のトンネル名として使用
- TUNNEL テーブルのキーが `MuxTunnel0` でない場合、MuxOrch は対象トンネルを見つけられずエラーとなる
- YANG パターン `"MuxTunnel[0-9]+"` で複数エントリを許容しているが、MuxOrch は `MuxTunnel0` を固定参照

---

## CONFIG_DB 非連動の整理

以下の値は CONFIG_DB の TUNNEL テーブルから読み込まれず、コードに直書きされている:

```
tun0          ← Linuxカーネルトンネルのデバイス名
Loopback3     ← トンネルローカルIPのソース
9100          ← Overlay RIF の MTU
MuxTunnel0    ← MuxOrch が固定参照するトンネル名
IPINIP_SUBNET / IPINIP_SUBNET_V6  ← サブネット decap トンネル識別子
```

これらは `config_db.json` での設定値変更では効果がなく、SONiC コードのリコンパイルが必要。

---

## 証跡

- `tunnelmgr.cpp` L17-19: `#define IPINIP`, `TUNIF`, `LOOPBACK_SRC`
- `tunneldecaporch.cpp` L14: `#define OVERLAY_RIF_DEFAULT_MTU 9100`
- `tunneldecaporch.cpp` L749-750: `overlay_intf_attr.value.u32 = OVERLAY_RIF_DEFAULT_MTU`
- `tunneldecaporch.h` L21: `#define MUX_TUNNEL "MuxTunnel0"`
- `tunneldecaporch.h` L97-102: `SubnetDecapConfig subnetDecapConfig = {"IPINIP_SUBNET", "IPINIP_SUBNET_V6"}`
