#!/usr/bin/env python
"""
Demo script to showcase the AI Log Analyzer & Auto-Task Creator functionality

This script demonstrates the complete workflow:
1. Generate test logs
2. Analyze and save logs to database  
3. Show statistics
"""

import os
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ideagraph.settings')
import django
django.setup()

from core.services.log_analyzer_service import LogAnalyzerService
from main.models import LogEntry, ErrorAnalysis
from django.utils import timezone
from datetime import timedelta

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")

def print_section(text):
    """Print a section header"""
    print(f"\n--- {text} ---\n")

def main():
    print_header("🔍 AI Log Analyzer Demo")
    
    # Step 1: Check existing logs
    print_section("Step 1: Checking log files")
    
    analyzer = LogAnalyzerService()
    log_files = analyzer.get_log_files()
    
    if not log_files:
        print("❌ No log files found!")
        print("\nGenerate test logs first:")
        print("  python generate_test_logs.py")
        return
    
    print(f"✅ Found {len(log_files)} log file(s):")
    for log_file in log_files:
        size = log_file.stat().st_size
        print(f"  - {log_file.name} ({size:,} bytes)")
    
    # Step 2: Analyze logs
    print_section("Step 2: Analyzing logs")
    
    entries = analyzer.analyze_logs(hours_back=24, min_level='WARNING')
    print(f"📊 Extracted {len(entries)} entries (WARNING and above)")
    
    # Count by level
    level_counts = {}
    for entry in entries:
        level = entry['level']
        level_counts[level] = level_counts.get(level, 0) + 1
    
    print("\n📈 Breakdown by level:")
    for level in ['WARNING', 'ERROR', 'CRITICAL']:
        count = level_counts.get(level, 0)
        if count > 0:
            print(f"  - {level}: {count}")
    
    # Step 3: Save to database
    print_section("Step 3: Saving to database")
    
    saved_count = analyzer.save_to_database(entries)
    print(f"✅ Saved {saved_count} new entries to database")
    
    # Step 4: Show database statistics
    print_section("Step 4: Database statistics")
    
    total_logs = LogEntry.objects.count()
    analyzed_logs = LogEntry.objects.filter(analyzed=True).count()
    unanalyzed_logs = LogEntry.objects.filter(analyzed=False).count()
    
    print(f"📊 Total log entries: {total_logs}")
    print(f"  - Analyzed: {analyzed_logs}")
    print(f"  - Not analyzed: {unanalyzed_logs}")
    
    # Recent errors
    recent_errors = LogEntry.objects.filter(
        level__in=['ERROR', 'CRITICAL']
    ).order_by('-timestamp')[:5]
    
    if recent_errors:
        print(f"\n🔴 Recent errors ({recent_errors.count()}):")
        for error in recent_errors:
            timestamp = error.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            print(f"  - [{error.level}] {error.message[:60]}...")
            print(f"    {timestamp} | {error.logger_name}")
    
    # Step 5: Show analyses
    print_section("Step 5: Error analyses")
    
    total_analyses = ErrorAnalysis.objects.count()
    pending = 0
    approved = 0
    task_created = 0
    
    print(f"📊 Total error analyses: {total_analyses}")
    
    if total_analyses > 0:
        # By status
        pending = ErrorAnalysis.objects.filter(status='pending').count()
        approved = ErrorAnalysis.objects.filter(status='approved').count()
        task_created = ErrorAnalysis.objects.filter(status='task_created').count()
        
        print("\n  Status breakdown:")
        print(f"    - Pending: {pending}")
        print(f"    - Approved: {approved}")
        print(f"    - Task created: {task_created}")
        
        # By severity
        severity_counts = {}
        for analysis in ErrorAnalysis.objects.all():
            severity = analysis.severity
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        if severity_counts:
            print("\n  Severity breakdown:")
            for severity in ['critical', 'high', 'medium', 'low']:
                count = severity_counts.get(severity, 0)
                if count > 0:
                    emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}[severity]
                    print(f"    {emoji} {severity}: {count}")
        
        # Recent analyses
        recent = ErrorAnalysis.objects.order_by('-created_at')[:3]
        if recent:
            print(f"\n  Recent analyses:")
            for analysis in recent:
                print(f"    - [{analysis.severity}] {analysis.summary[:50]}...")
                print(f"      Confidence: {analysis.ai_confidence:.0%} | Actionable: {analysis.is_actionable}")
    else:
        print("\n💡 No analyses yet. Run:")
        print("   python manage.py analyze_logs --analyze")
    
    # Step 6: Next steps
    print_section("Next Steps")
    
    if unanalyzed_logs > 0:
        print("📝 You have unanalyzed log entries!")
        print("\n  Analyze with AI:")
        print("    python manage.py analyze_logs --analyze --limit 10")
    
    if pending > 0:
        print("\n📋 You have pending error analyses!")
        print("\n  Create tasks:")
        print("    python manage.py analyze_logs --create-tasks --min-severity medium")
    
    if unanalyzed_logs == 0 and pending == 0:
        print("✨ Everything is up to date!")
        print("\n  Run complete workflow:")
        print("    python manage.py analyze_logs --all")
    
    print_header("Demo Complete")
    print("📚 For more information, see: AI_LOG_ANALYZER_GUIDE.md\n")

if __name__ == '__main__':
    main()
