---
title: NPU MDIO アクセスと gbsyncd 単一 docker 化
area: platform
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/gearbox/gearbox_mdio-HLD.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  cli: []
  yang: []
---

!!! warning "裏取りステータス: HLD-only"
    HLD は v0.7 (2022-09)。`MdioIpcServer` / `VendorPai` クラス、`gearbox_config.json` の `phys[].lib_name` / `phy_access_lib_name` / `mdio_cl22_only`、`syncd -i/--paiInstance` の現行 master 取り込みは未裏取り。Broadcom platform でのみ検証されており他 vendor は未確認との注記あり。

# NPU MDIO アクセスと gbsyncd 単一 docker 化

## 概要

外部 PHY (gearbox) を制御するために gbsyncd は **PAI library** を使う。PHY が接続される MDIO バスは platform により異なり、(a) FPGA/CPLD ベースで Linux kernel driver + sysfs 経由のもの と (b) **switch NPU の MDIO bus** で SAI 経由でアクセスするもの の 2 系統がある[^1]。後者では syncd と gbsyncd の **プロセス間通信（IPC）** が必要になる。本 HLD は (i) NPU MDIO 経由のアクセスを Unix socket IPC で実現し、(ii) PAI library と MDIO access library を **runtime ロード** することで **単一 gbsyncd docker** で全 platform を扱えるようにする設計。

## 動作仕様

### コンポーネント関係

```mermaid
flowchart LR
  subgraph syncd_docker[syncd docker]
    SY[syncd<br/>VendorSai]
    MS[MdioIpcServer<br/>Unix socket /tmp/...]
    SY --> NPU[NPU SAI]
    SY --- MS
  end
  subgraph gbsyncd_docker[gbsyncd docker (単一)]
    GB[syncd instance<br/>--paiInstance N]
    VP[VendorPai class<br/>VendorSai 継承]
    GB --> VP
    VP -. dlopen .-> PAI[PAI library<br/>vendor 別]
    VP -. dlopen .-> MAL[MDIO access lib]
    MAL -.->|sysfs or<br/>IPC client| EXT
  end
  EXT[(External PHY)]
  MAL -- Unix socket --> MS
  MS --> NPU
```

### IPC

- IPC は Unix domain socket、syncd 側に **MdioIpcServer** クラスが新設され、独立スレッドで listen/accept/read/reply を行う[^1]
- gbsyncd 側は **MDIO IPC client** を**動的ライブラリ**として実装。kernel sysfs ベース platform では同じ抽象の sysfs MDIO アクセス lib を選べる
- IPC 速度は **PHY firmware download が現実的時間で完了する** ことが要件
- デバッグでは IPC 部分を `socat` 等で simulate 可能

### `VendorPai` クラス

- `VendorSai` を継承する新クラス[^1]
- コンストラクタで **PAI library path** と **MDIO access library path** を引数に取り、両者を **runtime に dlopen** する
- これにより gbsyncd docker 1 つで vendor 別 PAI / MDIO 実装に切替可能になる

```cpp
int syncd_main(int argc, char **argv) {
    ...
    if (commandLineOptions->m_paiInstance >= 0) {
        auto vendorSai = std::make_shared<VendorPai>(
            commandLineOptions->m_paiInstance,
            commandLineOptions->m_contextConfig);
        ...
    } else {
        auto vendorSai = std::make_shared<VendorSai>();
        ...
    }
}
```

### コマンドライン

gbsyncd 内で動く syncd instance は `--paiInstance` (`-i <N>`) を受ける[^1]。`-x <gearbox_config.json>` で gearbox 設定ファイルパス、`-i N` が config 内 `phys[N]` を選ぶインデックスになる。

### `gearbox_config.json` の拡張

`phys` 配列の各要素に次のキーが追加される[^1]:

| key | 内容 |
|-----|------|
| `phy_id` | 既存。PHY 番号 |
| `lib_name` | PAI library のファイル名（dlopen 対象）|
| `phy_access_lib_name` | MDIO access library のファイル名（IPC client / sysfs lib）|
| `mdio_cl22_only` | この PHY が IEEE 802.3 Clause 22 のみ使う場合に true |

### MDIO Clause 22 / 45

| | アドレス空間 | port × reg |
|---|--------------|------------|
| Clause 22 | 32 reg × 32 port × 32 addr | 古い PHY 向け |
| Clause 45 | 65,536 reg × 32 dev × 32 port | 10G+ で標準 |

SAI switch api に **clause 22 用 MDIO read/write 関数**が追加され、`SaiInterface` に clause 45/22 の virtual 関数、`VendorSai` がそれを override する[^1]。

### Warm boot

- IPC socket の生成 / 接続手順は coldboot と同一[^1]
- platform 側ソフトは warm boot 中に外部 PHY を **reset しない**ことが必須

<!-- evidence:
source: sonic-net/SONiC/doc/gearbox/gearbox_mdio-HLD.md#L82-L94 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  Our design choice is to use the Unix socket as the IPC mechanism. Our design has the MDIO IPC server
  in the syncd daemon with its own thread. A new syncd class MdioIpcServer is added to start a new thread,
  to create an unix socket, to listen on the socket, to accept connection and to read/reply IPC messages.
reasoning: Unix socket IPC + MdioIpcServer 採用の根拠。
-->

## 制限事項

- HLD 検証は Broadcom NPU でのみ。他 vendor は未確認[^1]
- `--enableBulk` のような他フラグとの兼ね合いはスコープ外
- 外部 PHY firmware download の時間制約が IPC 設計の制約に直結

## 干渉する機能

- **Gearbox Manager (`gearbox_mgr_design.md`)**: 親 framework
- **syncd**（NPU 用）と **gbsyncd**（PHY 用）の責務分離
- **`gearbox_config.json`**: PHY topology 記述
- **`platform.json` / `port_config.ini`**: PHY を介する port の表現
- **`xcvrd` / `media_settings`**: PHY の前段に位置する optic 制御

## 引用元

[^1]: `sonic-net/SONiC` `doc/gearbox/gearbox_mdio-HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- syncd の MdioIpcServer 実装と Unix socket path 規約の sonic-sairedis 取り込み確認
- VendorPai クラス定義と paiInstance / contextConfig 引数の sonic-sairedis 取り込み確認
- gearbox_config.json の lib_name / phy_access_lib_name / mdio_cl22_only キー sonic-buildimage 反映確認
- SAI switch api の clause 22 read/write 拡張の opencomputeproject/SAI 取り込み確認
- 単一 gbsyncd docker での vendor 別 PAI/MDIO lib 同梱方針の現行 build 構成確認
-->
