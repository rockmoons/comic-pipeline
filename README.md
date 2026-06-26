# Comic Pipeline — 4-Agent AI 漫剧生成 + 校验体系

[![Validate](https://github.com/your-org/comic-pipeline/actions/workflows/validate.yml/badge.svg)](https://github.com/your-org/comic-pipeline/actions/workflows/validate.yml)

将小说/故事文本通过 4 个 AI Agent（故事创作→导演→美术指导→分镜师）自动转化为可输入 Seedance 2.0 / libtv 的视频提示词，并附带 112 项内部自检 + 46 项外部脚本校验。

## 快速开始

### 跑流程
按顺序执行 4 个 Agent 的 prompt：
```
01_故事创作_v3.0.md  →  02_导演漫改_v3.0.md  →  03_美术资产_v3.0.md  →  04_分镜生成_v3.0.md
```

### 校验
```bash
# 终端报告
python validate_pipeline.py story.txt director.txt art.txt cine.txt

# JSON 输出（CI 集成）
python validate_pipeline.py --json story.txt director.txt art.txt cine.txt

# 一键状态 + 冒烟测试
python pipeline_runner.py

# 校验指定目录
python pipeline_runner.py check test_fixtures/prison_story/
```

## 校验体系

| 层级 | 位置 | 项数 | 说明 |
|------|------|:--:|------|
| 内部自检 | 4 个 prompt 文件内 | **112** | LLM 产出时逐项执行，覆盖全部可量化规则 |
| 外部脚本 | `validate_pipeline.py` | **46** | Python 确定性检查，跨文件交叉比对 |
| 致命传播链 | 脚本第 3 层 | **4** | 检测静默传播的致命错误 |

### 校验通过率
- v1（修真界网约车）：**93.5%**，0❌ 0🔴
- v2（星际监狱心理医生）：**93.5%**，0❌ 0🔴

## 项目结构

```
mutil_agent_all/
├── 01_故事创作_v3.0.md      # Agent 1: 故事创作（32 项自检）
├── 02_导演漫改_v3.0.md      # Agent 2: 导演漫改（25 项自检）
├── 03_美术资产_v3.0.md      # Agent 3: 美术指导（32 项自检）
├── 04_分镜生成_v3.0.md      # Agent 4: 分镜师（23 项自检）
├── RULES.md                 # 4 条修改铁律
├── validate_pipeline.py     # 外部校验主入口
├── validators/              # 4 层校验模块
│   ├── single_file.py       # 单文件结构（13 项）
│   ├── cross_file.py        # 跨文件交叉（20 项）
│   ├── propagation.py       # 致命传播链（4 项）
│   └── srt_checks.py        # SRT 专项（9 项）
├── utils/
│   ├── parser.py            # 输出解析器
│   └── reporter.py          # 报告生成（终端+JSON）
└── test_fixtures/
    ├── sample_run/          # 修真界网约车测试数据
    └── prison_story/        # 星际监狱心理医生测试数据
```

## 校验报告示例

```
════════════════════════════════════════════════════════
  Comic Pipeline 校验报告 v1.0
  视觉风格：CG国漫 | 章节：第1章
════════════════════════════════════════════════════════

第一层：单文件结构 (13项)  → 12✅ 0❌ 1⚠️  92%
第二层：跨文件交叉 (20项)  → 17✅ 0❌ 3⚠️  85%
第三层：传播链检测 (4项)   → 4✅ 0❌ 0⚠️  100%
第四层：SRT专项 (9项)      → 8✅ 0❌ 1⚠️  89%
────────────────────────────────────────────────────────
  结果：43 ✅ / 0 ❌ / 3 ⚠️
  通过率：93.5%
  致命问题：0 🔴
════════════════════════════════════════════════════════
```

## 4 条修改铁律

修改任何 prompt 文件前必须：
1. **查关联链** — 向上查谁产出，向下查谁消费
2. **出清单表** — 5 列（文件/位置/改什么/为什么/影响下游）
3. **等确认** — 清单输出后等用户回复再动手
4. **验证** — 改完 grep 确认，不凭口头宣称

## 视觉风格

默认 **CG国漫**（三维渲染，国产动画电影风）。支持 49 种风格 Token，覆盖 3D/2D/真人/定格。

## 目标平台

**libtv**（LiblibAI 出品，集成 Seedance 2.0 + 节点式工作流 + Agent CLI）

## 校验分类体系

所有 112 项内部校验均分入以下类别：

| 类别 | 含义 | 现状 |
|------|------|:--:|
| A 类 | 可量化（数值阈值） | ~70 项 |
| B 类 | 结构化（格式/字段） | ~42 项 |
| C 类 | 主观（LLM 判断） | **0 项（已清零）** |
| D 类 | 交叉验证（跨 Agent） | 28 项 |
| E 类 | 有失败修复步骤 | 88 项（94% 覆盖率） |
