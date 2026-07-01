const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  PageBreak, Header, Footer, PageNumber, NumberFormat,
  AlignmentType, HeadingLevel, WidthType, BorderStyle, ShadingType,
  TableOfContents,
} = require("docx");
const fs = require("fs");

const NB = { style: BorderStyle.NONE, size: 0 };

function tCell(text, width, opts = {}) {
  return new TableCell({
    width: { size: String(width), type: WidthType.PERCENTAGE },
    shading: { type: ShadingType.CLEAR, fill: opts.fill || "FFFFFF" },
    children: [new Paragraph({
      alignment: opts.align || AlignmentType.LEFT,
      spacing: { before: 50, after: 50 },
      children: [new TextRun({ text, size: opts.bold ? 22 : 20, bold: !!opts.bold, color: opts.color || "000000", font: { eastAsia: opts.bold ? "SimHei" : "Microsoft YaHei" } })],
    })],
  });
}

function makeTable(headerCols, rows) {
  const headerFill = "0F4C5C", altFill = "F0EDE5";
  const tableRows = [];
  tableRows.push(new TableRow({
    tableHeader: true,
    children: headerCols.map(([txt, w]) => tCell(txt, w, { fill: headerFill, align: "center", bold: true, color: "FFFFFF" })),
  }));
  for (let i = 0; i < rows.length; i++) {
    tableRows.push(new TableRow({
      children: rows[i].map(([txt, w]) => tCell(txt, w, { fill: i % 2 === 0 ? "FFFFFF" : altFill })),
    }));
  }
  return new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, rows: tableRows });
}

function makeDayTitle(text) {
  return new Paragraph({ spacing: { before: 400, after: 200 }, children: [new TextRun({ text, size: 30, bold: true, color: "D35400", font: { eastAsia: "SimHei" } })] });
}
function makeH1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 500, after: 250 }, children: [new TextRun({ text, size: 32, bold: true, color: "0F4C5C", font: { eastAsia: "SimHei" } })] });
}
function makeNote(text) {
  return new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text, size: 24, color: "888888", font: { eastAsia: "Microsoft YaHei" } })] });
}
function makeP(text) {
  return new Paragraph({ spacing: { line: 312, after: 80 }, indent: { firstLine: 480 }, children: [new TextRun({ text, size: 24, font: { eastAsia: "SimSun" } })] });
}

// Build body content
const all = [];

// --- COVER ---
function buildCover() {
  return [
    new Paragraph({ spacing: { before: 3600 } }),
    new Paragraph({ indent: { left: 1200 }, spacing: { after: 600 }, border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: "0F4C5C", space: 10 } }, children: [new TextRun({ text: "A I   C O M I C   P R O D U C T I O N   W O R K S H O P", size: 20, color: "0F4C5C", font: { ascii: "Calibri" }, characterSpacing: 50 })] }),
    new Paragraph({ indent: { left: 1200 }, spacing: { after: 200 }, children: [new TextRun({ text: "AI漫剧工业化制作", size: 80, bold: true, color: "0F4C5C", font: { eastAsia: "SimHei" } })] }),
    new Paragraph({ indent: { left: 1200 }, spacing: { after: 800 }, children: [new TextRun({ text: "线下工作坊课程大纲（2天·双阶课程）", size: 26, color: "666666", font: { eastAsia: "Microsoft YaHei" } })] }),
    new Paragraph({ indent: { left: 1400 }, spacing: { after: 60 }, border: { left: { style: BorderStyle.SINGLE, size: 8, color: "D35400", space: 12 } }, children: [new TextRun({ text: "4-Agent管线 × 无限画布 × Seedance视频生成", size: 24, color: "777777", font: { eastAsia: "Microsoft YaHei" } })] }),
    new Paragraph({ indent: { left: 1400 }, spacing: { after: 60 }, border: { left: { style: BorderStyle.SINGLE, size: 8, color: "D35400", space: 12 } }, children: [new TextRun({ text: "2026年", size: 24, color: "777777", font: { eastAsia: "Microsoft YaHei" } })] }),
    new Paragraph({ spacing: { before: 4400 } }),
    new Paragraph({ indent: { left: 1200, right: 800 }, border: { top: { style: BorderStyle.SINGLE, size: 2, color: "0F4C5C", space: 8 } }, spacing: { before: 200 }, children: [new TextRun({ text: "Comic Pipeline v4.3", size: 16, color: "AAAAAA" }), new TextRun({ text: "                                                      " }), new TextRun({ text: "AI-COMIC-001", size: 16, color: "AAAAAA" })] }),
  ];
}

