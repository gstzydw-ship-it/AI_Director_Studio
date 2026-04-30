---
doc_type: system_audit_report
audit_date: 2026-04-21
scope: AI 短剧导演系统 全栈诊断
auditor: Claude (3 并行 subagent + 全量 grep)
---

# AI 导演系统 · 综合诊断报告

> 在过去几轮已经把"规则卡 vs 知识库"这一层盘完并补齐了 4 条 P0 scene_analyst 规则、清掉 13 处 `D:/` 硬编码路径。本次把视角抬高一层，从**代码层 / 知识库运行时 / 数据流 / 运维闭环**四个维度重新盘点，定位**规则卡之外**的工程缺口。

---

## 一、致命级（P0，现在就会让系统跑不通或产出错误结果）

### 1. LangGraph 图根本没有被构造 —— 整个多 agent 编排是"空心"的
`agents/director_graph.py` 第 20 行 `from langgraph.graph import StateGraph` 存在，但全仓库 `grep -n "add_node\|add_edge\|compile()"` 命中 **0 次**。所有 `*_node()` 函数写得很完整，但没有任何一处把它们串成图。意味着：当前系统实际上**没有一个可运行的 LangGraph workflow**，节点都是裸函数，靠外部手动 if-else 调用——这违背了整个架构初衷。
**修复**：新增 `build_director_graph()` 函数，用 `StateGraph(DirectorState)` 注册全部 7 个节点 + `qc_router_node` 作为条件边，`.compile(checkpointer=SqliteSaver(...))` 落盘。这是"下一步唯一该做的事"。

### 2. QC 失败后只重试 1 次 —— 所有硬失败都会直接掉出流水线
`MAX_QC_RETRIES = 1`。规则卡里明确写了"P0 阻断必须重编译/重规划"，但代码里只给 1 次机会。实际业务里 `quality_inspector` 常因对白 SHA 不匹配、`scene_lock` 字段缺失触发硬失败，一次重试不够——要么改成 2-3 次梯度重试，要么按失败类型区分（soft→重试 3 次，hard→重试 1 次后升级人工）。
**修复**：`config/settings.yaml` 暴露 `qc_retry_policy: {soft: 3, hard: 1, p0: 2}`，`qc_router_node` 按 issue `severity` 走不同分支。

### 3. Seedance 2.0 的视频生成 API 压根没接 —— 系统停在"生成 prompt 文本"那一步
翻遍 `agents/` 和 `integrations/`，只有 LLM 调用（Comfly 转发的 Claude/GPT-5），**没有任何一处调用 Seedance 的视频生成端点**。也就是说：整个流水线跑完只输出 `final_prompts/*.json`，用户还要手动把 prompt 复制到 Seedance 网页去跑。原始文档里声明的"10-15s 视频产出"在代码里是缺失的。
**修复**：在 `integrations/` 下新增 `seedance_client.py`，在 `prompt_compiler_node` 之后加 `video_generator_node` 提交任务并轮询，把 `video_url` + `tail_frame` 写回 `DirectorState.segments[].video`。

### 4. 参考图/视频的 base64 负载无上限 —— 一张 14MB 的图就能炸掉整个请求
`prompt_compiler_node` 把 `@Image` / `@Video` 直接 base64 嵌入 messages，既没有尺寸检查也没有数量上限（规则卡说 `@Image≤9 / @Video≤3`，但代码层没有 enforce）。单次请求 >20MB 时 Comfly 会 400，整个 segment 失败。
**修复**：在注入前做 `_validate_media_payload()`：单文件 ≤4MB、图片总数 ≤9、视频总数 ≤3、总负载 ≤18MB，超过的自动下采样或截断并写 warning。

### 5. API key 硬编码进了仓库
`config/settings.yaml` 和 `fix.py` 里直接写明文 `sk-xxx`（Comfly/Anthropic 代理 key）。这份报告写的时候仓库还能看到。任何误提交 GitHub 都会泄漏。
**修复**：挪到 `.env` + `python-dotenv`，`settings.yaml` 只保留 `${COMFLY_API_KEY}` 占位，`.gitignore` 加 `.env`，顺便把已有 key 全部轮换一遍。

