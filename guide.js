const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, PageBreak, Header, Footer, PageNumber, NumberFormat, AlignmentType, HeadingLevel, WidthType, BorderStyle, ShadingType, TableOfContents } = require("docx");
const fs = require("fs");

const P = { bg:"F4ECE0", hdr:"186A6A", acc:"D35400", hdrBg:"186A6A", altBg:"EDE8DF", line:"C8C0B4" };
const cellMargins = { top: 80, bottom: 80, left: 120, right: 80 };

function ccell(text, width, opts = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.PERCENTAGE },
    shading: { type: ShadingType.CLEAR, fill: opts.fill || "FFFFFF" },
    margins: cellMargins,
    children: [new Paragraph({
      alignment: opts.align || AlignmentType.LEFT,
      spacing: { line: 312, before: 20, after: 20 },
      children: [new TextRun({ text, size: opts.head ? 22 : 21, bold: !!opts.bold, color: opts.color || "000000", font: {eastAsia: opts.head ? "SimHei" : "Microsoft YaHei"} })],
    })],
  });
}

function tbl(headerCols, rows) {
  const widths = headerCols.map(function(x) { return x[1]; });
  var allRows = [];
  allRows.push(new TableRow({ tableHeader: true, children: headerCols.map(function(x) { return ccell(x[0], x[1], { fill: P.hdrBg, align: "center", bold: true, color: "FFFFFF", head: true }); }) }));
  for (var i = 0; i < rows.length; i++) {
    var children = [];
    for (var j = 0; j < rows[i].length; j++) {
      children.push(ccell(rows[i][j], widths[j], { fill: i % 2 === 0 ? "FFFFFF" : P.altBg }));
    }
    allRows.push(new TableRow({ children: children }));
  }
  return new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, rows: allRows });
}

function h1(t) { return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 480, after: 240, line: 312 }, children: [new TextRun({ text: t, size: 32, bold: true, color: P.hdr, font: {eastAsia:"SimHei"} })] }); }
function h2(t) { return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 360, after: 180, line: 312 }, children: [new TextRun({ text: t, size: 28, bold: true, color: P.hdr, font: {eastAsia:"SimHei"} })] }); }
function h3(t) { return new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 240, after: 120, line: 312 }, children: [new TextRun({ text: t, size: 26, bold: true, color: P.hdr, font: {eastAsia:"SimHei"} })] }); }
function para(t) { return new Paragraph({ spacing: { line: 312, after: 120 }, indent: { firstLine: 480 }, children: [new TextRun({ text: t, size: 24, font: {eastAsia:"SimSun"} })] }); }
function bul(t) { return new Paragraph({ spacing: { line: 312, after: 60 }, indent: { left: 600 }, children: [new TextRun({ text: "· " + t, size: 24, font: {eastAsia:"SimSun"} })] }); }
function tip(t) { return new Paragraph({ spacing: { line: 312, after: 80, before: 80 }, indent: { left: 360 }, border: { left: { style: BorderStyle.SINGLE, size: 6, color: P.acc, space: 8 } }, children: [new TextRun({ text: t, size: 22, color: "8B4513", font: {eastAsia:"Microsoft YaHei"} })] }); }
function demo(label, text) {
  return [
    new Paragraph({ spacing: { before: 160, after: 80 }, children: [new TextRun({ text: "▼ 实战演示：" + label, size: 24, bold: true, color: P.acc, font: {eastAsia:"SimHei"} })] }),
    new Paragraph({ spacing: { after: 120 }, indent: { left: 360, right: 200 }, shading: { type: ShadingType.CLEAR, fill: "F5F2EC" }, children: [new TextRun({ text, size: 18, font: {eastAsia:"Microsoft YaHei", ascii:"Consolas"} })] }),
  ];
}

// ===== COVER =====
const cover = [
  new Paragraph({ spacing: { before: 3800 } }),
  new Paragraph({ indent: { left: 1200 }, spacing: { after: 600 }, border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: P.hdr, space: 10 } }, children: [new TextRun({ text: "INSTRUCTOR  GUIDE", size: 20, color: P.hdr, font: {ascii:"Calibri"}, characterSpacing: 50 })] }),
  new Paragraph({ indent: { left: 1200 }, spacing: { after: 200 }, children: [new TextRun({ text: "AI漫剧工业化制作", size: 80, bold: true, color: P.hdr, font: {eastAsia:"SimHei"} })] }),
  new Paragraph({ indent: { left: 1200 }, spacing: { after: 800 }, children: [new TextRun({ text: "讲师手册（完整教学内容 + 提示词演示）", size: 26, color: "666666", font: {eastAsia:"Microsoft YaHei"} })] }),
  new Paragraph({ indent: { left: 1400 }, spacing: { after: 60 }, border: { left: { style: BorderStyle.SINGLE, size: 8, color: P.acc, space: 12 } }, children: [new TextRun({ text: "课程A（新手入门）+ 课程B（经验者进阶）全模块详解", size: 24, color: "777777", font: {eastAsia:"Microsoft YaHei"} })] }),
  new Paragraph({ indent: { left: 1400 }, spacing: { after: 60 }, border: { left: { style: BorderStyle.SINGLE, size: 8, color: P.acc, space: 12 } }, children: [new TextRun({ text: "每个知识点均附带实际 Agent 输出的提示词演示", size: 24, color: "777777", font: {eastAsia:"Microsoft YaHei"} })] }),
  new Paragraph({ indent: { left: 1400 }, spacing: { after: 60 }, border: { left: { style: BorderStyle.SINGLE, size: 8, color: P.acc, space: 12 } }, children: [new TextRun({ text: "2026年", size: 24, color: "777777", font: {eastAsia:"Microsoft YaHei"} })] }),
  new Paragraph({ spacing: { before: 3800 } }),
  new Paragraph({ indent: { left: 1200, right: 800 }, border: { top: { style: BorderStyle.SINGLE, size: 2, color: P.hdr, space: 8 } }, spacing: { before: 200 }, children: [new TextRun({ text: "Comic Pipeline v4.3", size: 16, color: "AAAAAA" }), new TextRun({ text: "                                                      " }), new TextRun({ text: "AI-COMIC-TG-002", size: 16, color: "AAAAAA" })] }),
];

