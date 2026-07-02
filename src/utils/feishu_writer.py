#!/usr/bin/env python3
"""
Feishu Bitable Writer — 飞书多维表格自动写入工具

Auto-creates bitable, tables, fields, and writes pipeline output.
Requires: FEISHU_APP_ID, FEISHU_APP_SECRET (environment variables)

Usage:
    from utils.feishu_writer import FeishuWriter
    fw = FeishuWriter()
    fw.ensure_tables()  # creates bitable + 4 tables + 83 fields if needed
    fw.write_story(data)     # data = dict of field_name -> value
    fw.write_director(data)
    fw.write_art(data)
    fw.write_cine(data)
"""

import os
import json
import time
import requests
from typing import Dict, List, Optional, Any


# ============================================================================
# Configuration
# ============================================================================

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_BASE_URL = "https://open.feishu.cn/open-apis"


# ============================================================================
# Field definitions for 4 tables (83 fields total)
# ============================================================================

STORY_FIELDS = [
    {"field_name": "书名", "type": 1},           # 1 = Text
    {"field_name": "章节标题", "type": 1},
    {"field_name": "一句话梗概", "type": 1},
    {"field_name": "正文字数", "type": 2},        # 2 = Number
    {"field_name": "情绪弧线位置", "type": 1},
    {"field_name": "主角姓名", "type": 1},
    {"field_name": "主角代号", "type": 1},
    {"field_name": "主角身份", "type": 1},
    {"field_name": "主角外貌摘要", "type": 1},
    {"field_name": "前期动机", "type": 1},
    {"field_name": "后期动机", "type": 1},
    {"field_name": "钩子类型", "type": 1},
    {"field_name": "未解决悬念数", "type": 2},
    {"field_name": "新增角色数", "type": 2},
    {"field_name": "新增场景数", "type": 2},
    {"field_name": "视觉风格", "type": 1},
    {"field_name": "创作者的话", "type": 1},
    {"field_name": "蓝图进度", "type": 1},
]

DIRECTOR_FIELDS = [
    {"field_name": "P编号", "type": 1},
    {"field_name": "四字标题", "type": 1},
    {"field_name": "时长_秒", "type": 2},
    {"field_name": "重要性", "type": 1},
    {"field_name": "场景名", "type": 1},
    {"field_name": "人物", "type": 1},
    {"field_name": "朝向", "type": 1},
    {"field_name": "空间位置", "type": 1},
    {"field_name": "运镜方式", "type": 1},
    {"field_name": "画面位置", "type": 1},
    {"field_name": "视线方向", "type": 1},
    {"field_name": "景别", "type": 1},
    {"field_name": "画面描述", "type": 1},
    {"field_name": "动作描述", "type": 1},
    {"field_name": "台词", "type": 1},
    {"field_name": "语气词", "type": 1},
    {"field_name": "音效", "type": 1},
    {"field_name": "灯光方案", "type": 1},
    {"field_name": "BGM_Cue", "type": 1},
    {"field_name": "转场方式", "type": 1},
    {"field_name": "角色数", "type": 2},
]

ART_FIELDS = [
    {"field_name": "编号", "type": 1},
    {"field_name": "资产类型", "type": 1},
    {"field_name": "角色ID", "type": 1},
    {"field_name": "场景ID", "type": 1},
    {"field_name": "道具ID", "type": 1},
    {"field_name": "名称", "type": 1},
    {"field_name": "阵营", "type": 1},
    {"field_name": "性别年龄", "type": 1},
    {"field_name": "体型身高", "type": 1},
    {"field_name": "外观关键词", "type": 1},
    {"field_name": "识别标记", "type": 1},
    {"field_name": "服装摘要", "type": 1},
    {"field_name": "音色描述", "type": 1},
    {"field_name": "场景光线色调", "type": 1},
    {"field_name": "场景氛围", "type": 1},
    {"field_name": "道具尺寸级", "type": 1},
    {"field_name": "道具持有者", "type": 1},
    {"field_name": "生图提示词", "type": 1},
    {"field_name": "Hex色值", "type": 1},
    {"field_name": "SRT时间码", "type": 1},
    {"field_name": "SRT内容", "type": 1},
    {"field_name": "生图成品", "type": 17},  # 17 = Attachment
]

