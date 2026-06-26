#!/usr/bin/env python3
"""Comic Pipeline Runner - One-click validation and status check.

Usage:
    python pipeline_runner.py check <dir>     # Validate a pipeline output directory
    python pipeline_runner.py status          # Show project status
    python pipeline_runner.py quick           # Quick smoke test on sample data
"""

import sys
import os
import glob
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def cmd_check(path: str):
    """Validate a pipeline output directory containing story/director/art/cine.txt."""
    from validate_pipeline import run_validation, read_file
    from utils.reporter import format_report, format_json
    
    files = {
        'story': os.path.join(path, 'story.txt'),
        'director': os.path.join(path, 'director.txt'),
        'art': os.path.join(path, 'art.txt'),
        'cine': os.path.join(path, 'cine.txt'),
    }
    
    missing = [k for k, v in files.items() if not os.path.exists(v)]
    if missing:
        print(f"❌ 缺少文件: {', '.join(missing)}")
        sys.exit(1)
    
    story = read_file(files['story'])
    director = read_file(files['director'])
    art = read_file(files['art'])
    cine = read_file(files['cine'])
    
    report = run_validation(story, director, art, cine)
    
    json_mode = '--json' in sys.argv
    if json_mode:
        print(format_json(report))
    else:
        print(format_report(report))
    
    # Exit code based on results
    if report.fatal_count > 0:
        sys.exit(2)
    elif report.fail_count > 0:
        sys.exit(1)


def cmd_status():
    """Show project status."""
    prompt_files = glob.glob(os.path.join(ROOT, '0*_v3.0.md'))
    test_dirs = glob.glob(os.path.join(ROOT, 'test_fixtures', '*', ''))
    
    print("=" * 50)
    print("  Comic Pipeline - 项目状态")
    print("=" * 50)
    print(f"\n📁 Prompt 文件 ({len(prompt_files)}个):")
    for f in sorted(prompt_files):
        name = os.path.basename(f)
        lines = len(open(f, encoding='utf-8').readlines())
        # Count checks
        text = open(f, encoding='utf-8').read()
        checks = text.count('□ ')
        print(f"  ✅ {name:<30s} {lines}行 {checks}项校验")
    
    print(f"\n🧪 测试数据 ({len(test_dirs)}组):")
    for d in sorted(test_dirs):
        name = os.path.basename(os.path.dirname(d))
        files = glob.glob(os.path.join(d, '*.txt'))
        print(f"  📂 {name:<30s} {len(files)}个文件")
    
    print(f"\n🔧 工具:")
    print(f"  ✅ validate_pipeline.py    外部校验脚本(46项)")
    print(f"  ✅ pipeline_runner.py      一键运行脚本")
    print(f"  ✅ README.md               项目文档")
    
    # Run quick smoke test
    print(f"\n🚀 快速冒烟测试...")
    cmd_quick()


def cmd_quick():
    """Quick smoke test on sample data."""
    from validate_pipeline import run_validation, read_file
    
    sample = os.path.join(ROOT, 'test_fixtures', 'prison_story')
    if not os.path.exists(sample):
        sample = os.path.join(ROOT, 'test_fixtures', 'sample_run')
    
    try:
        story = read_file(os.path.join(sample, 'story.txt'))
        director = read_file(os.path.join(sample, 'director.txt'))
        art = read_file(os.path.join(sample, 'art.txt'))
        cine = read_file(os.path.join(sample, 'cine.txt'))
        report = run_validation(story, director, art, cine)
        
        icon = "✅" if report.fatal_count == 0 else "🔴"
        print(f"  {icon} 通过率: {report.pass_rate:.1f}% | "
              f"{report.pass_count}✅ {report.fail_count}❌ {report.warn_count}⚠️ {report.fatal_count}🔴")
    except Exception as e:
        print(f"  ❌ 冒烟测试失败: {e}")


def cmd_help():
    print(__doc__)
    print("Commands:")
    print("  check <dir>     Validate pipeline output directory")
    print("  status          Show project status + quick smoke test")
    print("  quick           Quick smoke test on sample data")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        cmd_status()
    else:
        cmd = sys.argv[1]
        if cmd == 'check' and len(sys.argv) >= 3:
            cmd_check(sys.argv[2])
        elif cmd == 'status':
            cmd_status()
        elif cmd == 'quick':
            cmd_quick()
        else:
            cmd_help()
