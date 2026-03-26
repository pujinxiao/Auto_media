全流程优化：


正向提示词和反向提示词都需要，反向过少
先优化完成然后依次接入DSPy 与 Generative Feedback Loops





基于对 `image_0.png` 界面版式的反向工程分析，结合你之前所描述的“AI 短剧生成项目”的一致性治理方案，我为你整理了一份完整的短剧生成全流程规范文档。

这份文档不仅列出了线性流程，还详细规定了每个阶段的内容结构、输入输出数据以及图像中对应的表现。

---

# AI 短剧生成项目：全流程规范与数据结构文档

> 修订日期：2026-03-25
>
> 目标：在同一个剧本的流水线执行过程中，自动保证所有镜头在画风、场景氛围、人物外貌上的视觉一致性，通过引入 DSPy 实现结构化提取，通过 Generative Feedback Loops 实现闭环纠错。无需新增用户界面，纯后端实现。

---

## 一、 全流程（Pipeline）概览

图像 `image_0.png` 界面清晰地展示了一个从左到右的线性瀑布流流程。虽然分辨率较低，但可以通过模块识别出业务阶段：

```text
[文本剧本] -> [文本摘要] -> [文本故事板] -> [角色人设图] -> [场景基调图] -> [视频素材]
  (列 1)       (列 2)       (列 3)       (中间排图)    (偏右排图)     (最右侧)
```

**完整的业务全流程线性图示：**

1.  **世界观与剧本建立** (列 1) -> 产出 `Story` 实体。
2.  **构建 StoryContext (Phase 1)** -> 产出 `SceneStyle` 规则库。
3.  **构建 StoryContext (Phase 2, DSPy)** -> 产出结构化 `CharacterLock`。
4.  **故事板（Storyboard）生成** (列 2, 列 3) -> 产出 `Shot` 列表。
5.  **人设图生成与 Visual DNA 回填** (中间排图) -> 产出 `Character DNA` 投影。
6.  **场景基调图生成与场景缓存** (偏右排图) -> 产出 `Environment Key Art`。
7.  **镜头视觉 Prompt 构建** -> 产出 `final_generation_prompt`。
8.  **一致性生图与 VLM 质检反馈环路** -> 产出经过 Feedback 校验的图片。
9.  **视频生成** (最右侧) -> 产出最终视频素材。

---

## 二、 详细阶段规范与数据结构

### 2.1 阶段 1: 剧本与世界观建立 (Script & World Setting)

* **输入**: 用户输入的剧本（列 1）和世界观问答内容。
* **图像对应**: 界面最左侧的纯文本列。
* **处理逻辑**: LLM 总结出完整的世界观设定。
* **输出数据结构**:
    ```json
    {
      "story_id": "uuid",
      "genre": "修仙",
      "art_style": "fantasy Chinese ink painting, volumetric lighting",
      "selected_setting": "The Cyan Mist Sect hall is built of grey stone and floats on clouds, emitting soft light. The Peak of decisive battle is stormy and epic.",
      "characters": [...]
    }
    ```
* **全局规范**: 此阶段内容一旦建立，除剧情修改外，不得修改 `genre` 和 `selected_setting`。

### 2.2 阶段 2: 故事板生成 (Storyboard Generation)

* **输入**: `selected_setting`, `characters`, `SYSTEM_PROMPT`（故事板导演规则）。
* **图像对应**: 界面第 2 列（文本摘要）和第 3 列（文本故事板块）。
* **处理逻辑**: LLM 逐镜头拆解剧本，不再将 Portrait Prompt 直接透传，而是透传“干净角色块”（Visual DNA 标签）。
* **输出数据结构 (`Shot` 实体)**:
    ```json
    {
      "story_id": "uuid",
      "shot_id": 1,
      "environment_and_props": "宗门大殿，议事",
      "subject_and_clothing": "黎明，穿着白色汉服",
      "main_char": "黎明",
      "visual_elements": {
        "subject_and_clothing": "clean_character_黎明",
        "environment_and_props": "cyan mist sect hall"
      },
      "mood": "议事，庄重",
      "final_video_prompt": "medium shot, reverent atmosphere, large hall"
    }
    ```
