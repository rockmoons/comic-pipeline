#!/usr/bin/env python3
"""
Comic Pipeline Orchestrator v1.0
================================
Automates the 4-Agent pipeline: calls LLM API for each agent sequentially,
handles sliding-window batching, state snapshot pruning, global ID registry,
and automatic retry + validation.

Usage:
    python orchestrator.py --concept "火星女战士被怪兽追杀" --style "CG国漫"

Configuration via environment variables:
    OPENAI_API_KEY    API key for LLM
    OPENAI_BASE_URL   API base URL (default: https://api.openai.com/v1)
    LLM_MODEL         Model name (default: gpt-4o)
"""

import os
import sys
import re
import json
import time
import sqlite3
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from utils.parser import (
    extract_p_numbers, extract_state_snapshot, extract_at_images,
    extract_json_block, generate_session_id,
)
from utils.reporter import CheckResult, Status
from validate_pipeline import run_validation, read_file, prevalidate_json


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""
    api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o"))
    max_retries: int = 3
    retry_delay: float = 2.0
    temperature: float = 0.7
    max_tokens: int = 8192
    db_path: str = ""

    def __post_init__(self):
        if not self.db_path:
            self.db_path = str(ROOT / "pipeline_state.db")


# ============================================================================
# Global ID Registry
# ============================================================================

class GlobalIDRegistry:
    """SQLite-backed registry for character/scene/prop IDs across chapters.

    Ensures that the same character name always maps to the same ID,
    preventing cross-chapter identity collisions.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._init_tables()

    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                first_chapter INTEGER,
                last_chapter INTEGER,
                status TEXT DEFAULT 'active'
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS scenes (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                first_chapter INTEGER
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS props (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                first_chapter INTEGER
            )
        """)
        self.conn.commit()

    def next_char_id(self) -> str:
        row = self.conn.execute("SELECT COUNT(*) FROM characters").fetchone()
        return f"CHAR_{(row[0] + 1):02d}"

    def next_scene_id(self) -> str:
        row = self.conn.execute("SELECT COUNT(*) FROM scenes").fetchone()
        return f"SCENE_{(row[0] + 1):02d}"

    def next_prop_id(self) -> str:
        row = self.conn.execute("SELECT COUNT(*) FROM props").fetchone()
        return f"PROP_{(row[0] + 1):02d}"

    def resolve_character(self, name: str, chapter: int) -> str:
        """Resolve character name to ID. Creates new entry if not found."""
        row = self.conn.execute(
            "SELECT id FROM characters WHERE name = ?", (name,)
        ).fetchone()
        if row:
            self.conn.execute(
                "UPDATE characters SET last_chapter = ?, status = 'active' WHERE name = ?",
                (chapter, name)
            )
            self.conn.commit()
            return row[0]
        new_id = self.next_char_id()
        self.conn.execute(
            "INSERT INTO characters (id, name, first_chapter, last_chapter) VALUES (?, ?, ?, ?)",
            (new_id, name, chapter, chapter)
        )
        self.conn.commit()
        return new_id

    def resolve_scene(self, name: str, chapter: int) -> str:
        row = self.conn.execute(
            "SELECT id FROM scenes WHERE name = ?", (name,)
        ).fetchone()
        if row:
            return row[0]
        new_id = self.next_scene_id()
        self.conn.execute(
            "INSERT INTO scenes (id, name, first_chapter) VALUES (?, ?, ?)",
            (new_id, name, chapter)
        )
        self.conn.commit()
        return new_id

    def close(self):
        self.conn.close()


# ============================================================================
# Sliding Window Slicer
# ============================================================================

class SlidingWindowSlicer:
    """Batches P-numbers exceeding the safe single-pass threshold.

    When the director produces more than 30 P-numbers, downstream
    agents risk token overflow. This slicer splits scenes into
    batches of ~20 for sequential processing.
    """

    def __init__(self, max_per_batch: int = 20, threshold: int = 30):
        self.max_per_batch = max_per_batch
        self.threshold = threshold

    def should_slice(self, director_output: str) -> bool:
        pnums = extract_p_numbers(director_output)
        return len(pnums) > self.threshold

    def slice(self, director_output: str) -> List[str]:
        """Split director output into batch-sized chunks by P-number groups."""
        pnums = extract_p_numbers(director_output)
        if len(pnums) <= self.threshold:
            return [director_output]

        # Split by P-number blocks
        blocks = re.split(r'(?=\*\*P\d{2})', director_output)
        header = blocks[0]  # Everything before first P-number
        scene_blocks = blocks[1:]

        batches = []
        for i in range(0, len(scene_blocks), self.max_per_batch):
            batch = header + "".join(scene_blocks[i:i + self.max_per_batch])
            batches.append(batch)

        return batches


# ============================================================================
# Snapshot Pruner
# ============================================================================

