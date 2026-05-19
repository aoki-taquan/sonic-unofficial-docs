# PORTCHANNEL_INTERFACE — Phase H Platform Evidence

## grep結果（platform分岐ゼロ）

```
$ grep -n "platform\|getenv\|BRCM\|MLNX\|mellanox\|broadcom\|cisco\|barefoot\|marvell" \
    sonic-swss/cfgmgr/intfmgr.cpp
(0 hits)

$ grep -n "platform\|getenv\|BRCM\|MLNX\|mellanox\|broadcom\|cisco\|barefoot\|marvell" \
    sonic-swss/orchagent/intfsorch.cpp
(0 hits)
```

## カーネル依存: MPLS

`intfmgr.cpp:169-190` — `sysctl net.mpls.conf.<intf>.input` はカーネルMPLSモジュールが必須。
`mpls=enable` を明示設定した場合のみエラーが問題になる（空文字の場合はエラー無視）。

## カーネル依存: accept_untracked_na

`intfmgr.cpp:601-611` — `test -f /proc/sys/net/ipv6/conf/<intf>/accept_untracked_na` でファイル存在チェック後に書き込む。
カーネル 5.11未満ではファイルが存在しないためスキップ（エラーなし）。

## SAI RIF生成（全プラットフォーム共通）

`intfsorch.cpp:1210-1243` — `Port::LAG` は `SAI_ROUTER_INTERFACE_TYPE_PORT` + `m_lag_id` を使用。
`intfsorch.cpp:1146-1164` — `getSaiLoopbackAction()` は "drop"/"forward" の固定マップ。プラットフォーム分岐なし。

## Sources

- sonic-swss @ 4305596156d70e9797e8a881b3d19b46de0bce0d
  - cfgmgr/intfmgr.cpp
  - orchagent/intfsorch.cpp
