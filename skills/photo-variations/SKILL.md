---
name: photo-variations
description: Analyze a supplied photograph and its intended use, choose one of eight photo-art workflows (seven bundled and one read from upstream), and generate a finished raster artwork using the host image tool. Use for 变奏、自动选照片风格、照片艺术再创作、旅行卡、厚涂油画、照片拼贴、小人涂鸦、纸上留影 or limited-ink editorial posters. Does not provide professional retouching, deblurring, or documentary restoration.
license: Mixed upstream licenses; see THIRD-PARTY-NOTICES.md.
---

# 变奏 · Photo Variations

用户上传照片并要求自动处理时，直接完成 **看图 → 选一种风格 → 读取该工作流 → 调用生图/编辑工具 → 看结果 → 写入不可见署名并验证 → 交付**。默认每张输入生成一张作品；不要把八种风格混在一张图里，也不要只给推荐名单就结束。用户点名风格、用途、文字或数量时，以用户选择为准。

这是一个可移植 Skill：八种风格共用一个入口，其中七个原工作流随包提供，入口保存在 `references/workflows/<id>/UPSTREAM.md`。极简抽象通过 `references/external/photo-abstract-editorial.md` 读取固定版本的上游原文，不复制其原文件。不要向不存在的 `$子技能` 发起虚构调用。相对路径以对应工作流目录为根解析；在线原文中的相对链接以固定版本的上游目录解析。

## 自动处理

1. 查看当前照片。文件只在磁盘上时先用宿主的图片查看工具；没有可用照片才请用户补图。识别主体数量、主要关系、构图走势、色块、复杂度、原图可读文字，以及用户强调的保留内容。从用户当前或已给出的语境记录 `photo_context`；看图判断风景是否参与人物照片的表达，满足时标记 `scenic_setting`。不要从文件名、人物外貌或衣服文字推测身份、地点或旅行语境。
2. 读取 [routing.md](references/routing.md)，把真实视觉观察交给 `scripts/route_photo.py`。该脚本依据观察排序，**不自行识别图片，也不调用生图服务**。支持文件或标准输入；输出 JSON 包含选中工作流、原因、必读路径和执行条件。没有 Python 时按同一表手动选择，不让运行脚本成为生图的前提。
3. 默认目的 `auto`；明确是旅行纪念卡、趣味互动、安静留影、拼贴手账、极简构成、印刷封面或微缩摆件时采用对应目的。“假期拍的照片”只表示 `photo_context: travel`，不等于用户指定了旅行卡。自动模式下，人物与重要风景共同构成旅行记忆时，提高水彩旅行卡的适配分，降低会弱化风景的小人互动分；点名风格或明确用途仍优先。风景、车辆和美食继续按各自构图选择。默认自动选择一个结果，不让用户先做八选一。多款同样合适时用固定排序选一个，并用一句话解释。
4. 对选中项完整读取入口和它指定的生成必读资料。极简抽象需要真实可用的联网文档读取能力，才能填入 `remote_workflow_reader_available: true`；按外部索引读取上游入口、中文提示词与许可。读取失败就报告缺失条件，不凭风格名称猜写原规范。只加载选中工作流；再读 [execution.md](references/execution.md) 的对应适配规则。保留各自构图、摄影保留规则、配色和质感，不编译成通用“高级海报”模板。
5. 有生图/编辑工具就实际调用，携带当前原图作为参考或编辑目标。没有该工具时说明缺失的能力并交付可执行提示词，不宣称图已生成；不要安装服务、索要聊天中的密钥或默默换收费接口。用户只要提示词时停止于提示词。
6. 查看生成图，按该工作流质量门检查主体身份/数量/动作、空间关系、文字、专属视觉特征和画幅。有明确关键失败时最多重试一次，只纠正失败项。还不合格就如实报告，保留失败记录，不能当作合格效果展示。
7. 对每张最终输出读取 [attribution.md](references/attribution.md)，使用真实选中 ID 和 [creator-registry.json](references/creator-registry.json)，执行 `scripts/credit_artwork.py write`、`verify`，写入画面不可见的 `创作者×变奏` 元数据并读回。必须在拼版、优化和 XXD 清理之后执行；不把署名画进像素，不猜作者、不清除原有来源记录、不覆盖用户原片。没有处理能力或验证失败时，如实报告署名步骤未完成。
8. 交付署名后验证过的图片、一句选风格的理由和保存位置。需要视频前后对比时同时提供原图路径、输出路径和同一区域对照建议；原图与成品分别保留，由剪辑工具制作对比，不把水彩/厚涂成品改为左右拼图。提示词、署名及验证结果应保存到执行记录；没有文件工具时在回复中提供。

## 必须保留的边界

- 不覆盖输入，不将用户照片、结果或个人信息打进分享包。仅向本次执行所需的图片服务提供照片，不额外上传或发布。
- 有人物时锁定人数、头盔/服装等辨识特征和主要动作；照片作为摄影区保留的工作流不重造人脸。文字碑牌、日期、坐标等事实不可编造；不确定就保留真实照片或去掉新增事实文案。
- 小人涂鸦只进入普通海报分支，不自动进入小怪兽、桌宠或运行环境安装。多个独立主体且没有指定目标时，自动模式选另一种可处理整幅图的风格；用户明确指定小人涂鸦时，才简短确认主角。容器和内容可以作为一个主体。
- 使用语境不明时，自动路由先从五项 MIT 工作流选择。拾景、极简抽象、XXD 在个人非商业用途或已有对应授权时可用；无对应授权的商业用途不得自动调用这些受限工作流。不得把整个混合许可包标成 MIT 或承诺八项均可商用。具体来源与原文见 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。
- XXD 保留完整中文创意原文及 runtime；其 `xxd-strip-ai-meta` 辅助流程内置在 `references/helpers/xxd-strip-ai-meta/`。执行还需宿主有 Python 3.10+ 和 ExifTool；检查到这些能力后才能在 available_workflows 填入该名称。源码存在不等于可以执行，也不代表已清理元数据。
- “修糊、修曝光、去游客”等纯修图请求不强行套艺术风格；说明这八款的能力边界，并按宿主已有编辑能力处理或交接。

## 常见调用

- “把这张照片处理成适合朋友圈分享的作品，自动选风格。”
- “做成旅行纪念卡，保留这三个人和头盔。”
- “我要商业视频的前后对比，自动选一款可用工作流。”
- “只给路由判断和提示词，先不要出图。”

安装、分享与条件说明见 [README.md](README.md)。包自检：`python scripts/validate_bundle.py`。