const R = [];

// ========================================
// 第一部分：课程A
// ========================================
R.push(h1("第一部分：课程A 教学内容（新手入门）"));

// A1
R.push(h2("模块 A1：开营——认识 AI 漫剧"));
R.push(para("本模块是学员接触 AI 漫剧的第一扇门。目标是让学员在 30 分钟内建立对 AI 漫剧的完整认知框架，并理解其与传统动画和真人短剧的本质区别。"));
R.push(h3("1. 什么是 AI 漫剧"));
R.push(para("AI 漫剧是利用大语言模型（LLM）和 AI 图像/视频生成模型（Seedance、即梦、可灵等）联合制作的短篇动漫视频。与传统动画不同，AI 漫剧不需要手绘逐帧，而是通过文字描述（Prompt）驱动 AI 模型直接生成画面和动态效果。"));
R.push(para("核心特征：时长 50-90 秒/集、CG国漫风格为主、单线叙事、高密度情绪节奏。一个 4-Agent 管线可以在 2-4 小时内完成从故事构思到最终视频输出的全流程。"));
R.push(h3("2. AI 漫剧 vs 传统动画"));
R.push(tbl([["对比维度",30],["传统动画",35],["AI 漫剧",35]],[
  ["制作周期","单集数周至数月","单集 2-4 小时"],
  ["成本","数十万至百万级","数十至数百元 Token 费用"],
  ["人力","团队 10-50 人","1 人 + AI"],
  ["修改成本","极高，需返工","极低，改 Prompt 重新生成"],
  ["风格一致性","人工把控，稳定","需6层锚点+Hex色值锁死"],
  ["适用场景","大 IP 改编、院线","短视频平台、快速验证"],
]));
R.push(tip("实操要点：在无限画布中跑出第一条 5 秒视频作为热身。让学员亲眼看到从文字到视频的完整链路——这一步决定了他们对后续内容的信心。"));
R.push(para("一条 AI 漫剧的完整链路：想法 → 故事创作 Agent（写出 800-1200 字剧本）→ 导演 Agent（拆分为 12-20 个镜头）→ 美术 Agent（生成角色/场景/道具图）→ 分镜 Agent（编写 Seedance 视频提示词）→ 无限画布节点串联 → 最终视频输出。"));

// A2
R.push(h2("模块 A2：无限画布入门"));
R.push(para("无限画布是学员的「操作台」，所有 AI 模型调用、资产管理和视频生成都在这里完成。"));
R.push(h3("1. 节点式画布操作"));
R.push(para("采用节点式（Node-based）设计，每个功能模块是一个节点，节点之间通过连线传递数据。核心操作：拖拽添加节点、连线建立数据流、右键配置参数、双击预览输出。"));
R.push(h3("2. 模型市场"));
R.push(para("画布内置模型市场，包含 LLM（DeepSeek、GPT-4o 等）、图像生成模型（Flux、Midjourney）、视频生成模型（Seedance 2.0）。"));
R.push(h3("3. Seedance 视频生成原理"));
R.push(para("Seedance 是图生视频（I2V）模型。输入一张或多张参考图 + 文字提示词，输出 4-15 秒的动态视频。核心理念：首帧决定一切。"));
R.push(...demo("学员首个5秒视频 Prompt 示例","CG国漫风格。一个江湖侠客站在竹林中，风吹动他的衣袍和长发。\n画面缓慢推进（slow dolly-in），阳光从竹叶缝隙洒下，光影斑驳。\n(best quality, masterpiece, 8k, high detailed:1.2), CG国漫。"));
R.push(tip("实操要点：学员在画布中搭建「文本输入 → LLM 生成提示词 → Seedance 生视频」的最小节点链，跑出第一条 5 秒视频。"));

// A3
R.push(h2("模块 A3：4-Agent 管线概览"));
R.push(para("四个 Agent 依次协作，将「一个想法」变成「一条视频」。"));
R.push(tbl([["Agent",15],["职责",35],["核心产出",50]],[
  ["Agent1 故事创作","根据选题生成 800-1200 字剧本","小说正文+角色ID+场景ID+章末快照"],
  ["Agent2 导演漫改","将小说拆分为 12-20 个独立镜头","P编号分场剧本+演员表+场景表+JSON"],
  ["Agent3 美术资产","生成角色定妆/场景/道具/台词本","@图片资产库+定妆方案+音色库+SRT"],
  ["Agent4 分镜生成","组装为 Seedance 视频提示词","素材对应表+Seedance提示词+操作指南"],
]));
R.push(...demo("管线全链路示例（以「食为天」为例）","Agent1 产出: 第1章「铁锅里的金丹」1050字小说\n→ Agent2 产出: 拆为P01-P16共16个镜头，总时长65s\n→ Agent3 产出: @图片1-24(角色/场景/道具)+SRT台词本\n→ Agent4 产出: 16条Seedance提示词，每条含15+标签\n→ 无限画布串联各节点 → 最终60秒CG国漫视频"));
R.push(bul("P 编号：每个镜头的唯一标识，如 P01、P04_A。"));
R.push(bul("@图片：资产库中每张图像的唯一编号。"));
R.push(bul("场景 ID / 角色 ID：全局唯一标识，跨章复用不重置。"));

