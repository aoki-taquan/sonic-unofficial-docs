# PIM_GLOBALS / PIM_INTERFACE — Phase F: 設定変更の副作用調査結果

調査日: 2026-05-17
対象ファイル:
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-frr/pimd/pim_iface.c`
- `sonic-frr/pimd/pim_mroute.c`
- `sonic-frr/pimd/pim_bfd.c`
- `sonic-frr/pimd/pim_ssm.c`

---

## 1. PIM_INTERFACE.mode 変更時の副作用

### mode = 'sm' (sparse-mode 有効化)

`ip pim` コマンドが vtysh 経由で FRR pimd に送られると、pimd は以下を順次実行する:

1. **`pim_if_new()` 呼び出し** (`pim_iface.c` L112)
   - `pim_interface` 構造体を XCALLOC で確保
   - `igmp_socket_list`, `pim_neighbor_list` などのリストを初期化
   - `pim_sock_reset(ifp)` でソケット状態リセット
   - `pim_if_add_vif(ifp, false, false)` を呼び出してカーネルに VIF 追加

2. **カーネル VIF 登録** (`pim_iface.c` L182, `pim_mroute.c` L811)
   - `pim_mroute_add_vif()` が `setsockopt(fd, IPPROTO_IP, MRT_ADD_VIF, &vifctl, ...)` を発行
   - カーネルのマルチキャストルーティングテーブルにバーチャルインタフェース (VIF) を登録
   - VIF index は `pim_ifp->mroute_vif_index` に格納される（MAXVIFS = 32 上限）

3. **PIM Hello 即時送信** (`pim_iface.c` L286)
   - インタフェースに有効な IP アドレスが存在する場合、`pim_hello_restart_now(ifp)` を呼び出し
   - PIM Hello メッセージをリンク上にブロードキャスト (224.0.0.13 = ALL-PIM-ROUTERS)
   - Hello タイマー (default 30秒) をリスタート

4. **RP (Rendezvous Point) 評価** (`pim_iface.c` L769-770)
   - `pim_rp_setup(pim)` で RP の到達性を再評価
   - `pim_rp_check_on_if_add(pim_ifp)` でインタフェース追加に伴う RP 候補の再チェック

### mode = '' (OP_DELETE / sparse-mode 無効化)

1. **キャッシュフラッシュ** (`frrcfgd.py` L3791-3797)
   - `frrcfgd` が `data.items()` をイテレートし、全フィールドを `STAT_SUCC + OP_DELETE` に設定
   - 次回 sparse-mode 再有効化時にすべてのフィールドが再プログラムされるよう保証

2. **`no ip pim` コマンド発行**
   - pimd は `pim_if_delete()` を実行 (`pim_iface.c` L187)
   - `pim_if_del_vif()` → `pim_mroute_del_vif()` → `setsockopt(fd, IPPROTO_IP, MRT_DEL_VIF, ...)` でカーネルから VIF を削除
   - `pim_neighbor_delete_all()` で全 PIM 隣接情報を削除
   - `igmp_sock_delete_all()` で IGMP ソケットをクローズ

---

## 2. PIM_INTERFACE.bfd-enabled 変更時の副作用

### bfd-enabled = 'true' (BFD 有効化)

`ip pim bfd` コマンド発行後、pimd は以下を実行する:

1. **BFD 情報構造体初期化** (`pim_bfd.c`)
   - `pim_ifp->bfd_info` に BFD パラメータ (detect_mult, min_rx, min_tx) を設定

2. **既存 PIM 隣接への BFD セッション登録** (`pim_bfd.c` L140-158)
   - `pim_bfd_reg_dereg_all_nbr(ifp, ZEBRA_BFD_DEST_REGISTER)` を呼び出し
   - 現在の PIM 隣接ごとに `pim_bfd_reg_dereg_nbr()` → `bfd_peer_sendmsg()` でゼブラに BFD セッション登録要求を送信
   - BFD セッションはゼブラを介して `bfdd` プロセスで管理される

### bfd-enabled = 'false' (OP_DELETE)

- `pim_bfd_reg_dereg_all_nbr(ifp, ZEBRA_BFD_DEST_DEREGISTER)` で全 BFD セッションを解除
- `pim_ifp->bfd_info` の解放

---

## 3. PIM_GLOBALS.ssm-ranges 変更時の副作用

`ip pim ssm prefix-list <name>` コマンド発行後:

1. **SSM prefix-list 更新** (`pim_ssm.c` L55-66)
   - `pim_ssm_prefix_list_update()` が呼ばれ、`pim->ssm_info->plist_name` を更新
   - `pim_ssm_range_reevaluate()` を呼び出し

2. **既存 (S,G) エントリの再評価** (`pim_ssm.c` L33-50)
   - グループアドレスが SSM → ASM に変化したエントリには Register 状態変化が生じる
   - ASM グループが新たに SSM range 内に入った場合は (*,G) エントリの削除トリガー

---

## 4. PIM_GLOBALS.ecmp-enabled/ecmp-rebalance-enabled 変更時の副作用

`ip pim ecmp` / `ip pim ecmp rebalance` コマンド発行後:

- `pim->ecmp_enable` フラグが変更され、次の RPF lookup から ECMP 経路が考慮される
- ecmp-rebalance を有効化すると、既存の (S,G) エントリが ECMP 中に発生した場合にロードバランスが再計算される
- リバランス自体は設定変更直後ではなく、次回 RPF 評価（Join/Prune タイマー、トポロジ変化）時に発生

---

## 5. PIM_GLOBALS.join-prune-interval / keep-alive-timer 変更時の副作用

- `join-prune-interval` 変更: `router->t_periodic` が更新され、次の JP タイマー起動時から新しい間隔が適用。既に動作中のタイマーは次の expiry まで旧値で動作
- `keep-alive-timer` 変更: 新規作成された (S,G) エントリに適用。既存エントリのタイマーは変更されない（既存エントリは expiry まで旧 KAT で動作）

---

## 6. カーネル側の永続的影響

PIM を有効化したインタフェースは、カーネルに `MRT_INIT` (VRF ごとに 1 回) および `MRT_ADD_VIF` (インタフェースごとに 1 回) を発行する。`no ip pim` で `MRT_DEL_VIF` を発行するまで、カーネルはそのインタフェースをマルチキャスト転送候補として保持し続ける。

`MRT_INIT` は pimd プロセス起動時に mroute_socket に対して発行され、プロセス再起動（config reload）時に再初期化される。CONFIG_DB の変更は vtysh 経由での差分適用であり、pimd のプロセス再起動は不要。
