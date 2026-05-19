# erspan — Phase E (constants) 調査証跡

## 対象ファイル
- `sonic-swss/orchagent/mirrororch.cpp`
- `sonic-swss/orchagent/mirrororch.h`
- `sonic-swss/orchagent/orch.h`

## スキャン箇所
- `mirrororch.cpp` L14-45: `#define` 定数群（フィールド名文字列・STATUS 値・数値定数）
- `mirrororch.cpp` L57-77: `MirrorEntry` コンストラクタ（dscp=8, ttl=255, queue=0, greType 分岐）
- `mirrororch.cpp` L100-109: `MirrorOrch` コンストラクタでの `m_maxNumTC` SAI 取得 + フォールバック
- `mirrororch.cpp` L395: `getenv("platform")` で platform 文字列取得
- `mirrororch.cpp` L997-1011: VLAN PRI/CFI = 0, IP HDR VER 4/6, ERSPAN カプセル化タイプ
- `mirrororch.h` L36, L99-100: `greType` / `m_maxNumTC` フィールド宣言
- `orch.h` L42: `MLNX_PLATFORM_SUBSTRING = "mellanox"`

## 発見した定数

### フィールド初期値 (MirrorEntry コンストラクタ)
- dscp = 8 (CS1相当)
- ttl = 255
- queue = 0
- greType = 0x8949 (Mellanox) / 0x88be (その他)

### SAI 属性ハードコード値
- VLAN PRI = 0, VLAN CFI = 0 (VLAN ポートの場合のみ)
- IP HDR VER = 4 (IPv4) / 6 (IPv6) — dst_ip から自動判定
- DSCP_SHIFT = 2 (TOS = dscp << 2)
- DSCP_MIN = 0, DSCP_MAX = 63 (バリデーション範囲)
- ERSPAN カプセル化タイプ = SAI_ERSPAN_ENCAPSULATION_TYPE_MIRROR_L3_GRE_TUNNEL (固定)

### TC 上限フォールバック
- MIRROR_SESSION_DEFAULT_NUM_TC = 255 (SAI 取得失敗時の m_maxNumTC)

### STATE_DB 値定数
- MIRROR_SESSION_STATUS_ACTIVE = "active"
- MIRROR_SESSION_STATUS_INACTIVE = "inactive"

### プラットフォーム判定
- MLNX_PLATFORM_SUBSTRING = "mellanox" (完全一致比較)
