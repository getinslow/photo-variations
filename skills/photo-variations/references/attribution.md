# 不可见工作流署名

每张实际路由生成图在交付前写入 `创作者×变奏` 的图片元数据。署名表示选中工作流的原署名或已核实发布者来源，登记见 [creator-registry.json](creator-registry.json)，不猜测作者实名。

先完成生成、质量检查、拼版、优化和必要的元数据清理，再加署名。XXD 的清理助手会删除注释，必须在它执行并验证后加署名。之后不要再清空元数据；再次优化或重新编码后，给最终文件重新写署名并验证。

Python 3.10+ 命令，相对路径从 Skill 根目录运行：

```text
python scripts/credit_artwork.py write --input generated.png --output generated-credited.png --workflow watercolor-travel-card --registry references/creator-registry.json
python scripts/credit_artwork.py verify --input generated-credited.png --workflow watercolor-travel-card --registry references/creator-registry.json --against generated.png
python scripts/credit_artwork.py read --input generated-credited.png
```

`--workflow` 使用真实选中的英文 ID。输出必须是新文件，不能覆盖输入或已有输出。每张生成图逐一执行，不把一张的署名套到整个文件夹。交付引用署名后的文件，执行记录保存工作流、署名内容、路径和验证结果。

支持 PNG / JPEG / WebP，分别使用 iTXt / COM / XMP。脚本不解码重编码图片；验证压缩图像载荷不变、署名读回正确，并保留其他元数据。无法安全合并的 XMP 或格式损坏会明确失败。没有本地文件或元数据处理能力时，说明交付步骤未完成，不声称已加水印。

署名在画面中不可见，可用脚本或图片元数据工具读取。它不是加密、像素隐写或不可去除的版权保护；转存、重新编码、平台压缩可能删除它。保留上游许可与来源记录，不能用隐藏署名替代原许可证要求的公开署名；本署名步骤不清除或伪造 AI 来源信息。

XXD 没有核实具名作者，采用 `nevertoday（上游发布者）×变奏`；小人涂鸦采用原文集体署名 `heytea-style contributors×变奏`。