// ===== COURSE A =====
all.push(makeH1("课程 A：新手小白"));
all.push(makeNote("让你从零产出一条 60 秒漫剧。"));

// Day1 AM
all.push(makeDayTitle("■ Day 1 上午 · 认知篇（3h）"));
all.push(makeTable([["时间",15],["模块",20],["内容",65]],[
  ["0:30","开营","漫剧是什么？AI漫剧和传统动画的区别。一条漫剧是怎么从想法到视频的。"],
  ["1:00","无限画布入门","节点式画布操作、模型市场、Seedance视频生成原理。实操：画布里跑出第一条5秒视频。"],
  ["0:45","4-Agent管线概览","故事→导演→美术→分镜，每个Agent做什么、产出什么。核心概念：P编号、@图片、场景ID。"],
  ["0:45","Agent1深度","选题→蓝图→逐章写作。陷阱：蓝图没定死就开写。自检：书名热词、动机转变、情绪递进。"],
]));

// Day1 PM
all.push(makeDayTitle("■ Day 1 下午 · 实操篇（4h）"));
all.push(makeTable([["时间",15],["模块",20],["内容",65]],[
  ["1:00","Agent2导演","场景切割、P编号、时长控制、演员表/场景表。陷阱：场景切太碎或太粗（12-20场铁律）。"],
  ["1:00","Agent3美术（上）","演员定妆、S2生图。陷阱：白底定妆照不是视频首帧！"],
  ["1:00","Agent3美术（下）","场景单图、道具库、SRT台词本。陷阱：道具忘放参照物，AI比例失控。"],
  ["1:00","实战 Round1","用模板故事，从Agent1跑到Agent3，产出一套完整资产。"],
]));

// Day2 AM
all.push(makeDayTitle("■ Day 2 上午 · 出片篇（3h）"));
all.push(makeTable([["时间",15],["模块",20],["内容",65]],[
  ["1:00","Agent4分镜师","素材对应表、Seedance提示词结构、Camera/镜头/灯光标签。"],
  ["1:00","从资产到视频","无限画布里搭节点、@引用、末帧串联。陷阱：P01忘了写首帧来源。"],
  ["1:00","实战 Round2","把Day1下午的资产跑通Agent4，产出完整60秒漫剧视频。"],
]));

// Day2 PM
all.push(makeDayTitle("■ Day 2 下午 · 出师篇（4h）"));
all.push(makeTable([["时间",15],["模块",20],["内容",65]],[
  ["1:30","自由实战","学员用自己的创意（或讲师提供3个选题），完整跑一遍4-Agent管线。"],
  ["1:00","互评+讲师点评","每人展示成片，拆解常见翻车点。"],
  ["1:00","避坑20条","管线最常见的20个错误，每条配正反例。"],
  ["0:30","结营+作业","课后独立完成一条原创漫剧，提交评审。"],
]));

// ===== COURSE B =====
all.push(makeH1("课程 B：经验者进阶"));
all.push(makeNote("让跑量从「能用」变成「工业级」。"));

// Day1 AM
all.push(makeDayTitle("■ Day 1 上午 · 深水区（3h）"));
all.push(makeTable([["时间",15],["模块",20],["内容",65]],[
  ["0:30","破冰","每人2分钟：你做过多少条漫剧？最大的痛点？"],
  ["1:00","管线架构拆解","4-Agent的字段级依赖、JSON双轨制、校验体系。陷阱：改了Agent2的字段，Agent3&4崩了。"],
  ["1:00","比例控制全链路","道具S/M/L三级+怪物体量尺度+Gemini三步法。陷阱：生图有参照物，视频丢了比例。"],
  ["0:30","SRT子节拍拆分","无台词纯动作场景的时长黑洞。陷阱：12秒暴雨行走1行吞掉导致节奏崩。"],
]));

// Day1 PM
all.push(makeDayTitle("■ Day 1 下午 · 长剧集（4h）"));
all.push(makeTable([["时间",15],["模块",20],["内容",65]],[
  ["1:00","跨章处理","命名空间冲突、全量增量映射表、道具预分配、音频ID绑定。陷阱：第2章分镜师找不到第1章的场景@图片。"],
  ["1:00","兜底资产+条件触发","S0按题材匹配（仙侠/现代/科幻各一套），不再盲目预生成。陷阱：科幻剧预生了6张古风图。"],
  ["1:00","Python校验+调试","56条校验规则、传播链检测、SRT生成器。实操：跑一段有bug的管线，用校验报告定位。"],
  ["1:00","不确定词Few-Shot","可能/大概/左右怎么让AI死循环。正面模板vs反面模板的对比例子。"],
]));

