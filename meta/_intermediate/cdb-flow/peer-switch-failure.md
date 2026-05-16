# PEER_SWITCH 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/peer-switch.md` Phase D block.

## 調査対象ソース

- `sonic-swss/orchagent/muxorch.cpp` (全行スキャン、handlePeerSwitch / addOperation / create_tunnel)
- `sonic-swss/orchagent/request_parser.cpp` (parseIpAddress 例外)
- `sonic-swss/orchagent/request_parser.h` (getAttrIP)

スキャン範囲 (失敗・retry 分岐に関わる箇所):

- `MuxOrch::handlePeerSwitch()` L2336–2392 (SET / DEL 分岐)
- `MuxOrch::addOperation()` L2395–2415 (std::runtime_error キャッチ)
- `static create_tunnel()` L217–332 (overlay IF / tunnel object 作成)
- `Request::parseIpAddress()` (request_parser.cpp L263–274) — 不正 IP → `std::invalid_argument`

---

## 失敗パス一覧

### 1. 不正な `address_ipv4` → `std::invalid_argument` → addOperation がエントリをスキップ (return true)

`request_parser.cpp:263–274` (`Request::parseIpAddress`):

```cpp
IpAddress addr(str);
// IpAddress コンストラクタが不正フォーマットで std::invalid_argument を投げる
catch (std::invalid_argument& _)
{
    throw std::invalid_argument(std::string("Invalid ip address: ") + str);
}
```

`muxorch.cpp:2409–2413` (`MuxOrch::addOperation`):

```cpp
catch(std::runtime_error& _)
{
    SWSS_LOG_ERROR("Mux add operation error %s ", _.what());
    return true;
}
```

`request.getAttrIP("address_ipv4")` の内部で `parseIpAddress` が呼ばれ、不正フォーマット（例: `"999.999.999.999"`, `"not-an-ip"`, `""` 等）では `std::invalid_argument` が送出される。`addOperation` の `catch(std::runtime_error&)` は `std::invalid_argument` を補足しない（継承関係なし）ため、例外は orchagent のより外側のハンドラへ伝播する。結果として PEER_SWITCH エントリは **`mux_peer_switch_` に反映されない**。

**注**: `request_parser` が YANG 検証後に値を受け取るため、YANG `inet:ipv4-address` 型バリデーションが通過した不正値のみがここに到達する（実運用上は YANG が先にブロック）。

### 2. TUNNEL (MuxTunnel0) 未解決 → `return false` でリトライ待機

`muxorch.cpp:2348–2354` (`handlePeerSwitch`):

```cpp
IpAddresses dst_ips = decap_orch_->getDstIpAddresses(MUX_TUNNEL);
if (!dst_ips.getSize())
{
    SWSS_LOG_INFO("Mux tunnel not yet created for '%s' peer ip '%s'",
                   MUX_TUNNEL, peer_ip.to_string().c_str());
    return false;
}
```

SET 時に `decap_orch_` が `MuxTunnel0` (`MUX_TUNNEL` 定数) の宛先 IP アドレスを未登録の場合、`handlePeerSwitch` は `return false` でリトライキューに戻る。orchagent のイベントループが次回 PEER_SWITCH イベントを再処理するまで `mux_peer_switch_` は未設定 (`0.0.0.0`) のままとなり、MUX_CABLE エントリの生成もブロックされる。

ログ: `SWSS_LOG_INFO` (`orchagent.log` INFO レベル)。エラーログは出ない。

### 3. SAI overlay インタフェース作成失敗 → `std::runtime_error` → addOperation がエラーログを出力して return true

`muxorch.cpp:242–244` (`create_tunnel`):

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    throw std::runtime_error("Can't create overlay interface");
}
```

`muxorch.cpp:2409–2413` (`addOperation`):

```cpp
catch(std::runtime_error& _)
{
    SWSS_LOG_ERROR("Mux add operation error %s ", _.what());
    return true;
}
```

`sai_router_intfs_api->create_router_interface` が `SAI_STATUS_SUCCESS` 以外を返すと `std::runtime_error("Can't create overlay interface")` が投げられる。`addOperation` がキャッチして `SWSS_LOG_ERROR("Mux add operation error Can't create overlay interface")` を出力し `return true` (consume)。**エントリはリトライされない** — orchagent はこの PEER_SWITCH エントリを完了済みとして破棄し `mux_peer_switch_` は未設定のままとなる。

### 4. SAI tunnel object 作成失敗 → `std::runtime_error` → addOperation がエラーログを出力して return true

`muxorch.cpp:325–329` (`create_tunnel`):

```cpp
status = sai_tunnel_api->create_tunnel(&tunnel_id, gSwitchId, ...);
if (status != SAI_STATUS_SUCCESS)
{
    throw std::runtime_error("Can't create a tunnel object");
}
```

SAI ASIC ドライバが tunnel オブジェクト作成を拒否した場合（リソース不足等）、同様に `addOperation` の `catch` で吸収され `SWSS_LOG_ERROR("Mux add operation error Can't create a tunnel object")` が出力される。`mux_peer_switch_` は設定されない。

### 5. DEL コマンド → "Not Implemented" のみ、`mux_peer_switch_` はリセットされない

`muxorch.cpp:2387–2390` (`handlePeerSwitch`):

```cpp
SWSS_LOG_NOTICE("Mux peer ip '%s' delete (Not Implemented), peer name '%s'",
                 peer_ip.to_string().c_str(), peer_name.c_str());
// mux_peer_switch_ はリセットされない
```

DEL_COMMAND を受信しても `mux_peer_switch_` のクリアは一切行われない。orchagent は旧 peer IP を保持し続け、以降の MUX_CABLE 処理でも旧 IP が参照される。CONFIG_DB からエントリを削除しても orchagent の動作は変わらない — **orchagent 再起動が唯一の回復手段**。

---

## まとめ — retry / rollback の有無

| # | 失敗トリガー | retry | rollback | ログ |
|---|------------|------|---------|------|
| 1 | 不正 `address_ipv4` フォーマット | なし (YANG が先にブロック) | — | 例外伝播（実運用上は到達しない） |
| 2 | TUNNEL (MuxTunnel0) 未解決 | あり (return false でリトライ待機) | — | SWSS_LOG_INFO `Mux tunnel not yet created` |
| 3 | SAI overlay IF 作成失敗 | なし (consume) | なし | SWSS_LOG_ERROR `Mux add operation error Can't create overlay interface` |
| 4 | SAI tunnel オブジェクト作成失敗 | なし (consume) | なし | SWSS_LOG_ERROR `Mux add operation error Can't create a tunnel object` |
| 5 | DEL (Not Implemented) | — | なし (旧 IP 保持) | SWSS_LOG_NOTICE `delete (Not Implemented)` |

### 設計観察

- **TUNNEL 未解決だけが正常な retry パス**: `return false` でエントリをリトライキューに戻す唯一の失敗パス
- **SAI 失敗は consume**: `addOperation` の `catch(std::runtime_error)` が SAI 失敗を飲み込み retry しない
- **DEL 未実装が最大のリスク**: orchagent 再起動なしに peer IP を変更する手段がない
- **推奨書き込み順**: `TUNNEL (MuxTunnel0)` → `PEER_SWITCH` → `MUX_CABLE`