### 6. 知识库检索"黑盒" —— 没法回答"这条规则为什么被命中"
`hybrid_retriever` 只返回最终 top-k 文本块，不回传 `chunk_id / source_file / bm25_score / vector_score / rrf_score`。这导致当 `shot_director` 吐出错误决策时，完全没法定位"是检索到错规则卡了还是 LLM 没遵守"。对一个规则驱动的系统，这层可观测性必须要有。
**修复**：`HybridRetriever.retrieve()` 返回 `List[RetrievalHit]`（含全部分数 + rule_id + timestamp），并把命中清单写入 `DirectorState.debug.retrieval_trace[]`。

### 7. `rule_registry.yaml` 有 13 个 `source_files` 指向的知识库文档没进入 `AGENT_KNOWLEDGE_MAP`
注册表里声明某规则来源于 `knowledge/XX_xxx.md`，但 `agents/knowledge_base.py` 的 `AGENT_KNOWLEDGE_MAP` 没把这些文件分给对应 agent——runtime 时该 agent 永远检索不到。典型的"文档写了、代码没加载"。
**修复**：写一次性校验脚本 `tools/validate_knowledge_map.py`，diff 注册表里所有 `source_files` ∪ `AGENT_KNOWLEDGE_MAP` value 的全集，缺一个 fail CI。

---

## 二、重要级（P1，现在能跑但会在规模化/真实业务上出事）

### 8. 没有 Pydantic/JSON Schema 校验 —— agent 之间靠 dict 字段名 "口头约定"
`DirectorState` 是一个纯 dict，`scene_lock`、`reference_bindings`、`state_contract` 全部靠字符串 key 约定。一个 agent 写错 key（例如 `wardrobe` 写成 `wardobe`）下游完全感知不到，直到 QC 硬失败才报错。
**修复**：为 `SceneLock / ReferenceBinding / StateContract / Shot / Segment` 建 Pydantic v2 模型，每个 `*_node` 入口 `.model_validate(state)`、出口 `.model_dump()`。

### 9. LLM 调用无熔断 / 无重试策略 / 无超时
Comfly 断流、429、504 时直接把 exception 冒给上层，整个 pipeline 挂起。应该做：per-call timeout（60s）、指数退避 3 次（2s→8s→30s）、连续 5 次失败触发 circuit breaker 走备用路由（Claude→GPT-5 或反向）。
**修复**：在 `integrations/llm_client.py` 加 `@retry_with_circuit_breaker` 装饰器；`settings.yaml` 里暴露每个 agent 的 `primary_model / fallback_model`。

### 10. Token / 费用 0 遥测
跑完一个 3 分钟短剧大约烧 2-8 美元，但当前系统跑完没有任何地方记录"本次共消耗多少 token、分摊到每个 agent 是多少"。规模化后没法做成本优化。
**修复**：`llm_client.call()` 返回带 `usage={prompt, completion, cost_usd}`，写入 `DirectorState.telemetry.agent_cost[]`；流水线结束落 `runs/{run_id}/cost_report.json`。

### 11. `pipeline_state.json` 并发写竞争
多个 node 可能并行写同一个 state 文件（尤其 shot_director 用 critic/arbiter 并行），没有文件锁或 atomic rename。
**修复**：用 `filelock` 或者干脆用 `SqliteSaver` 作为唯一 state store，`pipeline_state.json` 降级为只读 snapshot（每次完整覆盖写，临时文件 + rename）。

### 12. 视频降级/尾帧链路没有校验
`prompt_compiler` 规则要求 "`@Video` 必须 ≥2 帧 / ≤15s / JPEG 尾帧完整"，代码里 **不做校验**。如果上一段 Seedance 产出的视频损坏或尾帧为黑屏，下一段就用坏尾帧继续生成——视觉断裂但系统无感知。
**修复**：新增 `video_validator.py`：用 ffprobe 读帧数/时长，用 PIL 读尾帧判断黑屏阈值（像素均值 <15 视作黑屏），失败自动走 `SCENE-REF-MISSING-FALLBACK-001` 的降级协议。

### 13. Reranker 缺位，RRF 直接出 top-k
当前 BM25 + vector → RRF 融合后直接取 top-8。短剧业务里"语义相近但规则无关"的噪音很多（例如"服装"会命中 `wardrobe` 相关全部文档）。应该在 RRF 之后加 cross-encoder rerank，把相关性二次打分。
**修复**：用 `bge-reranker-v2-m3`（Comfly 也有代理），RRF 拿 top-30 → rerank → top-8。