// A4
R.push(h2("模块 A4：Agent 1——故事创作"));
R.push(para("Agent 1 是整个管线的起点。好的故事让后续所有环节事半功倍。"));
R.push(h3("1. 选题与蓝图"));
R.push(para("首次交互输出 5-7 个热门题材选项。蓝图包含：爆款书名（≤10字+热词）、主角设定、一句话梗概（≤20字）、全篇 6 段 20 章结构。"));
R.push(h3("2. 封面写作"));
R.push(para("每章 800-1200 字。第一句必须用动作动词或心理冲突标记词切入。三天坑：①铺背景讲世界观 ②一群人开会 ③慢悠悠写景。"));
R.push(h3("3. 信息差三型"));
R.push(para("中段悬疑虐心期必须选用至少一种：观众先知型（期待打脸）、观众焦急型（替主角担心）、观众上帝型（期待真相大白）。"));
R.push(...demo("Agent1 实际输出示例（故事蓝图摘要）","📖 故事蓝图：《食为天》\n书名：主《食为天》/ 备选《御膳房最后一个厨子》\n主角：姜禾，25岁女，前御膳房首席→边城食堂老板\n一句话梗概：御厨被贬边城，一锅汤治好了金丹裂痕。\n全篇20章：开篇引爆(1-3)→递进爽点一(4-7)→递进爽点二(8-12)\n→递进爽点三(13-17)→终极高潮(18-19)→收尾钩子(20)\n\n第1章正文开头(轨A·动作切入):\n「姜禾被押到铁炉堡城门口的时候，天上正下着灵矿粉尘和\n煤灰混合的脏雪。押送她的修士解了她手上的禁灵锁，丢下\n一句好自为之，御剑飞走了。」"));

// A5
R.push(h2("模块 A5：Agent 2——导演漫改"));
R.push(para("Agent 2 将小说文本转化为可执行的拍摄台本。核心任务是把连续叙事切分为独立镜头。"));
R.push(h3("场景切割"));
R.push(para("每个场景 = 一个连续时间 + 一个连续地点 + 一个连续镜头。每场 4-15s，每章 12-20 场，总时长 50-90s。"));
R.push(h3("核心产出"));
R.push(tbl([["产出",30],["格式",70]],[
  ["P编号分场剧本","P01、P02_A... 每场含时长/重要性/场景/人物/朝向/灯光/音效"],
  ["演员表","演员名+年龄+阵营+首次出场+外观关键词(≥3项)"],
  ["场景列表","场景名+时间+光线/色调+氛围关键词"],
  ["JSON元数据","角色ID+场景ID+P编号+总时长+props数组"],
]));
R.push(...demo("Agent2 实际输出示例（P编号分场剧本片段）","**P01 铁锅与脏雪**\n时长建议: 5.0s | 重要性: main\n场景: 铁炉堡·城门口 | 人物: 姜禾 | 朝向: 3/4正面朝右\n灯光方案: key:右上方30°·硬光·冷7000K + fill:左侧·漫射·中5500K\n画面描述: 姜禾站在灰黄脏雪中，右手虎口烫伤旧疤在北风中\n隐隐发白，肩上扛着一口黑铁锅。[cite:1]\n\n**P02 矿工苏九**\n时长建议: 4.0s | 重要性: main\n场景: 铁炉堡·城门口 | 人物: 姜禾、苏九\n音效: 苏九蹲下时短褐布料摩擦声 + 寒风呼啸"));

// A6
R.push(h2("模块 A6：Agent 3——美术资产（上）"));
R.push(para("Agent 3 是管线的视觉工厂，负责生成角色、场景、道具的所有图像资产。"));
R.push(h3("1. S1 演员定妆档案"));
R.push(para("S 级主角 150-200 字外观描述，包含脸型骨骼、五官、发型、体型、皮肤、识别标记、服装、配件。禁止抽象气质词，所有维度给出确定值。"));
R.push(h3("2. S2a 定妆主图"));
R.push(para("单人全身站立正面，灰色渐变背景，三点布光（Key+Fill+Rim），表情中性。这是 I2V 参考底图，面部必须完整可识别。"));
R.push(h3("3. S2b 辅视图组"));
R.push(para("正视图+侧视图+背视图+面部特写，四图水平等距排列。正侧视必须完整全身，严禁截断腿部或压缩身高。"));
R.push(h3("4. 6 层角色锚点"));
R.push(tbl([["层级",25],["内容",75]],[
  ["骨相层","脸型(国字/瓜子/圆/方)+下颌线+颧骨"],
  ["五官层","眼型+鼻型+唇型+眉型"],
  ["辨识标记层","疤痕/痣/纹身的位置+形状(最强锚点)"],
  ["Hex色值层","虹膜/发色/肤色/唇色精确Hex(内部字典，不生图)"],
  ["皮肤纹理层","光滑/粗糙/瓷器/风霜"],
  ["发型锚点层","发色+长度+纹理+发际线形态"],
]));
R.push(...demo("Agent3 S2a 实际输出示例（角色定妆主图提示词）","CG国漫风格角色设定图。\n灰色渐变背景（中灰向浅灰自然过渡，无纯白）。\nKey light 左上方45°·柔光·中性5500K。\nFill light 右侧·柔光·2:1 ratio（面部完整可见）。\nRim light 后方偏上·冷光7000K（仅勾勒头发和肩部轮廓）。\n\n单人全身站立正面（角色从头到脚完整入画居画面中央，\n目光平视镜头），自然站立双臂自然下垂，表情警觉坚毅。\n\n外观描述：25岁女子，杏眼明亮，国字脸下颌线方正，\n高挺鼻梁，薄唇紧抿。墨黑长发及腰笔直垂坠（#1A0A00），\n发际线直角型额角碎发稀疏。暖麦色皮肤（#D4A574）微带\n风霜质感。右手虎口3cm斜向烫伤旧疤。靛蓝粗布围裙系于\n腰间，内衬灰色棉袍磨边。\n\n16:9比例，8K超高清，极致细节。\nNegative Prompt: 变形、不对称肢体、模糊、扭曲、夸张表情、\n  flat lighting, overexposed, pure white background"));
R.push(tip("致命翻车：把白底定妆照放进视频首帧。定妆照只是资产档案，不是视频底图——I2V 看到白底会输出白底悬空人物。"));

