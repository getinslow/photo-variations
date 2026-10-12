# 第三方工作流与使用条件

变奏（Photo Variations）的整合入口、路由代码和适配文档于 2026-10-11 新建。七款原入口与必要参考资料随包保留，原入口仅改名 `UPSTREAM.md`，内容未修改。极简抽象仅保留固定版本的来源索引，使用时由宿主读取原仓库。八个独立工作流的版权和许可证继续由各原作者持有；本文件不改变原许可范围，也不代表作者为整合包背书。

| 工作流 | 原仓库与作者 | 原许可证文件 |
| --- | --- | --- |
| impasto-miniature-landscape | [GZ-L/photo-to-poster-skills](https://github.com/GZ-L/photo-to-poster-skills/tree/main/skills/impasto-miniature-landscape) | [MIT](references/workflows/impasto-miniature-landscape/LICENSE) |
| watercolor-travel-card | [GZ-L/photo-to-poster-skills](https://github.com/GZ-L/photo-to-poster-skills/tree/main/skills/watercolor-travel-card) | [MIT](references/workflows/watercolor-travel-card/LICENSE) |
| photo-relic-editorial | [wnby/photo-relic-editorial](https://github.com/wnby/photo-relic-editorial) | [MIT](references/workflows/photo-relic-editorial/LICENSE) |
| heytea-doodle-poster | [Hchen1218/heytea-style](https://github.com/Hchen1218/heytea-style) | [MIT](references/workflows/heytea-doodle-poster/LICENSE)；[素材声明](references/workflows/heytea-doodle-poster/ASSET-NOTICE.md) |
| mono-color | [yanliudesign/mono-color-skill](https://github.com/yanliudesign/mono-color-skill) | [MIT](references/workflows/mono-color/LICENSE)；[素材限制](references/workflows/mono-color/ASSET-LICENSE.md) |
| scenes-gathered-zine-v1-3 | [Zeejay0/gathered-scenes-zine-skill](https://github.com/Zeejay0/gathered-scenes-zine-skill) | [个人非商业许可](references/workflows/scenes-gathered-zine-v1-3/LICENSE) |
| photo-abstract-editorial | [ZzzLc0405/photo-abstract-editorial](https://github.com/ZzzLc0405/photo-abstract-editorial) · @AM. | [个人研究与非商业条件](https://github.com/ZzzLc0405/photo-abstract-editorial/blob/49e55073d6d0330274d31f75d27f5dd6eb35fd6d/LICENSE.md)；[按需读取索引](references/external/photo-abstract-editorial.md)，原文件不内置 |
| xxd-panel-115 | [nevertoday/xxd-panel-115](https://github.com/nevertoday/xxd-panel-115) | [PolyForm Noncommercial 1.0.0](references/workflows/xxd-panel-115/LICENSE) |

## 分享范围

本包含八条路由、七款随包工作流和一款外部引用，免费提供给个人学习、研究和非商业使用。保留完整许可证、版权、来源及本次适配声明；不得统一换成 MIT、删除作者信息、转售整合包或声称全部可免费商用。若要放进收费服务、商业 Agent、付费课程/交付或商业工作流，请依各原作者的许可证取得对应授权。五项 MIT 路线的独立使用仍遵循它们自己的许可证及照片权利条件。getinslow 原创部分的 MIT 范围见 [LICENSE.md](LICENSE.md)。

Zeejay0 的许可明确涉及生成输出在变现内容中的使用，以及免费分享副本的条件；另外两项非商业许可措辞不同，使用时读各自原文。路由不会将三者概括成同一份许可。

## 本次适配与资源裁剪

- 一个公开入口，七个原工作流保留独立子树，极简抽象仅以固定版本链接引用，不把原提示词混合或重写。
- 总入口处理自动选款、一图一输出、宿主保存位置、回复形式和条件检查。小人互动默认为无新增文字并保留源照片原有字，与上游严格无字模式的差异已标明。
- 不包含 Heytea 的 private-assets 品牌研究图、示例图片或桌宠 runtime；普通海报可按文字规范执行。带字标题构造工具只有在用户提供有权使用的参考素材时才适用。
- 不包含 mono-color 的原创示例或第三方参考图片；六份设计系统目录及自制色板仍保留。
- 不包含任何用户照片、生成结果、来源视频、支付二维码或私密配置。详细来源时间、原入口哈希和所有保留文件哈希见 `bundle-manifest.json`。
- XXD 的辅助 [nevertoday/xxd-strip-ai-meta](https://github.com/nevertoday/xxd-strip-ai-meta/tree/15d75570227a4a03cb349e963302b49d69dd175d) 源码按固定提交内置，原 [MIT 许可](references/helpers/xxd-strip-ai-meta/LICENSE) 保留。ExifTool 可执行文件未包含，采用其独立许可。缺失的翻译索引 README 不是生成必要依赖。源码拉取不代表已经执行元数据清理。
