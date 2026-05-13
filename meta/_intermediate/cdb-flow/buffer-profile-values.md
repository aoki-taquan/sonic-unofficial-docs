# BUFFER_PROFILE 値依存挙動分析

## enum フィールド
1. `headroom_type`: `static` / `dynamic`
2. `packet_discard_action`: `drop` / `trim`

## 値依存挙動

### headroom_type
- `dynamic`: `buffermgrdyn` が `profile.dynamic_calculated = true` とセットし、ポート速度・ケーブル長・MTU から
  headroom を自動計算する (buffermgrdyn.cpp:2788)。ユーザが `size`/`xon`/`xoff` を明示する必要がない。
- `static` (既定): ユーザが `size`, `xon`, `xoff` を明示指定する。`buffermgrd` はそのまま APPL_DB に転送。
- static モード (`buffer_model=static`) では `headroom_type=dynamic` を設定しても `buffermgrdyn` が動いていないため無視される。

### packet_discard_action
- `trim`: `bufferhelper.cpp:23` で `isTrimmingEligible=true` がセットされ、ingress PG
  (`bufferorch.cpp:1382`) / ingress profile list (`bufferorch.cpp:1725`) / egress profile list (`bufferorch.cpp:1915`) への
  適用が **禁止**（タスク失敗）。egress shared buffer 用途のみ利用可能。
- `drop` (既定): `isTrimmingEligible=false`。ingress/egress 両方に制限なく適用できる。

## ソース
- `sonic-swss/orchagent/buffer/bufferhelper.cpp:23`
- `sonic-swss/cfgmgr/buffermgrdyn.cpp:2786-2790`
- `sonic-swss/orchagent/bufferorch.cpp:757, 1382, 1725, 1915`