// A7
R.push(h2("模块 A7：Agent 3——美术资产（下）"));
R.push(para("本模块覆盖场景单图、道具库和 SRT 台词本。"));
R.push(h3("1. S3 场景单图"));
R.push(para("每个场景生成 1-3 张独立单图。重要场景至少 3 张。每张图标注光学方案三要素（Key+Fill+Ambient）和色彩基调。废除宫格图策略——AI 无法在单次 Prompt 控制多个格子的不同视角。"));
R.push(...demo("Agent3 S3 实际输出示例（场景单图提示词）","CG国漫风格场景设定图。\nShot on ARRI Alexa 65，Medium format deep focus。\n\n光学方案：key:右上方30°·硬光·冷7000K |\n  fill:左侧·漫射·中5500K | ambient:冷7000K\n色彩基调：desaturated-cold, high-contrast, natural\n材质重点：地面·粗粝石板·粗糙度0.8 +\n  铁栅栏·氧化铸铁·低反射率\n大气：dust-particles, light, backlit-glowing\n  (god-rays-through-iron-bars)\n\n铁炉堡城门口冬日傍晚——灰黄脏雪覆盖石板地面，城墙裂缝\n中斜斜射入冷白体积光，在脏雪上切出冷暖光影。远处矿坑\n正升起灵矿粉尘。\n\n16:9，8K超高清，极致细节。\nNegative Prompt: 角色人物入镜、剪影、面部、人体"));
R.push(h3("2. S4 道具库"));
R.push(para("道具按尺寸分为 S/M/L 三级。S 级（≤50cm）4视图+手掌参照。M 级（50cm-2m）4视图+灰色素体穿戴示意。L 级（>2m）单张45度全景+独立补充视图+成年人剪影参照。外观描述禁止抽象物理数字。"));
R.push(...demo("Agent3 S4 实际输出示例（L级大型道具提示词）","⚠️ 生图注意事项：主图为单张16:9 45度角全景。\n  画面中放置成年人剪影紧贴载具站立——\n  载具约为剪影的2.5倍高度，人只到车轮毂上方。\n\n生图提示词：\nCG国漫风格道具设定图。\n通用无特征中性工业背景（纯灰渐变，无具体地点）。\n单张45度角全景展示载具全貌。\n外观：六轮重型火星矿车，深灰哑光装甲外壳布满战斗刮痕，\n车头方形厚重防撞梁，六只巨型轮胎胎纹深刻，驾驶舱透明\n防爆玻璃有细微划痕，货舱开放式钢架结构，侧面褪色矿队\n编号徽章。驾驶舱门微开可见全息仪表盘，货舱液压升降架。\n16:9，8K超高清，极致工业细节，三维渲染质感。\nNegative Prompt: 变形、透视错误、白色背景、studio lighting、\n  宫格、多图拼接、分镜、多视图、split screen、grid layout"));
R.push(h3("3. S6 SRT 台词本"));
R.push(para("SRT 将剧本中的台词和动作转换为时间轴格式。纯文本供人工审阅，标准 SRT 文件由 Python 脚本从 JSON 一键生成。"));
R.push(...demo("Agent3 S6 实际输出示例（SRT+S6 JSON）","纯文本SRT(人工审阅):\n1\n00:00:00,000 --> 00:00:04,000\n△ 姜禾站在灰黄脏雪中，右手虎口旧疤在北风中发白\n\n2\n00:00:04,000 --> 00:00:08,000\n苏九(好奇)：新来的？看你像被贬的。犯了什么事？\n\n3\n00:00:08,000 --> 00:00:12,500\n姜禾(平静)：给皇帝做了一道菜。\n\nS6 JSON(机读·供srt_generator.py生成最终文件):\n{\"srt\":{\"chapter\":1,\"entries\":[\n {\"p\":\"P01\",\"start_ms\":0,\"end_ms\":4000,\"type\":\"action\",\n  \"content\":\"姜禾站在灰黄脏雪中，右手虎口旧疤在北风中发白\"},\n {\"p\":\"P01\",\"start_ms\":4000,\"end_ms\":8000,\"type\":\"dialogue\",\n  \"character\":\"苏九\",\"line\":\"新来的？看你像被贬的。犯了什么事？\",\n  \"tone\":\"好奇\"}\n]}}"));