CINE_FIELDS = [
    {"field_name": "P编号", "type": 1},
    {"field_name": "分支", "type": 1},
    {"field_name": "Style", "type": 1},
    {"field_name": "Format", "type": 1},
    {"field_name": "Film_Stock", "type": 1},
    {"field_name": "Color_Grade", "type": 1},
    {"field_name": "Duration", "type": 2},
    {"field_name": "Camera", "type": 1},
    {"field_name": "Optics", "type": 1},
    {"field_name": "Subject", "type": 1},
    {"field_name": "Narrative", "type": 1},
    {"field_name": "Mood", "type": 1},
    {"field_name": "Dialogue_Cue", "type": 1},
    {"field_name": "Seedance直接输入", "type": 1},
    {"field_name": "Seedance时间分段", "type": 1},
    {"field_name": "首帧引用", "type": 1},
    {"field_name": "首帧提示词_完整版", "type": 1},
    {"field_name": "尾帧提示词_完整版", "type": 1},
    {"field_name": "首帧提示词_精简版", "type": 1},
    {"field_name": "尾帧提示词_精简版", "type": 1},
    {"field_name": "是否B2极端运动", "type": 4},  # 4 = Checkbox
    {"field_name": "首帧成品", "type": 17},       # 17 = Attachment
    {"field_name": "尾帧成品", "type": 17},
    {"field_name": "视频成品", "type": 17},
]

# Map agent name -> (table_name, fields)
TABLE_CONFIG = {
    "story":    ("故事总表", STORY_FIELDS),
    "director": ("分镜脚本表", DIRECTOR_FIELDS),
    "art":      ("资产库表", ART_FIELDS),
    "cine":     ("视频提示词表", CINE_FIELDS),
}


# ============================================================================
# FeishuWriter
# ============================================================================

