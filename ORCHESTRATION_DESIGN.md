# Orchestration 设计文档 — Comic Pipeline 后端编排层

本文档记录了 Comic Pipeline v4.0 在从「Prompt 规范」推向「全自动生产线」时，需要在 Python 后端编排层解决的 3 个工程问题。这些问题无法通过修改 Agent Prompt 解决，必须由后端代码处理。

---

## 1. 分镜数爆炸 — 动态滑窗切片器

### 问题

在高潮章节（如多人激烈对骂、战场高频互动），导演 Agent 可能产出 80-100 个 P编号。下游美术和分镜 Agent 的单次输出 Token 窗口（通常 4096-8192）无法容纳全部场景，导致输出在 P65 左右截断，后 30% 画面丢失。

### 检测

`validators/single_file.py` 已加入 `check_p_number_explosion_risk()`：
- ≤30 个 P编号 → PASS
- 31-50 个 → WARN（建议分批）
- >50 个 → FAIL（必须分批）

### 解决方案（Orchestrator 层）

```
如果 导演 Agent 输出的 P编号 > 30：
  → 按每 20 个 P编号切为一组
     Group A: P01-P20
     Group B: P21-P40
     Group C: P41-P60 ...
  → 依次将每组单独喂给美术 Agent 和分镜 Agent
  → 组间通过 01_故事 的状态快照 JSON 保持角色一致性
  → 最终合并所有组的输出
```

### 伪代码

```python
def segment_and_dispatch(director_output, batch_size=20):
    p_numbers = extract_p_numbers(director_output)
    if len(p_numbers) <= 30:
        return call_agent_3_and_4(director_output)  # 单次传递
    
    batches = chunk(p_numbers, batch_size)
    all_art_outputs = []
    all_cine_outputs = []
    
    for i, batch in enumerate(batches):
        batch_script = filter_director_output_by_p_numbers(director_output, batch)
        art = call_agent_3(batch_script)
        cine = call_agent_4(batch_script, art)
        all_art_outputs.append(art)
        all_cine_outputs.append(cine)
    
    return merge_outputs(all_art_outputs), merge_outputs(all_cine_outputs)
```

---

## 2. 状态快照无限膨胀 — 快照冷却与归档

### 问题

当小说连载到 150 章时，状态快照 JSON 累积了数百个历史角色、已销毁的场景和已死亡的配角。这个大 JSON 不仅吃掉大半上下文窗口，还会产生"注意力污染"——分镜师可能把已死角色画进当前画面。

### 解决方案（Orchestrator 层）

在每次传入 Agent 之前，由后端脚本裁剪快照：

```
规则：
  1. 凡是连续 5 章未出现的角色/场景 → 标记为 status: "archived"
  2. 凡是剧情中明确死亡/毁灭的资产 → 标记为 status: "archived"
  3. 喂给 Agent 的快照仅包含 status: "active" 的资产
  4. 归档资产保留在完整快照中（供回溯查询），但不注入上下文
```

### 伪代码

```python
def prune_snapshot(snapshot, chapter_num, inactive_threshold=5):
    active_chars = []
    for char in snapshot.get("all_characters", []):
        chapters_since_last = chapter_num - char["last_appearance_chapter"]
        if char.get("status") == "dead" or chapters_since_last > inactive_threshold:
            char["status"] = "archived"
        else:
            active_chars.append(char)
    
    # 仅传递活跃角色（上限 Top 20 核心角色以控制 Token）
    snapshot["active_characters"] = active_chars[:20]
    return snapshot
```

---

## 3. 跨章 ID 碰撞 — 全局主键映射

### 问题

LLM 在单章内为角色分配 ID（如 CHAR_01、CHAR_02）时，如果不知道前几章的 ID 分配情况，会把同一个 `CHAR_01` 在不同章节分配給不同角色。导致视频渲染时发生跨章换脸。

### 当前 Prompt 层防御

`02_导演漫改 §6.3` 已要求 Agent 读取上一章状态快照的 ID 清单后从最大编号续编。`validators/cross_file.py` 已加入 `check_id_propagation()` 检测 ID 丢失。

### 剩余风险

Prompt 层防御依赖 LLM 正确执行——在连续运行数千次时，仍存在 ~1% 的出错概率。需要后端数据库做硬性兜底。

### 解决方案（Orchestrator 层）

建立全局主键映射表（PostgreSQL / Redis）：

```
角色注册表:
  CHAR_01 → 陆沉（男主角，第1章首次出场）
  CHAR_02 → 苏清寒（女主角，第1章首次出场）
  CHAR_03 → 林若雪（配角，第3章首次出场）
  ...

场景注册表:
  SCENE_01 → 北区监狱
  SCENE_02 → 暗鸦森林
  ...

道具注册表:
  PROP_01 → 火球符
  ...
```

工作流：
```
1. 大模型产出时只写角色名（Name），不分配 ID
   例如：{ "name": "林若雪" }
   
2. 后端脚本查询注册表：
   - 若"林若雪"已注册 → 绑定已有 ID（CHAR_03）
   - 若"林若雪"未注册 → 分配新 ID（CHAR_NN）并写入注册表

3. 传给下游 Agent 的最终 Prompt 中，后端脚本将所有的 name 替换为 ID
```

### 伪代码

```python
class GlobalIDRegistry:
    def __init__(self, db_connection):
        self.db = db_connection
    
    def resolve_character_id(self, name: str) -> str:
        existing = self.db.query("SELECT id FROM characters WHERE name = ?", name)
        if existing:
            return existing["id"]
        new_id = self.db.next_sequence("characters")
        self.db.insert("characters", {"id": new_id, "name": name})
        return new_id
    
    def post_process_agent_output(self, text: str) -> str:
        # 将 LLM 输出的角色名替换为全局 ID
        for name, char_id in self.db.get_all_characters().items():
            text = text.replace(f'"name": "{name}"', f'"character_id": "{char_id}", "name": "{name}"')
        return text
```

---

## 当前仓库已内置的防御

| 防御层 | 位置 | 作用 |
|--------|------|------|
| P编号爆炸检测 | `validators/single_file.py` → `check_p_number_explosion_risk()` | 检测 >30 场景 → 建议分批 |
| ID 传播检查 | `validators/cross_file.py` → `check_id_propagation()` | 检测 ID 从导演到美术丢失 |
| JSON 自愈 | `validate_pipeline.py` → `prevalidate_json()` | LLM JSON 格式错误自动修复 |
| Prompt 层续编 | `02_导演漫改 §6.3` | 要求 Agent 从最大 ID 续编 |

---

## 实施路线图

| 优先级 | 任务 | 预估工时 | 依赖 |
|:--:|------|:--:|------|
| P0 | P编号爆炸检测（✅ 已完成） | — | — |
| P1 | 滑动窗口切片器（Orchestrator） | 3-5 天 | 需要 LLM API 调用框架 |
| P1 | 全局 ID 注册表（Orchestrator） | 2-3 天 | 需要数据库 |
| P2 | 快照裁剪工具（Orchestrator） | 1-2 天 | 依赖 ID 注册表 |
| P3 | 全自动 Headless Pipeline | 1-2 周 | 以上全部就绪后 |
