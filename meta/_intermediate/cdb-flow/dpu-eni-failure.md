# dpu-eni — Phase D failure-behavior 調査メモ

## 調査対象
- `sonic-swss/orchagent/dash/dashenifwdorch.cpp`
- `sonic-swss/orchagent/dash/dashenifwdorch.h`
- `sonic-swss/orchagent/dash/dashenifwdinfo.cpp`

## 主要失敗経路

### 1. SWSS_LOG_THROW (orchagent abort)
- `EniFwdCtxBase::getVip()` (dashenifwdorch.cpp:499-503): `VIP_TABLE` が空の場合。唯一の THROW 発生源。
- `EniInfo::update()` (dashenifwdinfo.cpp:339-341): `primary_vdpu` フィールドなしで `logic_error` を throw → abort。

### 2. rule_state_t::FAILED
- `EniAclRule::processUpdate()` (dashenifwdinfo.cpp:104-108): primary_id が DpuRegistry 未登録。
- `EniAclRule::processUpdate()` (dashenifwdinfo.cpp:93-97): TUNNEL_TERM ルール用のローカルエンドポイント不在。

### 3. rule_state_t::PENDING (自動回復あり)
- `LocalEniNH::resolve()` (dashenifwdinfo.cpp:28-31): Neighbor 未解決。NeighOrch Up 通知で再評価。
- `RemoteEniNH::resolve()` (dashenifwdinfo.cpp:45-57): VNET トンネル名 / VNI 未登録。

### 4. SWSS_LOG_ERROR (継続)
- `DpuRegistry::processDpuTable()` (dashenifwdorch.cpp:264): parse 例外。そのエントリをスキップ。
- `DpuRegistry::processVdpuTable()` (dashenifwdorch.cpp:338): 未登録 DPU ID。WARN でスキップ。
- `EniInfo::create()` (dashenifwdinfo.cpp:287): vdpu_ids/primary_vdpu 欠落。
- `DashEniFwdOrch::delOperation()` (dashenifwdorch.cpp:192): 存在しない ENI DEL。return true で容認。

## 注意点
- rule_state_t (FAILED/PENDING/INSTALLED/UNINSTALLED) は orchagent メモリ内のみ。STATE_DB / APPL_DB 非露出。
- ERROR_TABLE への書き込みはなし。
- populate() は lazyInit で 1 回限り。DPU テーブル修正後は orchagent 再起動が必要。