// A8
R.push(h2("模块 A8：Agent 4——分镜师"));
R.push(para("Agent 4 是管线最后一环，将导演的分场剧本和美术的资产库翻译为 Seedance 视频提示词。"));
R.push(h3("1. 素材对应表"));
R.push(para("在生成提示词前，先输出素材速查表，列出所有 @编号 资产及视觉关键词。道具必须含尺寸参照，生物必须含体量参照。"));
R.push(h3("2. Seedance 提示词结构"));
R.push(para("每条提示词包含 16 个标签：Style、Format、Film Stock、Color Grade、Duration、Optics、Camera、Material、Atmosphere、Vignette、Bokeh、Film Grain、Director/DP、Subject、Narrative、Intent、Mood、Dialogue Cue、Audio SFX。Camera 标签优先使用英文 Token。"));
R.push(h3("3. 首帧门禁"));
R.push(para("P01 必须指定场景全景图。持械镜头用多 @图片 融合写法。"));
R.push(...demo("Agent4 实际输出示例（P01完整Seedance提示词）","## P01 铁锅与脏雪 (5s)\n\n【📋 分镜详情】\nStyle: (CG国漫 cinematic lighting:1.2), CG国漫电影级光影\nFormat: Super-35, 2.35:1, ARRI Alexa 65\nFilm Stock: Kodak Vision3 500T 5219, tungsten\nColor Grade: desaturated-cold, high-contrast, natural\nDuration: 5s\n\n[0-5s] Shot1: 初见铁炉堡(全景·缓推)\nOptics: spherical, 35mm, none\nCamera: slow-dolly-in, wide-to-medium shot, f/8 to f/4\nMaterial: stone, rough-matte, semi-reflective, weathered\nAtmosphere: snow-dust-particles, medium, backlit\nVignette: subtle, smooth-fade\nBokeh: none\nFilm Grain: light\nDirector/DP: Denis Villeneuve, Roger Deakins\nSubject: @图片1姜禾 站在灰黄脏雪中，右手虎口旧疤在北风中\n  隐现，肩上扛一口黑铁锅——锅底三道裂纹边缘泛暗红氧化光泽\nNarrative: setup | Intent: 初临废城孤绝感 | Mood: desolation\nDialogue Cue: (无台词，纯氛围建立)\nAudio SFX: howling-wind, falling-snow, iron-gate-creak\n\n【🎬 Seedance直接输入】\nShot on ARRI Alexa 65, 2.35:1 anamorphic widescreen.\nKodak Vision3 500T film stock with light film grain.\nDesaturated-cold color grading, high contrast.\nDenis Villeneuve style.\n(best quality,masterpiece,8k,high detailed:1.2,cinematic lighting),CG国漫。\n首帧为 @图片6铁炉堡城门口场景全景图。\n@图片1姜禾站在灰黄脏雪中——右手虎口旧疤在北风中隐隐发白，\n肩上扛着一口黑铁锅。spherical 35mm镜头从全景缓慢推近至中景，\n体积光从城墙裂缝斜射，在脏雪上切出冷暖光影。粗粝石板地面\n覆盖灰黄积雪，细微雪尘在逆光中如金粉悬浮。subtle vignette\n压暗画面四角。寒风吹过铁栅栏发出低沉的金属呜咽声。"));

// ========================================
// 第二部分：课程B
// ========================================
R.push(h1("第二部分：课程B 教学内容（经验者进阶）"));
R.push(para("课程 B 面向已有基础产出经验的学员。以下内容假设学员已掌握课程 A 的全部知识。"));

// B1
R.push(h2("模块 B1：管线架构拆解"));
R.push(para("4-Agent 管线的强大在于 Agent 之间的精确依赖关系。理解这种关系是进阶使用的关键。"));
R.push(h3("字段级依赖表"));
R.push(tbl([["改动字段",30],["影响 Agent3",35],["影响 Agent4",35]],[
  ["Agent2 人物拆分规则","S6 SRT 行数自动增减","提示词条数自动增减"],
  ["Agent2 转场类型","SRT 不受影响","起始帧引用末帧是黑屏，自动处理"],
  ["Agent3 SRT 时长规则","—","时长基于 SRT 重算，节奏同步变化"],
  ["Agent3 @编号分配","—","素材对应表+@引用规则依赖编号连续性"],
]));
R.push(h3("JSON 双轨制"));
R.push(para("所有 Agent 产出同时包含 JSON block（机读优先）和 Markdown（人类阅读+降级）。下游优先解析 JSON，失败回退到 Markdown 提取。这是管线容错的核心设计。"));
R.push(...demo("Agent2 JSON示例（scenes_metadata.json）","{\n  \"chapter\": 1,\n  \"characters\": [\n    {\"character_id\":\"CHAR_01_姜禾\",\"name\":\"姜禾\",\"camp\":\"主角团\"},\n    {\"character_id\":\"CHAR_02_苏九\",\"name\":\"苏九\",\"camp\":\"中立配角\"}\n  ],\n  \"scenes\": [\n    {\"scene_id\":\"SCENE_01_铁炉堡城门口\",\"name\":\"铁炉堡·城门口\",\n     \"lighting\":\"灰黄脏雪+城缝冷白体积光\"}\n  ],\n  \"props\": [\n    {\"prop_id\":\"PROP_01_黑铁锅\",\"name\":\"黑铁锅\",\n     \"owner_id\":\"CHAR_01_姜禾\",\"appears_in\":[\"P01\",\"P06\"]}\n  ],\n  \"p_numbers\":[\"P01\",\"P02\",\"P03\",\"P04\",\"P05\",\"P06\",\"P07\",\"P08\",\n    \"P09\",\"P10\",\"P11\",\"P12\",\"P13\",\"P14\",\"P15\",\"P16\"],\n  \"total_duration_s\": 65\n}"));