* **全局规范**: 使用 Prompt Caching 缓存 System Prompt 和 Few-Shot Examples。

### 2.3 阶段 3: 角色视觉 DNA 提取与生成 (Character DNA & Portrait Generation)

* **输入**: `characters[].description`。
* **图像对应**: 界面第 4 列文本块，以及中间一排角色的全身肖像图。
* **处理逻辑**: 引入 **DSPy Module**，将中文描述转换为硬锁（生理特征）和软锁（默认服装）。
* **输出数据结构 (`CharacterLock`, DSPy JSON)**:
    ```json
    {
      "黎明": {
        "body_features": "young male, silver-white hair, ice blue eyes, slender 175cm",
        "default_clothing": "white hanfu with blue cloud embroidery"
      }
    }
    ```
* **人设图规范**: 生成人设图，必须在生成头部肖像的同时，生成全身像。
* **Visual DNA 回填**: 生成成功后，建议将结构化缓存投影回填为 compatible 版 `visual_dna` 文本：
    ```json
    Story.character_images["黎明"]["visual_dna"] = "young male, silver-white hair, ice blue eyes, slender 175cm"
    ```

### 2.4 阶段 4: 场景风格缓存与基调图生成 (Environment Style & Key Art Generation)

* **输入**: `Story.genre`, `Story.selected_setting`。
* **图像对应**: 偏右侧文本列，以及两张并排的场景风景基调图。
* **处理逻辑**: 根据 genre 映射内置规则库（修仙、都市等），并从 selected_setting 中提取增强规则。生成该场景的“概念基调图”以锁定氛围。
* **输出数据结构 (`SceneStyle` 规则)**:
    ```json
    [
      {
        "keywords": ["宗门", "大殿", "议事"],
        "extra_prompt": "grand sect hall, stone pillars, reverent atmosphere, floating clouds, mystical symbols",
        "key_art_url": "url_to_base_hall_image"
      }
    ]
    ```

### 2.5 阶段 5: 镜头视觉 Prompt 构建 (Shot Prompt Construction)

* **输入**: `Shot.visual_elements`, `CharacterLock`, `SceneStyle`, `Story.art_style`。
* **处理逻辑**: 集中构建运行期 `StoryContext`。将原本分散在各个模块拼 Prompt 的逻辑，统一在此集中处理。遵循顺序：核心内容 > 生理特征 > (换装检测)服装 > 通用情绪 > 场景氛围 > 基础画风。
* **核心公式 (`final_generation_prompt`)**:
    ```text
    正向 prompt:
      [干净角色块] + [通用情绪映射词] + [final_video_prompt] + [scene_style extra] + [art_style]
    ```

### 2.6 阶段 6: 一致性素材生成与纠错环路 (Consistency Asset Generation & QA Loop)

* **输入**: `final_generation_prompt`, `negative_prompt`。
* **图像对应**: 此阶段没有独立的文本列，它是生成图片背后的“质检员”。
* **处理逻辑**: 引入 **Generative Feedback Loop**。
* **质检规范**:
    1.  **感知**: 图片 API 生成初始图。
    2.  **反向描述 (VLM)**: 调用轻量级 VLM（如 Moondream2）反向提取图片中的关键视觉特征（如：发色=金色）。
    3.  **对比与反馈**: 将提取特征与 `CharacterLock`（黎明=银发）对比。若匹配失败（例如，金发 vs 银发），增加硬约束 Prompt 重绘。
* **输出**: 经过 Feedback 校验、满足 Visual DNA 要求的图片素材。

### 2.7 阶段 7: 视频生成 (Video Generation)

* **输入**: 阶段 6 校验通过的图片素材，`final_generation_prompt`。
* **图像对应**: 界面最右侧的深色块（可能是视频生成或上传点）。
* **处理逻辑**: 在 chained 模式下通过帧传递控制连续性。
* **输出数据结构 (`VideoAsset`)**:
    ```json
    {
      "story_id": "uuid",
      "shot_id": 1,
      "video_url": "url_to_final_video"
    }
    ```
