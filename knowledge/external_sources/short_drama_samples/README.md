---
source_id: SHORT-DRAMA-SAMPLES-94-20260516
title: 94集真人短剧样片分析索引
doc_type: external_source_index
status: draft
runtime_retrieval: true
---

# 94集真人短剧样片分析索引

样片目录：`H:\样片`

全量连续镜头统计输出：

- `output/short_drama_analysis_full_20260516_105744/short_drama_shot_director_report.md`
- `output/short_drama_analysis_full_20260516_105744/shot_records.csv`
- `output/short_drama_analysis_full_20260516_105744/analysis_summary.json`
- `output/short_drama_analysis_full_20260516_105744/keyframes/`

## 全量统计结论

- 视频数：94
- 竖屏视频：94/94
- 检测镜头数：3410
- 平均镜头时长：3.21秒
- 中位镜头时长：1.92秒
- P25/P75：0.96秒 / 3.84秒
- <=1.2秒短切：880个，占25.8%
- 1.2-3.0秒常规镜头：1499个，占44.0%
- >3.0秒长镜头：1031个，占30.2%

## 对 agent 的直接启发

1. 短剧节奏不是“多切特写”。样片中 CU/ECU 只占约2.1%，关系景、环境关系景、半身景占主导。
2. 快节奏的主要方法是缩短关系景/半身景的镜头时长，并让每个镜头承载明确动作、台词或反应落点。
3. 特写只用于信息爆点、道具揭示、受击反应、情绪顶点，不承担整段常规对话。
4. 需要保留“低切换长段”档位。部分集数平均镜头时长明显变长，说明样片体系中也允许慢处理、对峙、等待和情绪消化。
5. 镜头导演应先做 coverage 任务，不先堆机位术语。每个镜头必须回答：拍关系、拍动作、拍信息、拍反应、还是拍尾帧承接。

## 关联模板

- `rhythm_control_template_library_v1.yaml`
- `shot_coverage_template_library_v1.yaml`