// B2
R.push(h2("模块 B2：比例控制全链路"));
R.push(para("AI 生图/生视频模型无法理解物理尺度数字。整个管线的比例控制策略是：用参照物和关系描述暗示比例。"));
R.push(h3("Gemini 三步法"));
R.push(tbl([["步骤",20],["策略",40],["示例",40]],[
  ["第一步","找参照物(人体)","小道具用手掌，大道具用全身/视线"],
  ["第二步","底图焊死物理接触","第一帧就展示角色握着道具"],
  ["第三步","视频锁定相对比例","maintaining consistent proportional scale"],
]));
R.push(h3("道具 S/M/L 三级"));
R.push(tbl([["等级",15],["范围",25],["参照物",30],["生图策略",30]],[
  ["S级","≤50cm","成年人手掌","4视图+手掌参照"],
  ["M级","50cm-2m","灰色素体","4视图+穿戴状态示意"],
  ["L级",">2m","成年人剪影","单张45°全景+独立补充视图"],
]));
R.push(h3("生物体量控制"));
R.push(para("怪物体量尺度三要素：数值+单位+形态类型。巨型生物用环境碾压参照，微型生物用身体部位参照。视频 Subject 行人+生物同框时必须写入相对体量描述。"));
R.push(...demo("比例控制·视频提示词示例（角色+匕首/角色+怪兽/角色+机甲）","【S级道具·匕首持械镜头】\nSubject: @图片1陆沉 反手紧握 @图片17暗杀匕首，\n  短刃在虎口间仅露刃尖，压低身形贴墙移动。\n→ Seedance末尾: ...匕首相对于手部保持固定比例，\n  maintaining a consistent proportional scale\n  relative to the hand, motion control.\n\n【L级道具·机甲与角色同框】\nSubject: @图片19机甲 庞大机身从矿坑驶出——\n  @图片1角色 站在车旁只到车轮毂高度，仰头望驾驶舱。\n\n【巨型生物·怪兽跃出】\nSubject: @图片2砂钻蝎 庞大身躯从 @图片7火星赤色荒原的\n  沙尘中猛烈跃出——站立姿态下八条钻头节肢展开，\n  甲壳顶端遮蔽半边天光，高过废墟断壁。\n→ Seedance末尾: ...maintaining consistent body proportions\n  relative to the background ruins as it moves."));

// B3
R.push(h2("模块 B3：SRT 子节拍拆分"));
R.push(para("纯动作/氛围场景的 SRT 拆分是管线中极易被忽视但后果严重的深水区。"));
R.push(h3("问题：时长黑洞"));
R.push(para("美术指导 §7.4：无台词场景的动作行时长强制 100% 继承导演建议值。12 秒暴雨行走如果只有一行 △暴雨行走 占满全程，下游只能生成一条 12 秒提示词——I2V 产出单一静止慢动作，节奏彻底崩坏。"));
R.push(h3("解决方案：子节拍拆分"));
R.push(para("单行动作行上限 4s。拆分依据是导演动作描述的自然断点（逗号/句号/动词转折处），严禁机械平均切 3s。"));
R.push(...demo("SRT子节拍拆分·改前 vs 改后","改前(时长黑洞):\n1\n00:01:00,000 --> 00:01:12,000\n△ 暴雨行走\n→ 12秒只一行！分镜师只能生成1条提示词\n\n改后(子节拍拆分):\n1\n00:01:00,000 --> 00:01:04,000\n△ 暴雨行走·低头起步\n2\n00:01:04,000 --> 00:01:07,500\n△ 暴雨行走·绕过水洼\n3\n00:01:07,500 --> 00:01:12,000\n△ 暴雨行走·远景渐远\n→ 总和=12s不变，但每行≤4s，分镜师可生成3条独立提示词"));

// B4
R.push(h2("模块 B4：跨章处理"));
R.push(para("多章连续跑管线时，资产编号、映射表和 JSON 的跨章管理是工业化落地的核心难点。"));
R.push(h3("核心规则"));
R.push(bul("@编号 跨章持续递增不重置。旧场景保留原 @图片N 不变，不重分配。"));
R.push(bul("映射表必须是全量增量表：本章新增 + 前章全部已有（标注 reused:true, from_chapter:N）。"));
R.push(bul("音频编号绑定角色 ID（1:1），不受外观更新影响。CHAR_01 全局唯一绑定 @音频1。"));
R.push(bul("S0 兜底资产改为条件触发——按题材匹配，分镜师反馈缺失时才生成。"));
R.push(bul("导演 JSON 新增 props 数组，道具主键由导演预分配，美术指导沿用。"));
R.push(...demo("跨章全量增量映射表JSON示例(第2章)","{\n  \"@image_mapping\": [\n    // 前章已有资产(保留原编号+标注沿用)\n    {\"@image\":\"@图片1\",\"type\":\"actor\",\"id\":\"CHAR_01_姜禾\",\n     \"reused\":true,\"from_chapter\":1},\n    {\"@image\":\"@图片6\",\"type\":\"scene\",\"id\":\"SCENE_01_铁炉堡城门口\",\n     \"reused\":true,\"from_chapter\":1},\n    // 本章新增资产(续接编号)\n    {\"@image\":\"@图片25\",\"type\":\"actor\",\"id\":\"CHAR_03_林若雪\",\n     \"reused\":false},\n    {\"@image\":\"@图片28\",\"type\":\"scene\",\"id\":\"SCENE_03_暗鸦森林\",\n     \"reused\":false}\n  ]\n}\n\n// 支持一对多: 角色有战损外观变体\n{\"id\":\"CHAR_01_陆沉\",\"audio_no\":\"@音频1\",\n \"img_nos\":[\"@图片1\",\"@图片2\",\"@图片15\"],\n \"current_img_no\":\"@图片15\",\"status\":\"inherited\"}"));

