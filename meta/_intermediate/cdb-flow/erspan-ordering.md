# ERSPAN ordering phase research (Phase B)

## 調査対象
- `sonic-swss/orchagent/mirrororch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`

## 主な発見事項

### 1. PortsOrch allPortsReady() ガード
`MirrorOrch::doTask()` (mirrororch.cpp:1571) は冒頭で `gPortsOrch->allPortsReady()` を確認し、
false の間は即 return。全ポート初期化完了まで MIRROR_SESSION 処理は行われない。

### 2. RouteOrch 非同期依存 (ERSPAN 固有)
`createEntry()` は `m_routeOrch->attach(this, entry.dstIp)` (mirrororch.cpp:517) を呼び、
RouteOrch の observer に登録される。nexthop 解決 callback → updateNextHop() → activateSession() の
非同期チェーン。dst_ip ルートが解決されるまで SAI create_mirror_session は実行されない。

### 3. NeighOrch 依存
`getNeighborInfo()` (mirrororch.cpp:656) で NeighOrch に neighbor MAC を問い合わせる。
未解決の場合 activateSession() がスキップされる。

### 4. orchdaemon でのスケジューリング
orchdaemon.cpp:1127-1142 に明示コメント:
「MirrorOrch depends on everything else being settled before it can run,
and mirror ACL rules depend on MirrorOrch, so run these two at the end」

起動時リストアループで MirrorOrch は 3 ループの最後に doTask() し、
その後 AclOrch が doTask() する。ACL mirror アクションはこの順序に依存。

### 5. PolicerOrch 任意依存
MIRROR_SESSION に policer フィールドがある場合のみ gPolicerOrch->getPolicer() を呼ぶ。
失敗時は task_need_retry でキュー再試行。

## observer 登録
mirrororch.cpp:93-95:
- m_portsOrch->attach(this) — PortsOrch observer
- m_neighOrch->attach(this) — NeighOrch observer
- m_fdbOrch->attach(this)  — FdbOrch observer
