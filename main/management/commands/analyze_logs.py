"""
Django management command to analyze logs and create tasks

This command performs the complete log analysis workflow:
1. Fetch logs from local files and Sentry
2. Analyze errors with AI
3. Create tasks for actionable errors
4. Optionally create GitHub issues
"""

from django.core.management.base import BaseCommand
from core.logger_config import get_logger
from core.services.log_analyzer_service import LogAnalyzerService
from core.services.sentry_service import SentryService
from core.services.ai_error_analyzer_service import AIErrorAnalyzerService
from core.services.auto_task_creator_service import AutoTaskCreatorService

logger = get_logger('analyze_logs_command')


class Command(BaseCommand):
    help = 'Analyze logs, detect errors, and create tasks automatically'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Number of hours to look back in logs (default: 24)'
        )
        
        parser.add_argument(
            '--min-level',
            type=str,
            default='WARNING',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            help='Minimum log level to analyze (default: WARNING)'
        )
        
        parser.add_argument(
            '--fetch-local',
            action='store_true',
            help='Fetch logs from local log files'
        )
        
        parser.add_argument(
            '--fetch-sentry',
            action='store_true',
            help='Fetch logs from Sentry API'
        )
        
        parser.add_argument(
            '--analyze',
            action='store_true',
            help='Analyze fetched logs with AI'
        )
        
        parser.add_argument(
            '--create-tasks',
            action='store_true',
            help='Create tasks from analyses'
        )
        
        parser.add_argument(
            '--min-severity',
            type=str,
            default='medium',
            choices=['low', 'medium', 'high', 'critical'],
            help='Minimum severity for task creation (default: medium)'
        )
        
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.7,
            help='Minimum AI confidence for task creation (default: 0.7)'
        )
        
        parser.add_argument(
            '--auto-github',
            action='store_true',
            help='Automatically create GitHub issues for high/critical errors'
        )
        
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all steps: fetch (local+sentry), analyze, and create tasks'
        )
        
        parser.add_argument(
            '--sentry-org',
            type=str,
            help='Sentry organization slug (overrides settings)'
        )
        
        parser.add_argument(
            '--sentry-project',
            type=str,
            help='Sentry project slug (overrides settings)'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of entries to process (default: 50)'
        )
    
    def handle(self, *args, **options):
        """Execute the command"""
        hours = options['hours']
        min_level = options['min_level']
        fetch_local = options['fetch_local']
        fetch_sentry = options['fetch_sentry']
        analyze = options['analyze']
        create_tasks = options['create_tasks']
        run_all = options['all']
        
        # If --all flag is set, enable all steps
        if run_all:
            fetch_local = True
            fetch_sentry = True
            analyze = True
            create_tasks = True
        
        # If no specific action is specified, show help
        if not (fetch_local or fetch_sentry or analyze or create_tasks):
            self.stdout.write(self.style.WARNING(
                'No action specified. Use --all or specify individual actions '
                '(--fetch-local, --fetch-sentry, --analyze, --create-tasks)'
            ))
            return
        
        self.stdout.write(self.style.SUCCESS('=== AI Log Analyzer & Auto-Task Creator ==='))
        self.stdout.write(f'Looking back: {hours} hours')
        self.stdout.write(f'Minimum level: {min_level}')
        self.stdout.write('')
        
        # Step 1: Fetch local logs
        if fetch_local:
            self.stdout.write(self.style.HTTP_INFO('📂 Fetching local logs...'))
            try:
                log_analyzer = LogAnalyzerService()
                entries = log_analyzer.analyze_logs(
                    hours_back=hours,
                    min_level=min_level
                )
                saved = log_analyzer.save_to_database(entries)
                self.stdout.write(self.style.SUCCESS(f'✅ Saved {saved} new log entries from local files'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error fetching local logs: {e}'))
                logger.error(f"Error fetching local logs: {e}", exc_info=True)
        
        # Step 2: Fetch Sentry logs
        if fetch_sentry:
            self.stdout.write(self.style.HTTP_INFO('🔍 Fetching Sentry events...'))
            try:
                # Get Sentry configuration
                sentry_org = options.get('sentry_org')
                sentry_project = options.get('sentry_project')
                
                # Get from settings if not provided
                if not sentry_org or not sentry_project:
                    from main.models import Settings
                    settings_obj = Settings.objects.first()
                    if settings_obj:
                        # Parse from DSN or environment
                        import os
                        sentry_dsn = os.getenv('SENTRY_DSN', '')
                        sentry_token = os.getenv('SENTRY_AUTH_TOKEN', '')
                        
                        if sentry_dsn and sentry_token:
                            sentry_service = SentryService(dsn=sentry_dsn, auth_token=sentry_token)
                            
                            # Configure if org/project provided
                            if sentry_org and sentry_project:
                                sentry_service.configure(sentry_org, sentry_project, sentry_token)
                            
                            # Test connection
                            if sentry_service.test_connection():
                                saved = sentry_service.fetch_and_save_events(hours_back=hours)
                                self.stdout.write(self.style.SUCCESS(f'✅ Saved {saved} new events from Sentry'))
                            else:
                                self.stdout.write(self.style.WARNING('⚠️  Sentry connection failed'))
                        else:
                            self.stdout.write(self.style.WARNING('⚠️  Sentry not configured (missing DSN or token)'))
                    else:
                        self.stdout.write(self.style.WARNING('⚠️  No settings found in database'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error fetching Sentry events: {e}'))
                logger.error(f"Error fetching Sentry events: {e}", exc_info=True)
        
        # Step 3: Analyze with AI
        if analyze:
            self.stdout.write(self.style.HTTP_INFO('🤖 Analyzing errors with AI...'))
            try:
                ai_analyzer = AIErrorAnalyzerService(use_kigate=True)
                analyses = ai_analyzer.batch_analyze(
                    min_level=min_level,
                    limit=options['limit']
                )
                self.stdout.write(self.style.SUCCESS(f'✅ Created {len(analyses)} error analyses'))
                
                # Show summary
                if analyses:
                    severity_counts = {}
                    actionable_count = 0
                    
                    for analysis in analyses:
                        severity_counts[analysis.severity] = severity_counts.get(analysis.severity, 0) + 1
                        if analysis.is_actionable:
                            actionable_count += 1
                    
                    self.stdout.write('')
                    self.stdout.write('📊 Analysis Summary:')
                    for severity, count in sorted(severity_counts.items()):
                        self.stdout.write(f'  - {severity}: {count}')
                    self.stdout.write(f'  - Actionable: {actionable_count}')
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error analyzing logs: {e}'))
                logger.error(f"Error analyzing logs: {e}", exc_info=True)
        
        # Step 4: Create tasks
        if create_tasks:
            self.stdout.write(self.style.HTTP_INFO('📝 Creating tasks from analyses...'))
            try:
                task_creator = AutoTaskCreatorService()
                tasks = task_creator.process_pending_analyses(
                    min_severity=options['min_severity'],
                    min_confidence=options['min_confidence'],
                    auto_create_github=options['auto_github'],
                    limit=options['limit']
                )
                self.stdout.write(self.style.SUCCESS(f'✅ Created {len(tasks)} tasks'))
                
                # Show task details
                if tasks:
                    self.stdout.write('')
                    self.stdout.write('📋 Created Tasks:')
                    for task in tasks[:10]:  # Show first 10
                        self.stdout.write(f'  - {task.title}')
                        if task.github_issue_url:
                            self.stdout.write(f'    GitHub: {task.github_issue_url}')
                    
                    if len(tasks) > 10:
                        self.stdout.write(f'  ... and {len(tasks) - 10} more')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error creating tasks: {e}'))
                logger.error(f"Error creating tasks: {e}", exc_info=True)
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✨ Log analysis complete!'))