class FeishuWriter:
    """Auto-create bitable, tables, fields, and write pipeline output."""

    def __init__(self, app_id: str = "", app_secret: str = ""):
        self.app_id = app_id or FEISHU_APP_ID
        self.app_secret = app_secret or FEISHU_APP_SECRET
        self._disabled = not self.app_id or not self.app_secret
        if self._disabled:
            print("[飞书] 未配置凭证·跳过飞书写入")
            return

        self._token = None
        self._token_expire = 0
        self.bitable_id: Optional[str] = None
        self.table_ids: Dict[str, str] = {}
        self._ready = False

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _get_token(self) -> str:
        """Get or refresh tenant_access_token."""
        if self._token and time.time() < self._token_expire - 60:
            return self._token

        resp = requests.post(
            f"{FEISHU_BASE_URL}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=10,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"飞书鉴权失败: {data.get('msg', resp.text)}")

        self._token = data["tenant_access_token"]
        self._token_expire = time.time() + data.get("expire", 7200)
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    def _skip_if_disabled(self):
        """Return True if Feishu is disabled (no credentials)."""
        return self._disabled

    # ------------------------------------------------------------------
    # Bitable & Table creation
    # ------------------------------------------------------------------

    def use_bitable(self, bitable_id: str):
        """Use an existing bitable. Auto-fixes missing tables/fields."""
        if self._skip_if_disabled():
            return
        self.bitable_id = bitable_id
        token = self._get_token()

        # List existing tables
        resp = requests.get(
            f"{FEISHU_BASE_URL}/bitable/v1/apps/{bitable_id}/tables",
            headers=self._headers(),
            timeout=10,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"读取子表列表失败: {data.get('msg')}")

        name_to_key = {v[0]: k for k, v in TABLE_CONFIG.items()}
        for item in data.get("data", {}).get("items", []):
            table_name = item.get("name", "")
            table_id = item.get("table_id", "")
            if table_name in name_to_key:
                self.table_ids[name_to_key[table_name]] = table_id

        # Create missing tables
        for agent_key, (table_name, fields) in TABLE_CONFIG.items():
            if agent_key not in self.table_ids:
                tid = self._create_table(bitable_id, table_name)
                self.table_ids[agent_key] = tid
                self._create_fields(bitable_id, tid, fields)
            else:
                # Check field integrity
                self._ensure_fields(bitable_id, self.table_ids[agent_key], fields, agent_key)

        self._ready = True
        print(f"[飞书] 复用已有表格 {bitable_id}·字段完整")

    def ensure_tables(self, bitable_name: str = "漫剧流水线") -> bool:
        """Create bitable + 4 tables + fields if they don't exist."""
        if self._skip_if_disabled():
            return False
        token = self._get_token()

        # 1. Create bitable
        resp = requests.post(
            f"{FEISHU_BASE_URL}/bitable/v1/apps",
            headers=self._headers(),
            json={"name": bitable_name},
            timeout=10,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"创建多维表格失败: {data.get('msg', resp.text)}")

        self.bitable_id = data["data"]["app"]["app_token"]
        print(f"[飞书] 多维表格已创建: {self.bitable_id}")

        # 2. Create 4 tables
        for agent_key, (table_name, fields) in TABLE_CONFIG.items():
            table_id = self._create_table(self.bitable_id, table_name)
            self.table_ids[agent_key] = table_id

            # 3. Create fields for this table
            self._create_fields(self.bitable_id, table_id, fields)

        self._ready = True
        print(f"[飞书] 4 张子表 + {sum(len(f) for _, f in TABLE_CONFIG.values())} 个字段已就绪")
        return True

    def _create_table(self, bitable_id: str, name: str) -> str:
        """Create a table inside the bitable. Returns table_id."""
        resp = requests.post(
            f"{FEISHU_BASE_URL}/bitable/v1/apps/{bitable_id}/tables",
            headers=self._headers(),
            json={"table": {"name": name}},
            timeout=10,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"创建子表[{name}]失败: {data.get('msg', resp.text)}")
        return data["data"]["table_id"]

    def _ensure_fields(self, bitable_id: str, table_id: str, fields: List[dict], agent_key: str):
        """Check existing fields, create any that are missing."""
        resp = requests.get(
            f"{FEISHU_BASE_URL}/bitable/v1/apps/{bitable_id}/tables/{table_id}/fields",
            headers=self._headers(),
            timeout=10,
        )
        data = resp.json()
        existing_names = set()
        if data.get("code") == 0:
            for item in data.get("data", {}).get("items", []):
                existing_names.add(item.get("field_name", ""))

        missing = [f for f in fields if f["field_name"] not in existing_names]
        if missing:
            print(f"  🔧 {agent_key}表补建{len(missing)}个缺失字段")
            self._create_fields(bitable_id, table_id, missing)

    def _create_fields(self, bitable_id: str, table_id: str, fields: List[dict]):
        """Create fields one by one."""
        total = len(fields)
        for i, field in enumerate(fields):
            resp = requests.post(
                f"{FEISHU_BASE_URL}/bitable/v1/apps/{bitable_id}/tables/{table_id}/fields",
                headers=self._headers(),
                json=field,
                timeout=10,
            )
            data = resp.json()
            if data.get("code") != 0:
                print(f"  ⚠️ 字段({i+1}/{total}) {field['field_name']}: {data.get('msg','')}")
            time.sleep(0.08)  # rate limit (10 req/s in theory, be safe)
        print(f"  ✅ {total}个字段创建完成")

    # ------------------------------------------------------------------
    # Write rows
    # ------------------------------------------------------------------

    def write_story(self, data: dict):
        """Write one story row."""
        if self._skip_if_disabled(): return
        self._write_rows("story", [data])

    def write_director(self, rows: List[dict]):
        if self._skip_if_disabled(): return
        self._write_rows("director", rows)

    def write_art(self, rows: List[dict]):
        if self._skip_if_disabled(): return
        self._write_rows("art", rows)

    def write_cine(self, rows: List[dict]):
        if self._skip_if_disabled(): return
        self._write_rows("cine", rows)

    def _write_rows(self, agent_key: str, rows: List[dict]):
        """Write rows with proper type handling."""
        if self._skip_if_disabled(): return
        if not self._ready:
            raise RuntimeError("请先调用 ensure_tables() 或 use_bitable()")

        table_id = self.table_ids.get(agent_key)
        if not table_id:
            raise ValueError(f"Unknown agent key: {agent_key}")

        # Fields that should be bool (Checkbox type=4)
        bool_fields = {"是否B2极端运动"}
        # Fields that are Attachment type=17 — leave empty for manual upload
        attach_fields = {"生图成品", "首帧成品", "尾帧成品", "视频成品"}

        records = []
        for row in rows:
            fields = {}
            for k, v in row.items():
                if k in attach_fields:
                    continue  # skip attachment fields, manual upload
                if v is None or v == "":
                    continue
                if k in bool_fields:
                    fields[k] = bool(v)
                elif isinstance(v, (int, float)):
                    fields[k] = v
                else:
                    fields[k] = str(v)
            if fields:
                records.append({"fields": fields})

        if not records:
            return

        # Batch write (max 500 per call)
        batch_size = 500
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            resp = requests.post(
                f"{FEISHU_BASE_URL}/bitable/v1/apps/{self.bitable_id}/tables/{table_id}/records/batch_create",
                headers=self._headers(),
                json={"records": batch},
                timeout=30,
            )
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"写入{agent_key}表失败: {data.get('msg', resp.text)}")
            time.sleep(0.3)

        print(f"[飞书] {agent_key}表写入 {len(records)} 条记录")


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="飞书多维表格写入")
    parser.add_argument("--json", help="从 JSON 文件读取数据写入飞书")
    parser.add_argument("--bitable", help="复用已有表格的 bitable_id（首次不传·自动创建）")
    parser.add_argument("--name", default="漫剧流水线", help="新建表格名称")
    args = parser.parse_args()

    fw = FeishuWriter()

    if args.bitable:
        fw.use_bitable(args.bitable)
    else:
        fw.ensure_tables(args.name)

    if args.json:
        with open(args.json, "r", encoding="utf-8") as f:
            data = json.load(f)

        if data.get("story"):
            fw.write_story(data["story"])
        if data.get("director"):
            fw.write_director(data["director"])
        if data.get("art"):
            fw.write_art(data["art"])
        if data.get("cine"):
            fw.write_cine(data["cine"])

        print(f"[飞书] 全部写入完成: {args.json}")
