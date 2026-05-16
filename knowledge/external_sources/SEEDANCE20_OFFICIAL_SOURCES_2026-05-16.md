---
doc_id: SEEDANCE20-OFFICIAL-SOURCES-2026-05-16
title: Seedance 2.0 全能参考官方资料摘要
doc_type: research_report
status: source_digest
runtime_retrieval: false
created_at: 2026-05-16
model_target: seedance2.0_omni_reference
sources:
- title: "ByteDance Seedance 2.0 product page"
  url: "https://seed.bytedance.com/en/seedance2_0"
- title: "ByteDance Seedance 2.0 Official Launch"
  url: "https://seed.bytedance.com/en/blog/seedance-2-0-official-launch"
- title: "Volcengine developer article: Seedance 2.0 on Ark experience center"
  url: "https://developer.volcengine.com/articles/7606009619928449070"
- title: "Seedance 2.0 model card paper"
  url: "https://arxiv.org/abs/2604.14148"
---

# Seedance 2.0 全能参考官方资料摘要

本文件是非运行时资料摘要。运行时规则以 `rules/shared/SEEDANCE20-OMNI-CAPABILITY-MATRIX-001.md` 和 `rules/shot_director/SEEDANCE20-COVERAGE-WHITELIST-001.md` 为准。

## 已确认能力

- Seedance 2.0 使用统一多模态音视频联合生成架构，支持文字、图片、音频、视频四类输入。
- 全能参考可以混合输入自然语言指令、最多 9 张图片、3 段视频、3 段音频。
- 官方说明参考素材可用于构图、运动、运镜、视觉效果、音频等元素。
- 官方文章展示了用图片作为分镜/角色/场景/道具参考，并生成 15 秒短片的用法。
- 官方文章展示了参考视频延长、定向编辑、角色/动作/剧情修改能力。
- 模型卡论文说明直接生成时长范围为 4-15 秒，开放平台参考输入上限同样为 3 段视频、9 张图片、3 段音频；论文中列出的原生输出分辨率为 480p 与 720p。
- 官方发布文章说明模型支持 15 秒高质量多镜头音视频输出，并增强双声道音频能力。

## 官方明确提醒的未完善点

- 细节稳定性、超写实质感、动态活力仍需持续优化。
- 多主体一致性、文字渲染准确性、复杂编辑效果仍有优化空间。
- 音频可能偶发失真。
- 使用真人人像作为主体参考时需要本人验证或合法授权。

## 本项目采用的保守生产解释

- 官方示例能说明模型上限，不等于短剧工业生产的默认安全边界。
- 短剧精品生产应优先使用 4-8 秒、1-2 名主要角色、一个可见动作、一个情绪落点的生成单元。
- 15 秒、多镜头、多人、复杂动作、音画同步可以作为能力储备，但默认进入“需参考素材或测试通过”的候选区。
- 全能参考模式的核心价值不是让 prompt 更长，而是给每个参考资产明确分工：角色身份、场景空间、道具、运动节奏、镜头语言、音频节奏不能混在同一句里。

## 规则生成用途

这些事实用于建立：

- AI 视频模型能力矩阵。
- Seedance 2.0 全能参考输入绑定规则。
- 短剧 coverage 模板白名单。
- 94 集短剧样片学习的入库门槛：只有“短剧常见 + Seedance 可控 + 质检可判定”的模板才能进入生产库。
