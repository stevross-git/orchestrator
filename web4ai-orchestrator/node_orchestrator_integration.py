# enhanced_node/core/orchestrator_client.py
import requests
import time
import threading
import logging
from typing import Dict, Any, Optional
import psutil
import uuid
from datetime import datetime

class OrchestratorClient:
    """Client for registering and communicating with the Web4AI Orchestrator"""
    
    def __init__(self, node_server, orchestrator_url: str = "http://localhost:9000"):
        self.node_server = node_server
        self.orchestrator_url = orchestrator_url
        self.node_id = f"enhanced-node-{uuid.uuid4().hex[:12]}"
        self.registered = False
        self.heartbeat_running = False
        self.logger = logging.getLogger("OrchestratorClient")
        
    def register_with_orchestrator(self) -> bool:
        """Register this node with the orchestrator"""
        try:
            registration_data = {
                'node_id': self.node_id,
                'host': getattr(self.node_server, 'host', 'localhost'),
                'port': getattr(self.node_server, 'port', 8090),
                'node_type': 'enhanced_node',
                'capabilities': self.get_node_capabilities(),
                'agents_count': len(getattr(self.node_server, 'active_agents', {})),
                'version': '3.4.0-advanced-remote-control',
                'location': 'default'
            }
            
            response = requests.post(
                f"{self.orchestrator_url}/api/v1/nodes/{self.node_id}/register",
                json=registration_data,
                timeout=10
            )
            
            if response.status_code == 200:
                self.registered = True
                self.logger.info(f"✅ Successfully registered with orchestrator: {self.node_id}")
                self.start_heartbeat()
                return True
            else:
                self.logger.error(f"❌ Registration failed: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            self.logger.warning("⚠️ Orchestrator not available - running in standalone mode")
            return False
        except Exception as e:
            self.logger.error(f"❌ Registration error: {e}")
            return False
    
    def get_node_capabilities(self) -> list:
        """Get node capabilities"""
        capabilities = [
            "task_execution",
            "remote_control", 
            "health_monitoring",
            "script_deployment",
            "performance_monitoring"
        ]
        
        # Add GPU capability if available
        try:
            import torch
            if torch.cuda.is_available():
                capabilities.append("gpu_processing")
        except ImportError:
            pass
            
        return capabilities
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            return {
                'cpu_usage': psutil.cpu_percent(interval=1),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'network_connections': len(psutil.net_connections()),
                'load_score': self.calculate_load_score()
            }
        except Exception as e:
            self.logger.error(f"Error getting system metrics: {e}")
            return {
                'cpu_usage': 0,
                'memory_usage': 0, 
                'disk_usage': 0,
                'network_connections': 0,
                'load_score': 0.5
            }
    
    def calculate_load_score(self) -> float:
        """Calculate node load score (0.0 = idle, 1.0 = fully loaded)"""
        try:
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
            # Simple load calculation
            load_score = (cpu + memory) / 200.0
            return min(1.0, max(0.0, load_score))
        except:
            return 0.5
    
    def send_heartbeat(self) -> bool:
        """Send heartbeat to orchestrator"""
        try:
            metrics = self.get_system_metrics()
            heartbeat_data = {
                'node_id': self.node_id,
                'status': 'active',
                'timestamp': datetime.now().isoformat(),
                'cpu_usage': metrics['cpu_usage'],
                'memory_usage': metrics['memory_usage'],
                'agents_status': self.get_agents_status(),
                'load_score': metrics['load_score'],
                'tasks_running': len(getattr(self.node_server, 'active_tasks', {}))
            }
            
            response = requests.post(
                f"{self.orchestrator_url}/api/v1/nodes/{self.node_id}/heartbeat",
                json=heartbeat_data,
                timeout=5
            )
            
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Heartbeat failed: {e}")
            return False
    
    def get_agents_status(self) -> Dict[str, Any]:
        """Get status of all agents on this node"""
        try:
            if hasattr(self.node_server, 'get_active_agents'):
                agents = self.node_server.get_active_agents()
                return {
                    'total_agents': len(agents),
                    'active_agents': len([a for a in agents if getattr(a, 'status', 'unknown') == 'active']),
                    'agent_list': list(agents.keys()) if isinstance(agents, dict) else []
                }
            else:
                return {
                    'total_agents': 0,
                    'active_agents': 0,
                    'agent_list': []
                }
        except Exception as e:
            self.logger.error(f"Error getting agents status: {e}")
            return {'total_agents': 0, 'active_agents': 0, 'agent_list': []}
    
    def start_heartbeat(self):
        """Start heartbeat thread"""
        if self.heartbeat_running:
            return
            
        def heartbeat_loop():
            self.heartbeat_running = True
            while self.heartbeat_running and self.registered:
                try:
                    success = self.send_heartbeat()
                    if not success:
                        self.logger.warning("Heartbeat failed - orchestrator may be down")
                    time.sleep(30)  # Send heartbeat every 30 seconds
                except Exception as e:
                    self.logger.error(f"Heartbeat loop error: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=heartbeat_loop, daemon=True, name="OrchestratorHeartbeat")
        thread.start()
        self.logger.info("Heartbeat thread started")
    
    def stop_heartbeat(self):
        """Stop heartbeat"""
        self.heartbeat_running = False
        self.registered = False
    
    def receive_task_from_orchestrator(self, task_data: Dict[str, Any]) -> bool:
        """Receive and process task from orchestrator"""
        try:
            task_id = task_data.get('task_id')
            task_type = task_data.get('task_type')
            
            self.logger.info(f"Received task {task_id} of type {task_type} from orchestrator")
            
            # Forward task to node server's task manager
            if hasattr(self.node_server, 'process_orchestrator_task'):
                return self.node_server.process_orchestrator_task(task_data)
            else:
                self.logger.warning("Node server doesn't support orchestrator tasks")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing orchestrator task: {e}")
            return False

# Add this to your enhanced_node/core/server.py
class EnhancedNodeServerAdvanced:
    def __init__(self, *args, **kwargs):
        # ... existing initialization ...
        
        # Add orchestrator client
        self.orchestrator_client = OrchestratorClient(self)
        
    def start_server(self):
        """Start the server and register with orchestrator"""
        # ... existing server startup code ...
        
        # Try to register with orchestrator
        self.orchestrator_client.register_with_orchestrator()
        
    def process_orchestrator_task(self, task_data: Dict[str, Any]) -> bool:
        """Process task received from orchestrator"""
        try:
            # Implement task processing logic here
            task_id = task_data.get('task_id')
            self.logger.info(f"Processing orchestrator task: {task_id}")
            
            # Add task to internal queue or process directly
            # This depends on your existing task management system
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to process orchestrator task: {e}")
            return False