// B5
R.push(h2("模块 B5：Python 校验与调试"));
R.push(para("管线配备 56 条 Python 校验规则，分四层架构。"));
R.push(tbl([["层级",15],["范围",45],["典型检查",40]],[
  ["第一层","单文件结构(22条)","P编号连续性、总时长区间、@图片连续性"],
  ["第二层","跨文件交叉(20条)","演员数量对齐、场景名匹配、ID传播"],
  ["第三层","传播链致命(4条)","外观损失链、P编号断层、音频错配"],
  ["第四层","SRT专项(10条)","帧率合规、时间单调性、对话拆分"],
]));
R.push(...demo("Python校验命令行演示","# 四文件模式(推荐)\npython validate_pipeline.py art.txt cine.txt director.txt story.txt\n\n# 输出示例:\n✅ 23 外观描述禁止抽象数字          未发现吨/km/h/倍数\n✅ 24 L级道具Neg防宫格              Neg Prompt含split screen\n✅ 35 道具视觉关键词尺寸参照         全部4条道具含尺寸参照\n✅ 36 生物体量尺度完整               全部2个生物三要素齐全\n⚠️ 14 链B:P编号跳跃              轻微警告\n\n结果：46 ✅ / 6 ❌ / 13 ⚠️ | 通过率：70.8%"));

// B6
R.push(h2("模块 B6：不确定词 Few-Shot 约束"));
R.push(para("LLM 在长文本中极其擅长使用模糊过渡词。单纯靠末尾自检会导致 Agent 陷入死循环。"));
R.push(h3("解决方案"));
R.push(para("在 S1 定妆模板中嵌入正反例对比，让 LLM 在源头就锁定确定值。"));
R.push(...demo("Few-Shot正反例对比","❌ 反面示例(含不确定词·禁止):\n| 发型 | 可能是黑色长发，大概及腰，发质似乎偏直 |\n| 体型 | 身高大约175cm左右，体型可能偏瘦 |\n\n✅ 正面示例(确定表述):\n| 发型 | 墨黑长发及腰，发质笔直垂坠，鬓角碎发收于耳后 |\n| 体型 | 身高175cm，消瘦型，肩胛骨轮廓隐约可见 |\n\n严禁使用的词: 可能、或、大概、大约、左右、似乎、也许、差不多"));

// B7
R.push(h2("模块 B7：首帧门禁与持械合成"));
R.push(para("持械镜头是 I2V 管线中最容易翻车的场景类型。核心矛盾：美术道具图是白底单体，分镜师需要角色握道具的组合图。"));
R.push(h3("解决方案：多 @图片 融合"));
R.push(para("分镜师在 Seedance 提示词首句用多 @图片 混合描述，引导 I2V 模型自行合成两张参考图。"));
R.push(...demo("持械多图融合·完整Seedance提示词示例","以 @图片1陆沉(定妆主图) 为人物参考，\n将 @图片17暗杀匕首(道具资产图) 融合至其右手中——\n反手握持姿态，冷锻钢哑光刃面在昏暗走廊冷光下闪烁，\n短刃在虎口间仅露三寸寒芒。@图片1陆沉 压低身形贴墙移动，\n手掌完全包裹缠皮绳刀柄。\n\n匕首相对于手部保持固定比例，\nmaintaining a consistent proportional scale\nrelative to the hand, motion control,\nrealistic metallic reflection.\n\n严禁单独以道具单体图 @图片17 为首帧。\n背景置于 @图片5北区监狱走廊场景中。"));

// B8
R.push(h2("模块 B8：6 层锚点与 Hex 色值"));
R.push(para("角色一致性是 AI 漫剧最大的技术挑战。6 层锚点从结构上解决跨场景角色「撞脸」问题。"));
R.push(h3("Hex 色值内部字典"));
R.push(para("Hex 色值不直接写入生图提示词（AI 不认 #2C1810），而是作为 Agent 的内部颜色字典。Agent 将 Hex 转为自然语言颜色词后再写入提示词。"));
R.push(...demo("Hex色值·Agent内部对照表示例","角色：陆沉\n| Hex色值锚点 | 虹膜:#2C1810 | 发色:#1A0A00 |\n              肤色:#D4A574 | 唇色:#8B4513 |\n\n→ Agent翻译后写入S2a提示词:\n  「虹膜呈深暖棕色(#2C1810→深暖棕)」\n  「墨黑发丝在光下泛暖调(#1A0A00→漆黑偏暖)」\n  「暖麦色皮肤(#D4A574→暖麦色)」\n  「自然棕唇色(#8B4513→自然棕)」\n\n→ 发际线细节: 直角型发际线，额角碎发稀疏，\n  右额有一道旧伤断发\n\n→ S2a Neg Prompt追加: avoid: 圆眼, 浅肤色, 长发, 娃娃脸"));

// B9
R.push(h2("模块 B9：Toonflow 矛盾方法论"));
R.push(para("Toonflow 的核心贡献是将故事矛盾强度量化，让 Agent 1 产出的故事天然具备爆款基因。"));
R.push(h3("矛盾四级阶梯"));
R.push(tbl([["级别",12],["定义",40],["判定",48]],[
  ["1.基本矛盾","欲望 vs 阻碍成立但太弱","平淡"],
  ["2.强化矛盾","强欲望+强阻碍+不可调和+二选一","及格"],
  ["3.高级矛盾","两个好人因不同选择走向不同命运","优秀"],
  ["4.矛盾升级","行动招致不可回头的更严重后果","爆款"],
]));
R.push(h3("三天坑 + 信息差三型"));
R.push(para("每章开头自检：①铺背景 ②开会 ③写景。中段强制选用信息差三型之一（观众先知/焦急/上帝）。"));
R.push(...demo("信息差三型·在Agent1正文中的体现示例","【观众先知型】主角隐藏实力，扮猪吃虎：\n「姜禾把铁锅往肩上一扛。『给皇帝做了一道菜。』\n 苏九愣了一秒——他不知道，这道菜比御医的药管用。」\n→ 观众知道姜禾是御厨，苏九不知道→期待打脸\n\n【观众焦急型】有人要害主角，主角蒙在鼓里：\n「苏九不知道，城门口那个穿短褐的矿工背后，\n 长老会的眼线已经把他昨天的事报了上去。」\n→ 观众知道危险在靠近，苏九不知道→替主角担心\n\n【观众上帝型】人物关系未揭示：\n「林若雪摘下斗笠的瞬间，姜禾的瞳孔猛地一缩——\n 这张脸，和二十年前御膳房火灾中失踪的师妹一模一样。」\n→ 观众知道她们有关联，两人自己不知道→期待真相大白"));

