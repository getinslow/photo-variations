# 如何从照片选一款

照片没有唯一正确风格。优先级是：用户点名 → 用户用途 → 必须保留的内容 → 构图适配度。不要为了凑齐八款而给不合适的照片硬套一种。

| ID | 用途与强信号 | 自动模式避开的情况 |
| --- | --- | --- |
| watercolor-travel-card | 旅行纪念；山水、村落、建筑有可读轮廓；人物与风景共同构成记忆 | 用户要求摄影区不变、重要碑文须逐字保真 |
| impasto-miniature-landscape | 微缩艺术；层叠地形、鲜明色块、可压缩的场景关系 | 需要精确地图/史料或脸部细节保真 |
| photo-relic-editorial | 安静留影；拱门、屋顶、城市层次、水平线；照片细节必须保留 | 无法提炼出可识别的主体关系 |
| heytea-doodle-poster | 趣味互动；一个真实主体、容器+内容或单人动作 | 没有明确主角，多个独立人物/物件需自行挑一个 |
| mono-color | 印刷封面；车辆队列、重复节奏、强轴线、颜色可分成两版 | 必须原色摄影或纪实像素不变 |
| scenes-gathered-zine-v1-3 | 拼贴手账；旅伴、绿植、风景与真实摄影片段、撕纸 | 使用语境未知或商业且未获授权 |
| photo-abstract-editorial | 极简构成；公路/地貌方向、色块/空间关系清楚 | 使用语境未知/商业无授权，或无法联网读取上游原文 |
| xxd-panel-115 | 粉彩蜡笔日记；生活关系、小尺度记忆章印 | 使用语境未知/商业无授权，或缺 `xxd-strip-ai-meta` |

`route_photo.py` 只接受结构化视觉观察；这避免把“照片里出现一个词”当作风格判断，也不会从文件名推测内容。通常记录 subject_type、features、single_subject、purpose 和 photo_context。默认无明确生图工具状态时设 `image_tool_available: false`，先检查宿主实际能力再填 true。

```json
{
  "source_path": "/absolute/photo.jpg",
  "subject_type": "landscape",
  "features": ["layered_terrain", "strong_color_blocks", "clear_silhouette"],
  "single_subject": true,
  "purpose": "auto",
  "photo_context": "travel",
  "use_context": "unknown",
  "image_tool_available": true,
  "remote_workflow_reader_available": false,
  "available_workflows": [],
  "preserve_photo_region": false,
  "preserve_source_pixels": false,
  "pixel_preserving_compositor": false
}
```

允许的 subject_type：`landscape`、`architecture`、`person`、`group`、`food`、`object`、`urban_scene`。

允许的 features：`layered_terrain`、`architectural_layers`、`strong_color_blocks`、`clear_silhouette`、`visible_action`、`strong_axis`、`repeated_shapes`、`quiet_regions`、`dense_detail`、`legible_text`、`documentary_text`、`warm_memory`、`organic_shapes`、`horizon`、`scenic_setting`。帽子、包装、招牌上有字可以标记 `legible_text`；碑文、文献或用户要求准确保留的信息再加 `documentary_text`。不要把衣服上有字误当作整张照片的主要用途。

`photo_context` 来自用户当前或前文说明：`travel` 表示假期、出游等旅行照片；`everyday` 表示日常记录；`product` 表示商品展示；缺少依据用 `unknown`（默认）。它不等于许可语境 `use_context`，也不自动指定艺术风格。

`scenic_setting` 来自看图：海景、山林、街景等可辨识环境与人物共同构成画面记忆；单纯背景留白、棚拍背景或普通墙面不算。没有水平线也可以成立，不从文件名或画面文字猜测旅行。

自动模式下，当 `photo_context: travel`、主体为 `person` 或 `group` 且有 `scenic_setting`，加入一个软偏好：水彩旅行卡 +8，小人互动 -3，其余款不变。这样会考虑保留人物与环境的关系。仅有旅行语境或仅有风景标签都不触发；明确用途和指定风格不受这项偏好影响。主体数量、摄影区保留、许可和工具能力仍先过滤。

用途：`auto`、`travel_card`、`miniature_art`、`quiet_memory`、`playful_poster`、`print_poster`、`zine_collage`、`minimal_art`、`crayon_diary`。

可选：`style` 可传精确 ID、显示名称或配置列出的中文别名；`selected_subject` 仅在用户已经明确选主角时填；`request_kind` 为 `style`（默认）或 `retouch`。`use_context` 为 `unknown`、`personal_noncommercial` 或 `commercial`；`commercial_permissions` 列出用户确有相应授权的受限 ID，不推测已获授权。

`remote_workflow_reader_available` 默认 false。只有宿主真实具备联网文档读取能力时才填 true；这让外部引用的极简抽象可以参与路由，不代表内容已成功读取。选中后必须读取固定上游版本的完整入口、提示词和许可；工具读取失败仍需报告，不能凭名生成或声称完成。路由脚本不自行联网。

### 结果状态

- `ready`：路由条件与图片工具具备，继续调用工具；不是“已经生成”。
- `prompt_only`：没有图片工具，仅能交付提示词；不能冒充成品。
- `needs_subject`：用户点名小人海报但独立主体不唯一，需要选主角。
- `license_required`：用户点名受限款但用途/授权不满足。
- `dependency_missing`：点名 XXD 但额外工作流缺失，或点名极简抽象但无法联网读取上游。
- `compositor_required`：要求原图像素完全保留，却没有可保持像素的拼版工具。
- `incompatible_request` / `unsupported_retouch`：显式风格与保留需求冲突，或纯修图超出八款能力。

自动模式只排除不满足条件的路线，再选余下最高分；不通过不停提问完成自动化。明确请求不能静默换款。

用途分数作用于所有可选路线，受限款被排除后仍保留原用途。例如“商业用极简图”不能因为极简抽象入口受限就跳到满幅厚涂；可选择有限墨色印刷或纸上留影，并说明为何改用这一项。若用户明确点名入口而非只说用途，则保留条件阻断，不自动换款。
