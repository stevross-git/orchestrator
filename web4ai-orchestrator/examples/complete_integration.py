# examples/complete_integration.py - Complete Integration Example
"""
Complete example showing how to integrate all orchestrator components
This demonstrates a production-ready setup with all features enabled
"""

import asyncio
import logging
import signal
import sys
import os
from typing import Dict, Any
from datetime import datetime

# Import all orchestrator components
from web4ai_orchestrator import Web4AIOrchestrator
from orchestrator_api import OrchestratorAPI, OrchestratorConfig
from security.auth_manager import SecurityManager
from monitoring.alert_manager import MonitoringManager
from database.schema import DatabaseManager
from scaling.auto_scaler import AutoScaler
from backup.backup_manager import BackupManager
from analytics.analytics_engine import AnalyticsEngine
from benchmarking.benchmark_suite import BenchmarkSuite

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('orchestrator_complete.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class CompleteOrchestratorSystem:
    """Complete orchestrator system with all components integrated"""
    
    def __init__(self, config_file: str = "orchestrator_config.yaml"):
        self.config = OrchestratorConfig(config_file)
        self.components = {}
        self.running = False
        
        logger.info("🚀 Initializing Complete Orchestrator System")
        
        # Initialize all components
        self._initialize_components()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _initialize_components(self):
        """Initialize all orchestrator components"""
        try:
            # 1. Database Manager
            logger.info("📊 Initializing Database Manager...")
            self.components['database'] = DatabaseManager(self.config.config)
            
            # 2. Core Orchestrator
            logger.info("🎛️ Initializing Core Orchestrator...")
            self.components['orchestrator'] = Web4AIOrchestrator(
                orchestrator_id=self.config.config.get('orchestrator', {}).get('id'),
                config=self.config.config
            )
            
            # 3. Security Manager
            logger.info("🔐 Initializing Security Manager...")
            self.components['security'] = SecurityManager(
                self.config.config,
                redis_client=getattr(self.components['database'], 'connection', None)
            )
            
            # 4. Monitoring Manager
            logger.info("📈 Initializing Monitoring Manager...")
            self.components['monitoring'] = MonitoringManager(
                self.config.config,
                self.components['orchestrator']
            )
            
            # 5. Auto Scaler
            logger.info("⚖️ Initializing Auto Scaler...")
            self.components['autoscaler'] = AutoScaler(
                self.components['orchestrator'],
                self.config.config
            )
            
            # 6. Backup Manager
            logger.info("💾 Initializing Backup Manager...")
            self.components['backup'] = BackupManager(
                self.config.config,
                self.components['database']
            )
            
            # 7. Analytics Engine
            logger.info("🔍 Initializing Analytics Engine...")
            self.components['analytics'] = AnalyticsEngine(
                self.components['orchestrator'],
                self.components['database']
            )
            
            # 8. API Server
            logger.info("🌐 Initializing API Server...")
            self.components['api'] = OrchestratorAPI(self.config)
            self.components['api'].orchestrator = self.components['orchestrator']
            
            logger.info("✅ All components initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize components: {e}")
            raise
    
    async def start_system(self):
        """Start all orchestrator components"""
        try:
            logger.info("🎬 Starting Complete Orchestrator System...")
            self.running = True
            
            # 1. Start core orchestrator
            logger.info("▶️ Starting Core Orchestrator...")
            await self.components['orchestrator'].start_orchestrator()
            
            # 2. Start monitoring
            logger.info("▶️ Starting Monitoring...")
            self.components['monitoring'].start_monitoring()
            
            # 3. Start auto-scaling
            logger.info("▶️ Starting Auto-scaling...")
            asyncio.create_task(self.components['autoscaler'].start_auto_scaling())
            
            # 4. Start backup service
            logger.info("▶️ Starting Backup Service...")
            self.components['backup'].start_backup_service()
            
            # 5. Start API server in background
            logger.info("▶️ Starting API Server...")
            api_config = self.config.config.get('orchestrator', {})
            api_host = api_config.get('host', '0.0.0.0')
            api_port = api_config.get('port', 9000)
            
            # Run API server in a separate thread
            import threading
            api_thread = threading.Thread(
                target=lambda: self.components['api'].run(host=api_host, port=api_port),
                daemon=True
            )
            api_thread.start()
            
            logger.info("🎉 Complete Orchestrator System started successfully!")
            logger.info(f"🌐 API available at http://{api_host}:{api_port}")
            logger.info(f"📊 Dashboard: http://{api_host}:{api_port}")
            logger.info(f"🔍 Health: http://{api_host}:{api_port}/api/v1/health")
            
            # Run system monitoring loop
            await self._system_monitoring_loop()
            
        except Exception as e:
            logger.error(f"❌ Failed to start system: {e}")
            await self.stop_system()
            raise
    
    async def stop_system(self):
        """Stop all orchestrator components gracefully"""
        logger.info("🛑 Stopping Complete Orchestrator System...")
        self.running = False
        
        try:
            # Stop components in reverse order
            if 'backup' in self.components:
                self.components['backup'].stop_backup_service()
            
            if 'autoscaler' in self.components:
                self.components['autoscaler'].stop_auto_scaling()
            
            if 'monitoring' in self.components:
                self.components['monitoring'].stop_monitoring()
            
            if 'orchestrator' in self.components:
                await self.components['orchestrator'].stop_orchestrator()
            
            if 'database' in self.components:
                self.components['database'].close()
            
            logger.info("✅ System stopped gracefully")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")
    
    async def _system_monitoring_loop(self):
        """Main system monitoring loop"""
        while self.running:
            try:
                # Check system health
                await self._check_system_health()
                
                # Generate periodic reports
                await self._generate_periodic_reports()
                
                # Sleep for 60 seconds
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ System monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _check_system_health(self):
        """Check overall system health"""
        try:
            # Get network status
            status = await self.components['orchestrator'].get_network_status()
            
            # Log key metrics
            active_nodes = status['nodes']['active']
            pending_tasks = status['tasks']['pending']
            utilization = status['performance']['network_utilization']
            
            if active_nodes == 0:
                logger.warning("⚠️ No active nodes available")
            elif pending_tasks > 100:
                logger.warning(f"⚠️ High task queue: {pending_tasks} pending tasks")
            elif utilization > 0.9:
                logger.warning(f"⚠️ High utilization: {utilization:.1%}")
            else:
                logger.debug(f"✅ System healthy: {active_nodes} nodes, {pending_tasks} pending, {utilization:.1%} util")
                
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
    
    async def _generate_periodic_reports(self):
        """Generate periodic analytics reports"""
        try:
            current_time = datetime.utcnow()
            
            # Generate daily report at midnight
            if current_time.hour == 0 and current_time.minute < 2:
                logger.info("📊 Generating daily analytics report...")
                report = self.components['analytics'].generate_comprehensive_report(days=1)
                
                # Save report
                report_filename = f"daily_report_{current_time.strftime('%Y%m%d')}.json"
                with open(f"reports/{report_filename}", 'w') as f:
                    f.write(report.to_json())
                
                logger.info(f"📈 Daily report saved: {report_filename}")
            
            # Generate weekly report on Sundays
            if current_time.weekday() == 6 and current_time.hour == 1:  # Sunday at 1 AM
                logger.info("📊 Generating weekly analytics report...")
                report = self.components['analytics'].generate_comprehensive_report(days=7)
                
                # Save and potentially email report
                report_filename = f"weekly_report_{current_time.strftime('%Y%m%d')}.json"
                with open(f"reports/{report_filename}", 'w') as f:
                    f.write(report.to_json())
                
                logger.info(f"📈 Weekly report saved: {report_filename}")
                
        except Exception as e:
            logger.error(f"❌ Report generation failed: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
        self.running = False
        
        # Run shutdown in the event loop
        loop = asyncio.get_event_loop()
        loop.create_task(self.stop_system())
    
    def run_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive benchmark suite"""
        logger.info("🏃 Running benchmark suite...")
        
        benchmark = BenchmarkSuite(
            orchestrator_url=f"http://localhost:{self.config.config.get('orchestrator', {}).get('port', 9000)}"
        )
        
        results = benchmark.run_full_benchmark()
        
        # Save benchmark results
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        benchmark_file = f"benchmarks/benchmark_{timestamp}.json"
        
        os.makedirs('benchmarks', exist_ok=True)
        with open(benchmark_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"📊 Benchmark completed, results saved to {benchmark_file}")
        logger.info(f"🏆 Overall score: {results.get('overall_score', 0):.1f}/100")
        
        return results
    
    def create_backup(self) -> Dict[str, Any]:
        """Create system backup"""
        logger.info("💾 Creating system backup...")
        
        backup_result = self.components['backup'].create_full_backup()
        
        if 'error' not in backup_result:
            logger.info(f"✅ Backup created: {backup_result.get('backup_id')}")
        else:
            logger.error(f"❌ Backup failed: {backup_result['error']}")
        
        return backup_result
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            # Get status from all components
            status = {
                'timestamp': datetime.utcnow().isoformat(),
                'system_running': self.running,
                'components': {}
            }
            
            # Orchestrator status
            if 'orchestrator' in self.components:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                orchestrator_status = loop.run_until_complete(
                    self.components['orchestrator'].get_network_status()
                )
                loop.close()
                status['components']['orchestrator'] = orchestrator_status
            
            # Monitoring status
            if 'monitoring' in self.components:
                monitoring_data = self.components['monitoring'].get_monitoring_dashboard_data()
                status['components']['monitoring'] = {
                    'active_alerts': len(monitoring_data.get('alerts', {}).get('active', [])),
                    'health_checks': monitoring_data.get('health_checks', {})
                }
            
            # Database status
            if 'database' in self.components:
                status['components']['database'] = {
                    'type': self.components['database'].storage_type,
                    'connected': True  # Simplified check
                }
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Failed to get system status: {e}")
            return {'error': str(e)}

# CLI Interface
class OrchestratorCLI:
    """Command-line interface for orchestrator management"""
    
    def __init__(self):
        self.system = None
    
    def run(self):
        """Run CLI interface"""
        import argparse
        
        parser = argparse.ArgumentParser(description='Web4AI Orchestrator Management')
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Start command
        start_parser = subparsers.add_parser('start', help='Start the orchestrator system')
        start_parser.add_argument('--config', default='orchestrator_config.yaml', help='Configuration file')
        start_parser.add_argument('--daemon', action='store_true', help='Run as daemon')
        
        # Stop command
        subparsers.add_parser('stop', help='Stop the orchestrator system')
        
        # Status command
        subparsers.add_parser('status', help='Get system status')
        
        # Backup command
        backup_parser = subparsers.add_parser('backup', help='Create system backup')
        backup_parser.add_argument('--restore', help='Restore from backup ID')
        
        # Benchmark command
        subparsers.add_parser('benchmark', help='Run benchmark suite')
        
        # Report command
        report_parser = subparsers.add_parser('report', help='Generate analytics report')
        report_parser.add_argument('--days', type=int, default=7, help='Number of days to analyze')
        report_parser.add_argument('--format', choices=['json', 'html', 'pdf'], default='json', help='Report format')
        
        # Config command
        config_parser = subparsers.add_parser('config', help='Configuration management')
        config_parser.add_argument('--generate', action='store_true', help='Generate default config')
        config_parser.add_argument('--validate', action='store_true', help='Validate config')
        
        args = parser.parse_args()
        
        if args.command == 'start':
            self._start_system(args)
        elif args.command == 'stop':
            self._stop_system()
        elif args.command == 'status':
            self._show_status()
        elif args.command == 'backup':
            self._manage_backup(args)
        elif args.command == 'benchmark':
            self._run_benchmark()
        elif args.command == 'report':
            self._generate_report(args)
        elif args.command == 'config':
            self._manage_config(args)
        else:
            parser.print_help()
    
    def _start_system(self, args):
        """Start orchestrator system"""
        try:
            self.system = CompleteOrchestratorSystem(args.config)
            
            if args.daemon:
                # Run as daemon
                import daemon
                with daemon.DaemonContext():
                    asyncio.run(self.system.start_system())
            else:
                # Run in foreground
                asyncio.run(self.system.start_system())
                
        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested by user")
        except Exception as e:
            print(f"❌ Failed to start system: {e}")
            sys.exit(1)
    
    def _stop_system(self):
        """Stop orchestrator system"""
        # This would typically send a signal to the running process
        print("🛑 Stopping orchestrator system...")
        print("   (This would send SIGTERM to running process)")
    
    def _show_status(self):
        """Show system status"""
        if not self.system:
            print("❌ System not running")
            return
        
        status = self.system.get_system_status()
        print(f"📊 System Status:")
        print(f"   Running: {status.get('system_running', False)}")
        print(f"   Timestamp: {status.get('timestamp', 'Unknown')}")
        
        components = status.get('components', {})
        for component, data in components.items():
            print(f"   {component.title()}: {'✅' if data else '❌'}")
    
    def _manage_backup(self, args):
        """Manage backups"""
        if not self.system:
            print("❌ System not initialized")
            return
        
        if args.restore:
            print(f"💾 Restoring from backup: {args.restore}")
            # Implement restore logic
        else:
            print("💾 Creating backup...")
            result = self.system.create_backup()
            if 'error' not in result:
                print(f"✅ Backup created: {result.get('backup_id')}")
            else:
                print(f"❌ Backup failed: {result['error']}")
    
    def _run_benchmark(self):
        """Run benchmark suite"""
        if not self.system:
            self.system = CompleteOrchestratorSystem()
        
        print("🏃 Running benchmark suite...")
        results = self.system.run_benchmark()
        print(f"🏆 Overall score: {results.get('overall_score', 0):.1f}/100")
    
    def _generate_report(self, args):
        """Generate analytics report"""
        if not self.system:
            self.system = CompleteOrchestratorSystem()
        
        print(f"📊 Generating {args.days}-day report in {args.format} format...")
        
        report = self.system.components['analytics'].generate_comprehensive_report(args.days)
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        if args.format == 'json':
            filename = f"report_{timestamp}.json"
            with open(filename, 'w') as f:
                f.write(report.to_json())
            print(f"📈 Report saved: {filename}")
        
        elif args.format == 'html':
            filename = f"report_{timestamp}.html"
            html_content = self.system.components['analytics'].export_report_html(report)
            with open(filename, 'w') as f:
                f.write(html_content)
            print(f"📈 Report saved: {filename}")
        
        elif args.format == 'pdf':
            filename = f"report_{timestamp}.pdf"
            pdf_content = self.system.components['analytics'].export_report_pdf(report)
            with open(filename, 'wb') as f:
                f.write(pdf_content)
            print(f"📈 Report saved: {filename}")
    
    def _manage_config(self, args):
        """Manage configuration"""
        if args.generate:
            print("🔧 Generating default configuration...")
            config = OrchestratorConfig()
            config.save_config()
            print("✅ Default configuration generated: orchestrator_config.yaml")
        
        elif args.validate:
            print("🔍 Validating configuration...")
            try:
                config = OrchestratorConfig()
                print("✅ Configuration is valid")
            except Exception as e:
                print(f"❌ Configuration invalid: {e}")

# Example usage and integration patterns
def example_basic_usage():
    """Example: Basic orchestrator usage"""
    
    async def basic_example():
        # Initialize system
        system = CompleteOrchestratorSystem()
        
        try:
            # Start system
            await system.start_system()
            
            # System will run until interrupted
            
        except KeyboardInterrupt:
            print("Shutting down...")
        finally:
            await system.stop_system()
    
    asyncio.run(basic_example())

def example_programmatic_control():
    """Example: Programmatic control of orchestrator"""
    
    from web4ai_client import Web4AIClient
    
    # Start orchestrator system
    system = CompleteOrchestratorSystem()
    
    # Start in background thread
    import threading
    system_thread = threading.Thread(
        target=lambda: asyncio.run(system.start_system()),
        daemon=True
    )
    system_thread.start()
    
    # Wait for system to start
    time.sleep(10)
    
    # Use client to interact with orchestrator
    client = Web4AIClient("http://localhost:9000")
    
    # Check health
    health = client.health_check()
    print(f"Orchestrator health: {health['status']}")
    
    # Register a node
    client.register_node(
        node_id="example-node-001",
        host="localhost",
        port=8080,
        capabilities=["ai_inference", "data_processing"]
    )
    
    # Submit tasks
    for i in range(10):
        task_id = client.submit_task(
            task_type="example_task",
            input_data={"iteration": i},
            priority=client.TaskPriority.NORMAL
        )
        print(f"Submitted task: {task_id}")
    
    # Monitor tasks
    tasks = client.get_tasks()
    print(f"Current tasks: {len(tasks['pending'])} pending, {len(tasks['active'])} active")
    
    # Get analytics
    time.sleep(30)  # Wait for some data
    report = system.components['analytics'].generate_comprehensive_report(days=1)
    print(f"Analytics report generated: {report.title}")

def example_custom_integration():
    """Example: Custom integration with existing infrastructure"""
    
    class CustomOrchestratorIntegration:
        """Custom integration example"""
        
        def __init__(self, existing_config):
            self.existing_config = existing_config
            
            # Create custom configuration
            orchestrator_config = {
                'orchestrator': {
                    'id': 'custom_orchestrator',
                    'port': existing_config.get('orchestrator_port', 9000)
                },
                'network': {
                    'discovery_endpoints': existing_config.get('node_endpoints', [])
                },
                'storage': {
                    'type': existing_config.get('database_type', 'redis'),
                    'redis': existing_config.get('redis_config', {})
                }
            }
            
            # Initialize orchestrator with custom config
            self.orchestrator_system = CompleteOrchestratorSystem()
            self.orchestrator_system.config.config.update(orchestrator_config)
        
        async def integrate_with_existing_system(self):
            """Integrate with existing infrastructure"""
            
            # Start orchestrator
            await self.orchestrator_system.start_system()
            
            # Register existing compute nodes
            for node_config in self.existing_config.get('compute_nodes', []):
                await self._register_existing_node(node_config)
            
            # Setup custom monitoring integration
            self._setup_monitoring_integration()
            
            # Setup custom alerting
            self._setup_custom_alerts()
        
        async def _register_existing_node(self, node_config):
            """Register existing compute node"""
            orchestrator = self.orchestrator_system.components['orchestrator']
            
            node_data = {
                'node_id': node_config['id'],
                'host': node_config['host'],
                'port': node_config['port'],
                'node_type': node_config.get('type', 'compute'),
                'capabilities': node_config.get('capabilities', []),
                'version': node_config.get('version', '1.0.0')
            }
            
            await orchestrator.register_node(node_data)
        
        def _setup_monitoring_integration(self):
            """Setup integration with existing monitoring"""
            monitoring = self.orchestrator_system.components['monitoring']
            
            # Add custom alert callback that integrates with existing alerting system
            def custom_alert_handler(alert):
                # Send to existing monitoring system
                self._send_to_existing_monitoring(alert)
            
            monitoring.threshold_monitor.add_alert_callback(custom_alert_handler)
        
        def _setup_custom_alerts(self):
            """Setup custom alerting rules"""
            monitoring = self.orchestrator_system.components['monitoring']
            
            # Add custom thresholds based on existing SLAs
            monitoring.threshold_monitor.add_threshold(
                metric_name="custom_sla_metric",
                critical_threshold=self.existing_config.get('sla_critical', 0.95),
                warning_threshold=self.existing_config.get('sla_warning', 0.98),
                comparison="less"
            )
        
        def _send_to_existing_monitoring(self, alert):
            """Send alert to existing monitoring system"""
            # This would integrate with your existing monitoring infrastructure
            print(f"Sending alert to existing system: {alert.title}")

if __name__ == "__main__":
    # Run CLI interface
    cli = OrchestratorCLI()
    cli.run()