* **全局规范**: 若视频 Provider 不支持独立 negative 参数，则丢弃 negative，严禁将其硬拼接到正向 Prompt 中（不要写 `"do not include modern objects..."`）。

---

## 三、 全局规范汇总

### 3.1 画风头规范 (Art Style Header)

* 自动流水线和手动链路（Step5）必须完全拉齐。
* `/api/v1/image/*`、`/pipeline/{id}/generate-assets` 等素材生成入口，统一消费 `X-Art-Style` Header 作为全局基调，而不是在每个 Prompt 里反复描述基础画风词。

### 3.2 Prompt Caching 消息排布规范

为最大化 Prompt Caching 命中率，LLM 请求中的 messages 排布顺序必须始终遵循“从静态到动态”：

```text
[静态 SYSTEM_PROMPT] -> [静态 Story Context设定] -> [静态 Few-shot examples] -> [动态 Current Task]
```
只有静态前缀超过 `1024 tokens` 时才建议启用 Caching，不对过短文本（<1024 tokens）启用。

### 3.3 负向提示词规范 (Negative Prompt)

* 必须同步接入：`generate_image()`、`generate_images_batch()`、`generate_videos_chained()` 内部生图。
* **构建公式**:
    ```text
    负向 prompt:
      [portrait contamination terms, studio, portrait] + [genre negative, modern buildings] + [single-character negative]
    ```
* 多角色同框时，使用 `set()` 集合运算对 negative 词自动去重，防止 Payload 超长。








这张图片虽然分辨率有限，但其**水平瀑布流（Horizontal Waterfall）**的 UI 布局，完美暴露了短剧生成背后的**系统架构与数据流转逻辑**。

如果你想把这个项目做得极其专业，我们不能仅仅停留在“这一列是什么数据”的层面，而是要进行一次 **“像素到逻辑 (Pixel-to-Logic)” 的深度拆解**。

以下是对这张界面的充实分析，涵盖了 UX/UX 哲学、隐性数据流以及你可以优化的工程锚点：

---

### 一、 核心 UI/UX 架构哲学：渐进式承诺 (Progressive Commitment)

整个界面的设计遵循了 AI 生产管线中非常经典的“渐进式承诺”原则。
从左到右，**计算成本（Token/GPU 算力）呈指数级上升**，而**修改成本则呈指数级下降**。

1.  **左侧（纯文本区 - 极低成本）：** 剧本、设定、分镜。修改只需要几秒钟和几美分的 API 调用。
2.  **中部（静态图像区 - 中等成本）：** 角色人设、场景概念图。生成需要几十秒，是视觉一致性的“定海神针”。
3.  **右侧（视频生成区 - 极高成本）：** 最终的视频渲染。耗时最长，成本最高。

**UI 隐喻**：这种布局强迫用户（或系统）在进入极其昂贵的视频生成阶段前，必须先“锁定”左侧和中部的文本与静态视觉锚点（`CharacterLock` 和 `SceneStyle`）。这与我们之前讨论的 `StoryContext` 集中构建理念在视觉上是完美契合的。

---

### 二、 逐列深度拆解与系统隐射

结合图片特征与你的后端设计，我们来看每一列到底承载了什么：

#### 🔴 区域一：文本与逻辑解构区（前三列）
这部分是整个引擎的“大脑”，所有的 Prompt Caching 都在这里发生。

* **第 1 列：原始输入与宏观世界（Source of Truth）**
    * **视觉特征**：密集的连续文本段落。
    * **系统定位**：这是用户的 Raw Script 或是未经清洗的剧情描述。
    * **工程隐患**：如果这里包含了高频变化的无用词汇，会破坏后续的 Prompt Caching 命中率。需要在此处加一层清洗。
* **第 2 列：结构化设定提取（The Context Builder）**
    * **视觉特征**：呈现块状或列表状的文本。
    * **系统定位**：这是从第 1 列提炼出的 `selected_setting`（世界观）和全局大纲。
    * **数据结构**：这就是你 `StoryContext` 的雏形数据区。