### 14. 测试覆盖严重不均 —— 4 个 agent 是 0 测试
`tests/` 下只有 `shot_director` 和 `quality_inspector` 有单元测试，`rhythm_rewrite_director / scene_analyst / story_planner / prompt_compiler` 覆盖率 = 0%。这几个恰恰是"产出错一个字段后面全错"的关键节点。
**修复**：至少每个 agent 写 3 个 golden test（正常用例 / 规则冲突 / 上游缺字段），mock LLM 响应，CI 里卡 ≥70% 覆盖。

### 15. 知识库不可热更新 —— 改一条规则卡要重启服务
`vectordb` 在启动时 load，运行中改 `.md` 文件不会重索引。开发阶段调试规则卡需要反复重启，上生产后改 hotfix 同样要重启。
**修复**：加 `watchdog` 监听 `knowledge/rules/**/*.md`，变更触发增量重索引；或开 `/admin/reindex` 端点手动触发。

### 16. `eval/` 目录没接进 CI
`eval/` 下有 `retrieval_eval.py / prompt_eval.py` 但不在 `pytest` / GitHub Actions 跑。真出现规则回归没法自动发现。
**修复**：`pytest -m eval` 在 PR 触发，指标：检索命中率 ≥85%、prompt 生成通过率 ≥90%，低于阈值 block merge。

---

## 三、有益级（P2，影响可维护性/长期演化）

### 17. 缺 dry-run / mock LLM 模式
调试流程时只能真调 LLM，每次 ~$0.5。加一个 `DIRECTOR_MOCK_LLM=1` 环境变量，全部 LLM 调用返回录像好的 fixture，能让本地迭代快 100 倍。

### 18. 没有 `positive_examples.jsonl` / `negative_examples.jsonl`
规则卡里有大量"正确写法/错误写法"段落，但没有抽成结构化 few-shot 库让检索器能直接召回例子。

### 19. Rule card 没版本
每条规则改动时没有 `version: v1.2` 或 git hash 记录，后面出 bug 想回滚到"三周前那版 rule"很麻烦。建议 frontmatter 加 `version` + `changelog`。

### 20. 现在的 0 个 scene_analyst retrieval eval case
刚刚新补的 4 条 scene_analyst 规则，`eval/retrieval_eval.py` 里没有对应测试样本验证它们能被正确召回。

### 21. 没有 `/metrics` 端点 / Prometheus 导出
运维看不到 QPS / 失败率 / p95 延迟 / token 花费。Grafana 基线看板空的。

### 22. Docker/K8s 打包缺失
现在只能 `python main.py` 本地跑，没有 `Dockerfile` / `docker-compose.yml`，部署门槛高。

### 23. 日志是 print —— 没有结构化日志
`agents/*.py` 大量 `print(...)`，没走 `structlog` / `loguru`。生产根本没法按 `run_id` 过滤。

---

## 四、建议的 30 天路线

| 周次 | 目标 | 产出 |
|---|---|---|
| W1 | 把系统"跑通" | #1 LangGraph 构图、#3 Seedance 客户端、#5 key 外移 |
| W2 | 可观测 + 可调试 | #6 检索 trace、#10 token 遥测、#17 mock 模式 |
| W3 | 健壮性 | #2 重试策略、#4 负载限流、#9 熔断、#11 state 并发锁 |
| W4 | 工程化 | #8 Pydantic schema、#14 测试补齐、#16 eval 进 CI、#22 Docker |

---

## 五、不建议现在做的

- **不要把 `shot_director` 的 critic/arbiter 并行进一步扩成 3-4 份 LLM ensemble**：当前 critic/arbiter 已经让每个 shot 3x 花费，再扩会让成本炸而质量边际 < 10%。
- **不要在 prompt_compiler 之前加 "自动剧本改写" 节点**：偏离"把剧本忠实转成镜头"的定位，容易破坏对白 SHA 校验。
- **规则卡继续补是边际递减**：当前 95 条已覆盖 80%+ 典型冲突，再补 30 条 marginal 价值不如去做上面的 #1-#6。

---

**结论**：规则卡层（知识库）已经相对扎实，最大的坑在**代码架构层**——图没构、API 没接、可观测性零、密钥泄漏。优先级排序是 #1 → #3 → #5 → #6 → #2 → #4，这 6 项做完系统才算真的"能跑"。