class SnapshotPruner:
    """Trims accumulated state snapshots for long-running series.

    Characters/scenes not appearing for `inactive_threshold` chapters
    are marked as 'archived' and excluded from the active context
    passed to downstream agents.
    """

    def __init__(self, inactive_threshold: int = 5):
        self.threshold = inactive_threshold

    def prune(self, snapshot: dict, current_chapter: int) -> dict:
        """Return a pruned snapshot with only active characters."""
        if not snapshot:
            return {}

        pruned = dict(snapshot)
        all_chars = snapshot.get("all_characters", [])

        active = []
        for char in all_chars:
            last = char.get("last_appearance_chapter", current_chapter)
            if char.get("status") == "dead":
                char["status"] = "archived"
            elif current_chapter - last > self.threshold:
                char["status"] = "archived"
            else:
                char["status"] = "active"
                active.append(char)

        pruned["active_characters"] = active[:20]  # Top 20 core
        pruned["all_characters"] = all_chars  # Keep full list for audit
        return pruned


# ============================================================================
# Agent Chain Runner
# ============================================================================

class AgentChainRunner:
    """Orchestrates the 4-Agent pipeline with LLM API calls."""

    def __init__(self, config: OrchestratorConfig = None):
        self.config = config or OrchestratorConfig()
        self.registry = GlobalIDRegistry(self.config.db_path)
        self.slicer = SlidingWindowSlicer()
        self.pruner = SnapshotPruner()
        self._session_id = generate_session_id()

        # Initialize LLM client
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
        except ImportError:
            print("ERROR: openai package not installed. Run: pip install openai")
            sys.exit(1)

    def _call_llm(self, system_prompt: str, user_message: str) -> str:
        """Call LLM with retry logic."""
        last_error = None
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                return response.choices[0].message.content
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (2 ** attempt)
                    print(f"  LLM call failed (attempt {attempt + 1}): {e}")
                    print(f"  Retrying in {delay:.1f}s...")
                    time.sleep(delay)
        raise RuntimeError(f"LLM call failed after {self.config.max_retries} retries: {last_error}")

    def _load_prompt(self, filename: str) -> str:
        """Load an agent prompt file."""
        path = ROOT / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def run_agent_1(self, concept: str, style: str = "CG国漫",
                    chapter: int = 1, prev_snapshot: dict = None) -> Tuple[str, dict]:
        """Agent 1: Story Creation.

        Returns (story_output, state_snapshot).
        """
        prompt = self._load_prompt("01_故事创作_v3.0.md")

        # Build user message
        if chapter == 1:
            user_msg = f"请根据以下构思创建故事：{concept}\n视觉风格：{style}\n请直接生成第1章。"
        else:
            snap_str = json.dumps(prev_snapshot, ensure_ascii=False, indent=2) if prev_snapshot else "{}"
            user_msg = f"继续写第{chapter}章。上一章状态快照：\n{snap_str}"

        print(f"[Agent 1] Story Creation - Chapter {chapter}...")
        output = self._call_llm(prompt, user_msg)

        # Extract state snapshot
        snapshot = extract_state_snapshot(output) or {}
        snapshot = self.pruner.prune(snapshot, chapter)

        print(f"  Output: {len(output)} chars, snapshot: {len(snapshot)} keys")
        return output, snapshot

    def run_agent_2(self, story_output: str) -> str:
        """Agent 2: Director Adaptation."""
        prompt = self._load_prompt("02_导演漫改_v3.0.md")
        user_msg = f"请将以下小说改编为分场剧本：\n\n{story_output}"

        print(f"[Agent 2] Director Adaptation...")
        output = self._call_llm(prompt, user_msg)

        # Check for P-number explosion
        p_count = len(extract_p_numbers(output))
        if p_count > self.slicer.threshold:
            print(f"  WARNING: {p_count} P-numbers detected (> {self.slicer.threshold})")
            print(f"  SlidingWindowSlicer will be used for downstream agents")

        print(f"  Output: {len(output)} chars, {p_count} P-numbers")
        return output

    def run_agent_3(self, director_output: str) -> str:
        """Agent 3: Art Direction.

        If P-numbers exceed threshold, uses SlidingWindowSlicer
        to process in batches and merge results.
        """
        prompt = self._load_prompt("03_美术资产_v3.0.md")

        if self.slicer.should_slice(director_output):
            batches = self.slicer.slice(director_output)
            print(f"[Agent 3] Art Direction - {len(batches)} batches (sliding window)...")

            all_outputs = []
            for i, batch in enumerate(batches):
                print(f"  Batch {i + 1}/{len(batches)}...")
                user_msg = f"请为以下分场剧本生成美术资产：\n\n{batch}"
                output = self._call_llm(prompt, user_msg)
                all_outputs.append(output)

            # Merge: concatenate with separator
            merged = "\n\n---\n\n".join(all_outputs)
            print(f"  Merged output: {len(merged)} chars")
            return merged
        else:
            print(f"[Agent 3] Art Direction...")
            user_msg = f"请为以下分场剧本生成美术资产：\n\n{director_output}"
            output = self._call_llm(prompt, user_msg)
            print(f"  Output: {len(output)} chars")
            return output

    def run_agent_4(self, director_output: str, art_output: str) -> str:
        """Agent 4: Cinematographer."""
        prompt = self._load_prompt("04_分镜生成_v3.0.md")
        user_msg = f"请根据以下分场剧本和美术资产生成视频提示词：\n\n## 分场剧本\n{director_output}\n\n## 美术资产\n{art_output}"

        print(f"[Agent 4] Cinematographer...")
        output = self._call_llm(prompt, user_msg)
        print(f"  Output: {len(output)} chars")
        return output

    def run_full_pipeline(self, concept: str, style: str = "CG国漫",
                          output_dir: str = None, max_chapters: int = 1) -> Dict:
        """Run the complete pipeline for one or more chapters.

        Returns dict with keys: story, director, art, cine, validation_report.
        """
        out = Path(output_dir) if output_dir else ROOT / "output" / self._session_id
        out.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"  Comic Pipeline Orchestrator v1.0")
        print(f"  Concept: {concept}")
        print(f"  Style: {style}")
        print(f"  Chapters: {max_chapters}")
        print(f"  Output: {out}")
        print(f"{'='*60}\n")

        prev_snapshot = None
        all_results = []

        for ch in range(1, max_chapters + 1):
            print(f"\n--- Chapter {ch}/{max_chapters} ---\n")

            # Agent 1
            story, snapshot = self.run_agent_1(concept, style, ch, prev_snapshot)
            prev_snapshot = snapshot
            (out / f"story_ch{ch:02d}.txt").write_text(story, encoding="utf-8")

            # Agent 2
            director = self.run_agent_2(story)
            (out / f"director_ch{ch:02d}.txt").write_text(director, encoding="utf-8")

            # Agent 3
            art = self.run_agent_3(director)
            (out / f"art_ch{ch:02d}.txt").write_text(art, encoding="utf-8")

            # Agent 4
            cine = self.run_agent_4(director, art)
            (out / f"cine_ch{ch:02d}.txt").write_text(cine, encoding="utf-8")

            # Validate
            print(f"\n[Validation] Running checks...")
            report = run_validation(story, director, art, cine)
            print(f"  Pass rate: {report.pass_rate:.1f}% | "
                  f"FATAL: {report.fatal_count} | FAIL: {report.fail_count} | "
                  f"WARN: {report.warn_count}")

            if report.fatal_count > 0:
                print(f"  FATAL errors detected! Check output for details.")
            elif report.fail_count > 0:
                print(f"  Non-fatal failures detected. Review recommended.")

            all_results.append({
                "chapter": ch,
                "pass_rate": report.pass_rate,
                "fatal": report.fatal_count,
                "fail": report.fail_count,
                "warn": report.warn_count,
            })

        # Cleanup
        self.registry.close()

        # Summary
        print(f"\n{'='*60}")
        print(f"  Pipeline Complete")
        print(f"  Total chapters: {max_chapters}")
        avg_pass = sum(r["pass_rate"] for r in all_results) / len(all_results) if all_results else 0
        total_fatal = sum(r["fatal"] for r in all_results)
        print(f"  Average pass rate: {avg_pass:.1f}%")
        print(f"  Total FATAL: {total_fatal}")
        print(f"  Output directory: {out}")
        print(f"{'='*60}")

        return {
            "session_id": self._session_id,
            "output_dir": str(out),
            "results": all_results,
        }


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Comic Pipeline Orchestrator - Automated 4-Agent Pipeline"
    )
    parser.add_argument("--concept", "-c", type=str, required=True,
                        help="Story concept (e.g., '火星女战士被怪兽追杀')")
    parser.add_argument("--style", "-s", type=str, default="CG国漫",
                        help="Visual style (default: CG国漫)")
    parser.add_argument("--chapters", "-n", type=int, default=1,
                        help="Number of chapters (default: 1)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output directory")
    parser.add_argument("--model", "-m", type=str, default=None,
                        help="LLM model name (overrides LLM_MODEL env var)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate existing outputs without calling LLM")

    args = parser.parse_args()

    if args.dry_run:
        # Validate existing output directory
        out = Path(args.output) if args.output else None
        if not out or not out.exists():
            print("ERROR: --output required for --dry-run")
            sys.exit(1)
        files = {
            "story": out / "story_ch01.txt",
            "director": out / "director_ch01.txt",
            "art": out / "art_ch01.txt",
            "cine": out / "cine_ch01.txt",
        }
        missing = [k for k, v in files.items() if not v.exists()]
        if missing:
            print(f"ERROR: Missing files: {missing}")
            sys.exit(1)
        report = run_validation(
            files["story"].read_text(encoding="utf-8"),
            files["director"].read_text(encoding="utf-8"),
            files["art"].read_text(encoding="utf-8"),
            files["cine"].read_text(encoding="utf-8"),
        )
        from utils.reporter import format_report
        print(format_report(report))
        sys.exit(0 if report.fatal_count == 0 else 2)

    # Check API key
    config = OrchestratorConfig()
    if args.model:
        config.model = args.model
    if not config.api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set.")
        print("Set it via: $env:OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    runner = AgentChainRunner(config)
    runner.run_full_pipeline(
        concept=args.concept,
        style=args.style,
        output_dir=args.output,
        max_chapters=args.chapters,
    )


if __name__ == "__main__":
    main()
