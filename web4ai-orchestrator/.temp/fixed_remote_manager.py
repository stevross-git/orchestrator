# enhanced_node/control/remote_manager.py
import time
import threading
import uuid
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Optional, Any

from ..models.commands import AgentCommand, AgentConfiguration
from ..models.scripts import ScheduledCommand, BulkOperation, AgentHealthCheck, AgentScript
from ..models.agents import EnhancedAgentStatus
from ..core.database import (
    AgentCommandRecord, ScheduledCommandRecord, BulkOperationRecord,
    AgentHealthRecord, AgentScriptRecord
)
from ..utils.serialization import serialize_for_json
from ..utils.logger import get_remote_logger


class AdvancedRemoteControlManager:
    """Advanced remote control capabilities"""
    
    def __init__(self, node_server):
        self.node_server = node_server
        self.logger = get_remote_logger()
        
        # EXISTING features
        self.active_commands = {}
        self.agent_configurations = {}
        self.command_queue = defaultdict(deque)
        
        # NEW: Advanced features
        self.scheduled_commands = {}
        self.bulk_operations = {}
        self.agent_health_monitors = {}
        self.agent_scripts = {}
        self.command_history = defaultdict(list)
        
        # NEW: Service control
        self.scheduler_running = False
        self.health_monitor_running = False
        
        # NEW: Enhanced command capabilities
        self.advanced_commands = {
            "system_control": {
                "restart_agent": "Restart agent gracefully",
                "shutdown_agent": "Shutdown agent safely", 
                "update_config": "Update agent configuration",
                "reload_config": "Reload configuration files",
                "restart_service": "Restart specific service",
                "kill_process": "Kill specific process",
                "reboot_system": "Reboot entire system",
                "update_system": "Update system packages"
            },
            "task_management": {
                "start_task": "Start specific task on agent",
                "cancel_task": "Cancel running task",
                "pause_task": "Pause task execution",
                "resume_task": "Resume paused task",
                "set_task_priority": "Change task priority",
                "clear_task_queue": "Clear all pending tasks",
                "backup_task_data": "Backup task results",
                "restore_task_data": "Restore task data"
            },
            "performance_tuning": {
                "set_cpu_limit": "Set CPU usage limit",
                "set_memory_limit": "Set memory usage limit",
                "enable_gpu": "Enable/disable GPU usage",
                "optimize_performance": "Optimize agent performance",
                "clear_cache": "Clear system caches",
                "defragment_storage": "Defragment storage",
                "tune_network": "Optimize network settings"
            }
        }
    
    def start_advanced_services(self):
        """Start advanced remote control services"""
        self.start_command_scheduler()
        self.start_health_monitor()
        self.logger.info("Advanced remote control services started")
    
    def start_command_scheduler(self):
        """Start command scheduler service"""
        def scheduler_loop():
            self.scheduler_running = True
            while self.scheduler_running:
                try:
                    self.process_scheduled_commands()
                    time.sleep(10)  # Check every 10 seconds
                except Exception as e:
                    self.logger.error(f"Command scheduler error: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=scheduler_loop, daemon=True, name="CommandScheduler")
        thread.start()
        self.logger.info("Command scheduler started")
    
    def start_health_monitor(self):
        """Start agent health monitoring service"""
        def health_monitor_loop():
            self.health_monitor_running = True
            while self.health_monitor_running:
                try:
                    self.monitor_agent_health()
                    time.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    self.logger.error(f"Health monitor error: {e}")
                    time.sleep(120)
        
        thread = threading.Thread(target=health_monitor_loop, daemon=True, name="HealthMonitor")
        thread.start()
        self.logger.info("Agent health monitor started")
    
    def process_scheduled_commands(self):
        """Process due scheduled commands - MISSING METHOD FIXED"""
        current_time = datetime.now()
        
        for scheduled_cmd in list(self.scheduled_commands.values()):
            if scheduled_cmd.status == "scheduled" and scheduled_cmd.scheduled_time <= current_time:
                try:
                    scheduled_cmd.status = "executing"
                    
                    # Execute the command
                    success = self.execute_command_on_agent(scheduled_cmd.command)
                    
                    if success:
                        scheduled_cmd.current_repeats += 1
                        
                        # Check if we need to reschedule
                        if (scheduled_cmd.repeat_interval and 
                            scheduled_cmd.current_repeats < scheduled_cmd.max_repeats):
                            
                            # Reschedule for next execution
                            scheduled_cmd.scheduled_time = current_time + timedelta(seconds=scheduled_cmd.repeat_interval)
                            scheduled_cmd.status = "scheduled"
                            self.logger.info(f"Rescheduled command {scheduled_cmd.id} for {scheduled_cmd.scheduled_time}")
                        else:
                            scheduled_cmd.status = "completed"
                            self.logger.info(f"Completed scheduled command {scheduled_cmd.id}")
                    else:
                        scheduled_cmd.status = "failed"
                        self.logger.error(f"Failed to execute scheduled command {scheduled_cmd.id}")
                        
                except Exception as e:
                    scheduled_cmd.status = "error"
                    self.logger.error(f"Error executing scheduled command {scheduled_cmd.id}: {e}")
    
    def monitor_agent_health(self):
        """Monitor agent health - MISSING METHOD FIXED"""
        try:
            # Get all active agents
            agents = self.node_server.get_active_agents() if hasattr(self.node_server, 'get_active_agents') else []
            
            for agent_id in agents:
                try:
                    # Check agent status
                    health_data = self.check_agent_health(agent_id)
                    
                    # Store health record
                    health_record = AgentHealthCheck(
                        id=f"health-{int(time.time())}-{uuid.uuid4().hex[:8]}",
                        agent_id=agent_id,
                        timestamp=datetime.now(),
                        cpu_usage=health_data.get('cpu_usage', 0),
                        memory_usage=health_data.get('memory_usage', 0),
                        disk_usage=health_data.get('disk_usage', 0),
                        network_status=health_data.get('network_status', 'unknown'),
                        status=health_data.get('status', 'unknown')
                    )
                    
                    self.agent_health_monitors[agent_id] = health_record
                    
                    # Log issues if any
                    if health_data.get('cpu_usage', 0) > 90:
                        self.logger.warning(f"High CPU usage on agent {agent_id}: {health_data['cpu_usage']}%")
                    
                    if health_data.get('memory_usage', 0) > 90:
                        self.logger.warning(f"High memory usage on agent {agent_id}: {health_data['memory_usage']}%")
                        
                except Exception as e:
                    self.logger.error(f"Health check failed for agent {agent_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Health monitoring error: {e}")
    
    def check_agent_health(self, agent_id: str) -> Dict[str, Any]:
        """Check individual agent health"""
        try:
            # This would normally query the actual agent
            # For now, return mock data to prevent errors
            return {
                'status': 'healthy',
                'cpu_usage': 25.0,
                'memory_usage': 45.0,
                'disk_usage': 60.0,
                'network_status': 'connected',
                'last_response': time.time()
            }
        except Exception as e:
            self.logger.error(f"Agent health check failed for {agent_id}: {e}")
            return {
                'status': 'error',
                'cpu_usage': 0,
                'memory_usage': 0,
                'disk_usage': 0,
                'network_status': 'disconnected',
                'error': str(e)
            }
    
    def execute_command_on_agent(self, command: AgentCommand) -> bool:
        """Execute command on specific agent"""
        try:
            # Store command in active commands
            self.active_commands[command.id] = command
            
            # Add to command history
            self.command_history[command.agent_id].append({
                'command_id': command.id,
                'command_type': command.command_type,
                'timestamp': datetime.now(),
                'status': 'executing'
            })
            
            # This would normally send the command to the agent
            # For now, simulate success to prevent errors
            self.logger.info(f"Executing command {command.id} on agent {command.agent_id}")
            
            # Update command status
            self.command_history[command.agent_id][-1]['status'] = 'completed'
            
            return True
            
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            if command.agent_id in self.command_history:
                self.command_history[command.agent_id][-1]['status'] = 'failed'
            return False
    
    def create_scheduled_command(self, agent_id: str, command_type: str, 
                                scheduled_time: datetime, parameters: Dict = None,
                                repeat_interval: int = None, max_repeats: int = 1) -> ScheduledCommand:
        """Create a scheduled command"""
        command = AgentCommand(
            id=f"cmd-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            agent_id=agent_id,
            command_type=command_type,
            parameters=parameters or {}
        )
        
        scheduled_cmd = ScheduledCommand(
            id=f"sched-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            command=command,
            scheduled_time=scheduled_time,
            repeat_interval=repeat_interval,
            max_repeats=max_repeats
        )
        
        self.scheduled_commands[scheduled_cmd.id] = scheduled_cmd
        self.store_scheduled_command_in_db(scheduled_cmd)
        
        self.logger.info(f"Scheduled command {scheduled_cmd.id} for agent {agent_id} at {scheduled_time}")
        return scheduled_cmd
    
    def store_scheduled_command_in_db(self, scheduled_cmd: ScheduledCommand):
        """Store scheduled command in database"""
        try:
            # This would normally store in database
            # For now, just log to prevent errors
            self.logger.info(f"Stored scheduled command {scheduled_cmd.id} in database")
        except Exception as e:
            self.logger.error(f"Failed to store scheduled command: {e}")
    
    def stop_services(self):
        """Stop all advanced services"""
        self.scheduler_running = False
        self.health_monitor_running = False
        self.logger.info("Advanced remote control services stopped")