---
rule_id: SCENE-REF-MISSING-FALLBACK-001
title: 参考图缺失时的降级协议
doc_type: rule_card
rule_type: scene_analysis
agent_scope:
  - scene_analyst
  - prompt_compiler
  - quality_inspector
priority: hard
status: active
runtime_retrieval: true
source_files:
  - knowledge/11_场景分析输入卡与导演意图提取.md
  - knowledge/06_连续性与安全规则.md
  - knowledge/rules/prompt_compiler/REFERENCE-ROLE-STRICT-001.md
conflicts_with: []
supersedes: []
applies_to:
  - 无参考图
  - 身份描述降级
  - 风格锚点降级
  - 首帧锁定
---

# 参考图缺失时的降级协议

## 规则

当某个 `subject_id` 或 `scene_id` 在参考资产层没有匹配的参考图时，`scene_analyst` 必须触发降级协议，不得直接让下游自由生成。降级输出必须包含：

1. `no_reference_image: true` 标志。
2. `identity_description`：对该主体的文字身份锚点，至少覆盖 **性别 / 年龄段 / 发型 / 体型 / 关键服装 / 关键特征** 6 项。
3. `first_frame_lock`：首次出镜镜头的强制首帧文本描述，至少 3 个可视化锚点（例如"白衬衫领口微敞，左手扶门框，侧身面向镜头 3/4"）。
4. `allowed_style`：允许的风格词范围（限定到项目风格白名单内的 1-2 项，禁止外扩）。
5. `extra_constraints`：必带约束——`不生成额外人物`、`不引入画面外人物`、`角色身份不可变`、`不添加未提及服装或道具`。
6. `need_supplement`：明确请求上游（脚本 / 运营 / 用户）补图的清单。

## 禁止项

- 禁止在没有参考图时仍按"有图"流程继续，让 `prompt_compiler` 自行脑补身份。
- 禁止使用过于开放的身份描述（例如"一名年轻女性"）——必须具体到 6 项锚点。
- 禁止把 `style_direction` 设置为非白名单词（例如"赛博朋克"但项目风格是"港式写实"）。
- 禁止在 `need_supplement` 为空的同时声称"已缺图但无需补充"——这种情况必须触发 `quality_inspector` 的 `missing_reference_without_notice` 硬失败。

## 正确写法

```yaml
SUBJ_YANG:
  no_reference_image: true
  identity_description:
    gender: 男
    age_band: 28-32
    hair: 黑色短发，两侧微推
    body: 中等偏瘦，肩宽适中
    signature_wear: 白色立领衬衣 + 深灰西裤
    distinguishing_feature: 右眉尾有 1cm 旧疤
  first_frame_lock: >
    SUBJ_YANG 白衬衫领口微敞，侧身站在办公桌左侧，
    右手拇指压住文件夹边缘，脸朝镜头 3/4，眼神下垂 15°。
  allowed_style:
    - 港式写实
    - 低饱和冷调
  extra_constraints:
    - 不生成额外人物
    - 不引入画面外人物
    - 角色身份不可变
    - 不添加未提及服装或道具
  need_supplement:
    - 尽快补一张 SUBJ_YANG 的正面证件式参考图
```

## Agent 执行

- `scene_analyst` 产出降级卡。
- `prompt_compiler` 在首次调用该主体时，把 `first_frame_lock` 整段写入首帧描述，把 `extra_constraints` 并入硬约束池；不得对 `identity_description` 做任何美化改写。
- `quality_inspector` 对每个 `no_reference_image=true` 的主体，必须逐项检查 6 个身份锚点齐全、首帧锁已注入、风格未外扩；任一项缺失按 P0 阻断处理。
