# Outline Internal Concurrency
> 生成日期：2026-04-02
## 背景

`/api/v1/story/generate-outline` 之前采用单次 LLM 请求，要求模型一次性返回完整 6 集 `outline`。
这会带来两个问题：

- 单次返回内容较长，部分 provider 更容易超时或返回不完整 JSON。
- 如果只为降低时延而拆成 6 个独立请求，会明显增加重复上下文，且更容易出现人物与地点命名漂移。

当前实现改为“全局蓝图 + 分段并发扩写”的两阶段流程，默认内部并发数为 `2`，但接口对前端保持不变，仍然一次返回完整 `outline`。

## 当前流程

### 1. Blueprint 阶段

后端先调用一次 `OUTLINE_BLUEPRINT_PROMPT`，只生成：

- `meta`
- `characters`
- `relationships`
- `season_plan.episode_arcs`
- `season_plan.location_glossary`
- `season_plan.tone_rules`

这一阶段不直接生成完整 `summary`、`beats`、`scene_list`，目的是把原始长设定压缩成后续 batch 可复用的全局蓝图。

### 2. Batch 阶段

后端根据 `outline_generation_concurrency` 生成分段：

- `1`：`[1,2,3,4,5,6]`
- `2`：`[1,2,3]`、`[4,5,6]`
- `3`：`[1,2]`、`[3,4]`、`[5,6]`

当前默认值是 `2`。

每个 batch 只接收：

- 压缩后的 `blueprint`
- 本批目标集数

每个 batch 只返回该批的 `outline` 条目，不返回 `meta`、`characters`、`relationships`。

### 3. 汇总阶段

所有 batch 完成后，主协程会：

- 汇总全部 `outline` 条目
- 按 `episode` 升序排序
- 复用整季校验逻辑检查 `1..6` 是否完整连续
- 统一落库

因此前端最终拿到的结果仍然是完整、按集排序的：

- `meta`
- `characters`
- `relationships`
- `outline`

## 配置项

后端新增配置项：

- `outline_generation_concurrency`

默认值：

```env
OUTLINE_GENERATION_CONCURRENCY=2
```

取值范围：

- 最小 `1`
- 最大 `3`

超过上限会被钳制到 `3`。

## 关键实现约束

### 一次性落库

并发 batch 不直接写数据库。
所有 batch 只在内存中返回结果，最后统一调用一次 `repo.save_story(...)`。

这样做是因为当前 `save_story` 是“读取旧值后 merge 再写回”的语义；如果每个 batch 单独落库，会有覆盖彼此结果的风险。

### 同一 story 加锁

同一个 `story_id` 的 `generate_outline` 在服务进程内使用锁串行化，避免页面自动恢复和用户手动重试同时触发两轮大纲生成。

### 前端接口不变

当前实现没有把 `/generate-outline` 改成流式接口。
前端仍然通过普通 `fetch(...).json()` 一次拿完整结果，不消费中间批次状态。

## 为什么默认并发 2

默认采用 `2` 而不是 `3`，原因是：

- 每批 3 集，局部剧情连续性更好
- 请求数更少，重复上下文更低
- 对 provider 限流更保守
- 调试与定位失败更简单

如果后续 telemetry 显示稳定，可以再把配置提升到 `3`。

## 已知取舍

- 成本通常会略高于单次整季生成，因为 `blueprint` 会被多个 batch 重复引用。
- 一致性虽然优于“6 个单集完全并发”，但仍可能比单次整季略弱。
- 当前版本不做 batch 层面的自动重试；任一 batch 校验失败会直接让整次生成失败。
- 当前锁是进程内锁；如果未来部署为多进程/多实例，需要改成分布式锁或持久化协调机制。

## 回退方式

如果需要回退到单次生成，可以把 `outline_generation_concurrency` 设为 `1`，这样仍然保留 blueprint 流程，但只会生成一个 batch。