* **第 3 列：分镜序列化（The Storyboard Grid）**
    * **视觉特征**：高度结构化的短文本块，明显的列表感。
    * **系统定位**：这是 LLM 输出的 `Shot` 数组。每一个区块代表一个镜头（包含景别、动作、对白）。
    * **你的优化点**：这里**绝对不能**再出现冗长的角色外貌描述（比如“穿着白衣服的银发少年”），只能出现 `[Main_Char: 黎明]` 这样的指针（Pointer），指向后方的视觉锚点。

#### 🔵 区域二：视觉锚点锁定区（中间图像排）
这里是整条流水线最核心的**“防污染隔离带”**。

* **第 4 组：角色 DNA 阵列（Character Locks）**
    * **视觉特征**：一排清晰的角色全身/半身立绘，背景干净（通常是白底或灰底，以防背景污染）。
    * **系统定位**：这是 `character_appearance_cache` 的具象化展示。
    * **DSPy 融合点**：你之前想引入的 **DSPy 结构化提取**，其输出结果就直接映射为这一排图片。这里生成的图片必须采用严格的正向 Prompt（去除背景词）和统一的负向 Prompt，确保它们是纯粹的“视觉参考源”，而不是剧情图。
* **第 5 组：场景氛围基准图（Scene Key Art）**
    * **视觉特征**：横向的宽幅场景图（图片中偏右侧的两张大图），没有具体的主角，只有环境和光影。
    * **系统定位**：这是 `SceneStyle` 的具象化。它锁定了“宗门大殿”、“魔族深渊”等特定地点的色调和美术风格（`base_art_style` + `extra_prompt`）。

#### ⚫ 区域三：最终渲染区（最右侧）
* **第 6 列：视频合成块（The Final Render）**
    * **视觉特征**：深色背景块，带有明显的“播放 (Play)”图标。
    * **系统定位**：消费前面所有列的数据（分镜指针 + 角色 DNA + 场景风格），最终组装成 `final_generation_prompt` 发送给视频大模型。

---

### 三、 从静态图到“动态闭环”的架构建议

图片展示的是一个**理想的顺滑单向流**。但在实际的短剧生成中，一次性成功的概率极低。结合我们之前聊到的 **Generative Feedback Loops (VLM 质检)**，这个 UI 背后应该隐藏着以下机制：

1.  **隐藏的“重试环路” (Retry Loops)**：
    * 在第 4 组（角色人设）和最右侧（视频生成）之间，系统底层应该有一个 VLM 质检员。
    * 如果最终生成的视频帧里，角色的衣服颜色不对，数据流不应该崩溃，而是应该在后台自动打回该镜头的 Prompt 构建节点，追加纠错提示词，重新请求。

2.  **状态流转指示器 (State Management)**：
    * 虽然图中没画出来，但你的系统需要为每个 `Shot` 和 `CharacterLock` 维护状态字典：`status: pending | generating | qa_failed | qa_passed | completed`。
    * 只有前置依赖（如角色的 Visual DNA）状态为 `qa_passed` 时，后续的视频生成任务才能被放入队列。

3.  **人工干预锚点 (Manual Override)**：
    * 全自动流水线必然有“智障”的时候。在第 4 组角色立绘的下方，系统接口必须允许人工 PATCH（修改） `character_appearance_cache` 的 JSON 字段。
    * 也就是说，如果在这一步发现“黎明”的衣服不对，用户或运营应该能打断流水线，手动修改描述后，再让流水线继续往下走。

**总结来看：**
这张界面的版式非常优秀，它将复杂的数据结构转化为了直观的生产线。如果你要实现它，**后端的 `PipelineExecutor` 必须被重构为一个状态机 (State Machine)**，而不是一个简单的 `for` 循环，这样才能精准控制从“文本”到“视觉锚点”再到“视频”的稳定流转，并随时响应 Prompt Caching 的命中与 VLM 质检的打回。