// Day2 AM
all.push(makeDayTitle("■ Day 2 上午 · 极致质量（3h）"));
all.push(makeTable([["时间",15],["模块",20],["内容",65]],[
  ["1:00","首帧门禁+持械合成","怎么用多@图片融合让AI自己合成角色握剑画面。陷阱：门禁卡死导致找不到组合图。"],
  ["1:00","6层角色锚点","Hex色值内部字典、发际线细节、负面提示词。陷阱：两张图同一个角色肤色不一样。"],
  ["1:00","Toonflow矛盾方法论","矛盾四级阶梯+三天坑+信息差三型，让Agent1产出的故事天然具备爆款基因。"],
]));

// Day2 PM
all.push(makeDayTitle("■ Day 2 下午 · 工业化（4h）"));
all.push(makeTable([["时间",15],["模块",20],["内容",65]],[
  ["1:30","实战·多章管线","给一段3章剧本，跑完整跨章流程：增量映射表、外观更新、SRT独立时间轴。"],
  ["1:00","故障注入训练","故意制造5个常见故障，学员用校验报告定位并修复。"],
  ["1:00","圆桌讨论","你的管线还有什么痛点？我们现场改提示词、跑验证。"],
  ["0:30","结营","工业级漫剧管线验收标准+持续更新路线图。"],
]));

// ===== APPENDIX =====
all.push(makeH1("附录：20条常见翻车"));
all.push(makeNote("两套课程通用。"));
all.push(makeTable([["#",5],["阶段",12],["问题",48],["后果",35]],[
  ["1","故事","蓝图没定死就开写","后续章节崩盘"],
  ["2","导演","P编号少于12或多于20","节奏失控"],
  ["3","导演","单场时长大于15s","长镜头视频崩"],
  ["4","美术","定妆照用了白底→当成视频首帧","I2V输出白底悬空画面"],
  ["5","美术","道具图没放参照物","AI比例失控"],
  ["6","美术","L级道具用了4面板","一根剪影锚定不了4个视图"],
  ["7","美术","外观描述写了抽象数字（吨/km/h）","AI画出阿拉伯数字"],
  ["8","美术","不确定词（可能/大概）→后验死循环","Agent反复自我重写"],
  ["9","美术","S0兜底资产盲目预生成","科幻剧烧了古风图的Token"],
  ["10","美术","SRT纯动作场景1行吞掉12s","时长黑洞→单镜拖沓"],
  ["11","美术","跨章映射表只写增量不写旧资产","分镜师@引用查不到ID"],
  ["12","美术","外观更新→音频编号跟着变","音频序列断裂"],
  ["13","分镜","P01没写首帧@图片来源","冷启动失败"],
  ["14","分镜","持械镜头→门禁卡死","无组合底图"],
  ["15","分镜","Subject行人+物同框没写体量参照","匕首变长剑，怪兽变小狗"],
  ["16","导演","跨章JSON遗漏旧场景","美术指导校验失败"],
  ["17","导演","JSON没有结构化props数组","道具数量无法跨Agent对齐"],
  ["18","全部","改了上游没查下游依赖","字段断裂"],
  ["19","全部","改动前没出清单、没等确认","改完发现连锁崩"],
  ["20","全部","没跑Python校验就交付","隐藏错误带到视频阶段"],
]));

// ===== BUILD =====
const doc = new Document({
  sections: [
    {
      properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 0, bottom: 0, left: 0, right: 0 } } },
      children: buildCover(),
    },
    {
      properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1701, right: 1417 } } },
      headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "AI漫剧工业化制作·课程大纲", size: 18, color: "AAAAAA", font: { eastAsia: "Microsoft YaHei" } })] })] }) },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: ["- ", PageNumber.CURRENT, " -"], size: 18, color: "AAAAAA" })] })] }) },
      children: [
        new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { after: 300 }, children: [new TextRun({ text: "目录", size: 32, bold: true, color: "0F4C5C", font: { eastAsia: "SimHei" } })] }),
        new TableOfContents("TOC", { hyperlink: true, headingStyleRange: "1-3" }),
        new Paragraph({ children: [new PageBreak()] }),
      ],
    },
    {
      properties: {
        page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1701, right: 1417 }, pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL } },
      },
      headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "AI漫剧工业化制作·课程大纲", size: 18, color: "AAAAAA", font: { eastAsia: "Microsoft YaHei" } })] })] }) },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: ["- ", PageNumber.CURRENT, " -"], size: 18, color: "AAAAAA" })] })] }) },
      children: all,
    },
  ],
});

(async () => {
  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync("课程大纲_AI漫剧工业化制作.docx", buffer);
  console.log("Done.");
})();