// ========================================
// 附录
// ========================================
R.push(h1("附录：20 条常见翻车详解"));
R.push(para("每条含原因分析+修复方案。"));

const pitfalls = [
  ["1","蓝图没定死就开写","急于产出跳过蓝图确认→写到第5章发现主线矛盾模糊无法挽回","蓝图输出后等用户回复「继续」再进入逐章写作"],
  ["2","P编号<12或>20","导演对小说节奏判断偏差","输出后检查P编号数量，区间外立即修正"],
  ["3","单场时长>15s","未做单场时长上限控制→I2V无法生成连贯视频","超15s必须拆分，找自然断点切新场"],
  ["4","白底定妆照当视频首帧","混淆资产档案图和视频参考底图","首帧用场景图，定妆照仅做@图片特征参考"],
  ["5","道具图没放参照物","生图提示词忘记加入尺寸锚定","S级放手掌、M级放素体、L级放剪影"],
  ["6","L级道具用4面板","载具用了S/M级模板→一根剪影锚定不了4个视图","仅生成单张全景主图，补充视图独立生成"],
  ["7","外观写了抽象数字","用「3.8吨」「时速80km」→AI画数字","改用视觉化语言(重型/庞大/碾过碎石)"],
  ["8","不确定词导致死循环","S1用「可能/大概/左右」→Agent反复自我重写","模板嵌入Few-Shot正反例，源头锁定确定值"],
  ["9","S0兜底盲目预生成","每次预生成6张古风图→现代/科幻剧本全废","条件触发：分镜师反馈缺失时按题材匹配生成"],
  ["10","SRT纯动作1行吞","12s暴雨行走只有1行→单一慢镜拖沓","子节拍拆分≤4s，总和=导演时长"],
  ["11","跨章映射表丢旧资产","第2章只写增量→分镜师查不到旧场景@图片","全量增量表=新增+前章全部(标注reused)"],
  ["12","外观更新→音频跟着变","角色战损换新@图片→音频序列断裂","音频绑定角色ID(1:1)，不受外观更新影响"],
  ["13","P01没写首帧来源","忘记声明首帧→Seedance冷启动失败全黑","首句必须写「首帧为@图片X(场景全景图)」"],
  ["14","持械门禁卡死","道具白底单体+门禁要求已握持→无合规底图","多@图片融合+持握姿态描述引导I2V合成"],
  ["15","Subject没写体量参照","只有@引用无比例关系→匕首变长剑","写入关系描述(仅露刃尖/高过断壁/在掌心爬行)"],
  ["16","跨章JSON遗漏旧场景","只列新增场景→美术指导校验失败","所有出场场景(含旧)必须列入"],
  ["17","JSON无props数组","只有文本备注无结构数据→无法跨Agent对齐","新增结构化props数组(prop_id/name/owner_id)"],
  ["18","改上游没查下游","修改字段不检查消费方→字段断裂","铁律一：改前必查谁产出谁消费"],
  ["19","改动前没出清单","发现问题急于动手→改完连锁崩","铁律二三：出五列表格+等用户确认"],
  ["20","没跑Python校验","跳过校验直接交付→隐藏bug带到视频阶段","必须运行validate_pipeline.py+全部通过"],
];

for (const p of pitfalls) {
  R.push(h2(p[0] + ". " + p[1]));
  R.push(para("原因：" + p[2]));
  R.push(para("修复：" + p[3]));
}

// ===== BUILD =====
const hdr = new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "AI漫剧工业化制作·讲师手册", size: 18, color: "AAAAAA", font: {eastAsia:"Microsoft YaHei"} })] })] });
const ftr = new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: ["— ", PageNumber.CURRENT, " —"], size: 18, color: "AAAAAA" })] })] });

const doc = new Document({
  styles: {
    default: { document: { run: { font: { eastAsia: "SimSun", ascii: "Times New Roman" } } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", run: { size: 32, bold: true, color: P.hdr, font: { eastAsia: "SimHei" } }, paragraph: { spacing: { before: 480, after: 240, line: 312 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", run: { size: 28, bold: true, color: P.hdr, font: { eastAsia: "SimHei" } }, paragraph: { spacing: { before: 360, after: 180, line: 312 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", run: { size: 26, bold: true, color: P.hdr, font: { eastAsia: "SimHei" } }, paragraph: { spacing: { before: 240, after: 120, line: 312 }, outlineLevel: 2 } },
    ],
  },
  sections: [
    { properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 0, bottom: 0, left: 0, right: 0 } } }, children: cover },
    { properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1701, right: 1417 } } }, headers: { default: hdr }, footers: { default: ftr }, children: [
      new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { after: 300 }, children: [new TextRun({ text: "目录", size: 32, bold: true, color: P.hdr, font: {eastAsia:"SimHei"} })] }),
      new TableOfContents("TOC", { hyperlink: true, headingStyleRange: "1-3" }),
      new Paragraph({ children: [new PageBreak()] }),
    ]},
    { properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1701, right: 1417 }, pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL } } }, headers: { default: hdr }, footers: { default: ftr }, children: R },
  ],
});

(async () => {
  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync("讲师手册_AI漫剧工业化制作.docx", buffer);
  console.log("OK");
})();
