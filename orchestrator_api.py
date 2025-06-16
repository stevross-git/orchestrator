#!/usr/bin/env python3
"""
Web4AI Orchestrator API & Configuration
RESTful API interface and configuration management for the orchestrator
"""

from flask import Flask, request, jsonify, g
from flask_cors import CORS
import asyncio
import threading
import json
import os
import yaml
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from functools import wraps

# Import the main orchestrator
from web4ai_orchestrator import Web4AIOrchestrator, TaskRequest, TaskPriority, NodeStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrchestratorConfig:
    """Configuration management for the orchestrator"""
    
    def __init__(self, config_file: str = "orchestrator_config.yaml"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        default_config = {
            'orchestrator': {
                'id': 'web4ai_main_orchestrator',
                'port': 9000,
                'host': '0.0.0.0',
                'heartbeat_interval': 30,
                'task_timeout': 300,
                'max_retries': 3,
                'auto_discovery': True,
                'security_enabled': True
            },
            'network': {
                'discovery_endpoints': [
                    'http://localhost:8080',
                    'http://localhost:8081', 
                    'http://localhost:8082'
                ],
                'load_balance_algorithm': 'weighted_round_robin',
                'fault_tolerance_enabled': True,
                'auto_scaling_enabled': True,
                'max_nodes': 100,
                'min_nodes': 1
            },
            'performance': {
                'monitoring_enabled': True,
                'optimization_enabled': True,
                'metrics_retention_days': 7,
                'performance_threshold': 0.8,
                'cpu_threshold': 80,
                'memory_threshold': 85,
                'latency_threshold': 1000
            },
            'security': {
                'api_key_required': True,
                'rate_limiting': True,
                'max_requests_per_minute': 100,
                'encryption_enabled': True,
                'audit_logging': True
            },
            'storage': {
                'type': 'local',  # local, redis, mongodb
                'path': './orchestrator_data',
                'backup_enabled': True,
                'backup_interval_hours': 6
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    file_config = yaml.safe_load(f)
                    # Merge with defaults
                    self._deep_merge(default_config, file_config)
            except Exception as e:
                logger.error(f"Failed to load config file: {e}")
        
        return default_config
    
    def _deep_merge(self, base: Dict, override: Dict):
        """Deep merge configuration dictionaries"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def get(self, key_path: str, default=None):
        """Get configuration value using dot notation"""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any):
        """Set configuration value using dot notation"""
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value

class OrchestratorAPI:
    """RESTful API for the Web4AI Orchestrator"""
    
    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Initialize orchestrator
        self.orchestrator = Web4AIOrchestrator(
            orchestrator_id=config.get('orchestrator.id'),
            config=config.config
        )
        
        # Background thread for orchestrator
        self.orchestrator_thread = None
        self.loop = None
        
        # API statistics
        self.api_stats = {
            'requests_total': 0,
            'requests_successful': 0,
            'requests_failed': 0,
            'start_time': datetime.now().isoformat()
        }
        
        self._setup_routes()
        self._setup_middleware()
    
    def _setup_middleware(self):
        """Setup API middleware"""
        
        @self.app.before_request
        def before_request():
            g.start_time = datetime.now()
            self.api_stats['requests_total'] += 1
            
            # API key validation (if enabled)
            if self.config.get('security.api_key_required'):
                api_key = request.headers.get('X-API-Key')
                if not api_key or not self._validate_api_key(api_key):
                    return jsonify({'error': 'Invalid API key'}), 401
        
        @self.app.after_request
        def after_request(response):
            duration = (datetime.now() - g.start_time).total_seconds()
            
            if response.status_code < 400:
                self.api_stats['requests_successful'] += 1
            else:
                self.api_stats['requests_failed'] += 1
            
            # Add timing header
            response.headers['X-Response-Time'] = f"{duration:.3f}s"
            
            return response
    
    def _validate_api_key(self, api_key: str) -> bool:
        """Validate API key (implement your validation logic)"""
        # For demo purposes, accept any non-empty key
        return bool(api_key)
    
    def _setup_routes(self):
        """Setup API routes"""
        
        # Health and status endpoints
        @self.app.route('/api/v1/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'orchestrator_id': self.orchestrator.orchestrator_id,
                'timestamp': datetime.now().isoformat(),
                'version': '1.0.0'
            })
        
        @self.app.route('/api/v1/status', methods=['GET'])
        def status():
            """Get orchestrator status"""
            try:
                network_status = self.orchestrator.get_network_status()
                return jsonify({
                    'success': True,
                    'data': network_status,
                    'api_stats': self.api_stats
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # Node management endpoints
        @self.app.route('/api/v1/nodes', methods=['GET'])
        def get_nodes():
            """Get all nodes in the network"""
            try:
                nodes = {node_id: node.__dict__ for node_id, node in self.orchestrator.nodes.items()}
                return jsonify({
                    'success': True,
                    'nodes': nodes,
                    'total_nodes': len(nodes)
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/v1/nodes/<node_id>', methods=['GET'])
        def get_node(node_id):
            """Get specific node information"""
            try:
                if node_id not in self.orchestrator.nodes:
                    return jsonify({'success': False, 'error': 'Node not found'}), 404
                
                node = self.orchestrator.nodes[node_id]
                agents = [self.orchestrator.agents[aid].__dict__ 
                         for aid in self.orchestrator.node_agents[node_id]]
                
                return jsonify({
                    'success': True,
                    'node': node.__dict__,
                    'agents': agents
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/v1/nodes/<node_id>/status', methods=['PUT'])
        def update_node_status(node_id):
            """Update node status"""
            try:
                data = request.get_json()
                new_status = data.get('status')
                
                if node_id not in self.orchestrator.nodes:
                    return jsonify({'success': False, 'error': 'Node not found'}), 404
                
                if new_status not in [s.value for s in NodeStatus]:
                    return jsonify({'success': False, 'error': 'Invalid status'}), 400
                
                self.orchestrator.nodes[node_id].status = NodeStatus(new_status)
                
                return jsonify({
                    'success': True,
                    'message': f'Node {node_id} status updated to {new_status}'
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # Agent management endpoints
        @self.app.route('/api/v1/agents', methods=['GET'])
        def get_agents():
            """Get all agents in the network"""
            try:
                agents = {agent_id: agent.__dict__ for agent_id, agent in self.orchestrator.agents.items()}
                return jsonify({
                    'success': True,
                    'agents': agents,
                    'total_agents': len(agents)
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/v1/agents/<agent_id>', methods=['GET'])
        def get_agent(agent_id):
            """Get specific agent information"""
            try:
                if agent_id not in self.orchestrator.agents:
                    return jsonify({'success': False, 'error': 'Agent not found'}), 404
                
                agent = self.orchestrator.agents[agent_id]
                return jsonify({
                    'success': True,
                    'agent': agent.__dict__
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # Task management endpoints
        @self.app.route('/api/v1/tasks', methods=['POST'])
        def submit_task():
            """Submit a new task"""
            try:
                data = request.get_json()
                
                # Validate required fields
                required_fields = ['task_type', 'input_data']
                for field in required_fields:
                    if field not in data:
                        return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
                
                # Create task request
                task_request = TaskRequest(
                    task_id=data.get('task_id'),
                    task_type=data['task_type'],
                    priority=TaskPriority(data.get('priority', TaskPriority.NORMAL.value)),
                    requirements=data.get('requirements', {}),
                    input_data=data['input_data'],
                    timeout=data.get('timeout', 300.0),
                    max_retries=data.get('max_retries', 3)
                )
                
                # Submit task asynchronously
                future = asyncio.run_coroutine_threadsafe(
                    self.orchestrator.submit_task(task_request), 
                    self.loop
                )
                task_id = future.result(timeout=10)
                
                return jsonify({
                    'success': True,
                    'task_id': task_id,
                    'message': 'Task submitted successfully'
                })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/v1/tasks', methods=['GET'])
        def get_tasks():
            """Get task status"""
            try:
                return jsonify({
                    'success': True,
                    'tasks': {
                        'active': list(self.orchestrator.active_tasks.keys()),
                        'pending': len(self.orchestrator.pending_tasks),
                        'completed': len(self.orchestrator.completed_tasks),
                        'failed': len(self.orchestrator.failed_tasks)
                    }
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/v1/tasks/<task_id>', methods=['GET'])
        def get_task_status(task_id):
            """Get specific task status"""
            try:
                if task_id in self.orchestrator.active_tasks:
                    task = self.orchestrator.active_tasks[task_id]
                    return jsonify({
                        'success': True,
                        'task_id': task_id,
                        'status': 'active',
                        'task': task.__dict__
                    })
                elif task_id in self.orchestrator.completed_tasks:
                    return jsonify({
                        'success': True,
                        'task_id': task_id,
                        'status': 'completed',
                        'result': self.orchestrator.completed_tasks[task_id]
                    })
                elif task_id in self.orchestrator.failed_tasks:
                    return jsonify({
                        'success': True,
                        'task_id': task_id,
                        'status': 'failed',
                        'error': self.orchestrator.failed_tasks[task_id]
                    })
                else:
                    return jsonify({'success': False, 'error': 'Task not found'}), 404
                    
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # Configuration endpoints
        @self.app.route('/api/v1/config', methods=['GET'])
        def get_config():
            """Get orchestrator configuration"""
            try:
                return jsonify({
                    'success': True,
                    'config': self.config.config
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/v1/config/<path:key_path>', methods=['PUT'])
        def update_config(key_path):
            """Update configuration value"""
            try:
                data = request.get_json()
                value = data.get('value')
                
                self.config.set(key_path, value)
                self.config.save_config()
                
                return jsonify({
                    'success': True,
                    'message': f'Configuration {key_path} updated'
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # Metrics and monitoring endpoints
        @self.app.route('/api/v1/metrics', methods=['GET'])
        def get_metrics():
            """Get performance metrics"""
            try:
                return jsonify({
                    'success': True,
                    'network_metrics': self.orchestrator.network_metrics,
                    'api_stats': self.api_stats,
                    'load_balancer_stats': self.orchestrator.load_balancer.node_weights,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/v1/metrics/performance', methods=['GET'])
        def get_performance_metrics():
            """Get detailed performance metrics"""
            try:
                # Calculate additional metrics
                active_nodes = [n for n in self.orchestrator.nodes.values() 
                               if n.status == NodeStatus.ACTIVE]
                
                if active_nodes:
                    avg_cpu = sum(n.cpu_usage for n in active_nodes) / len(active_nodes)
                    avg_memory = sum(n.memory_usage for n in active_nodes) / len(active_nodes)
                    avg_latency = sum(n.network_latency for n in active_nodes) / len(active_nodes)
                else:
                    avg_cpu = avg_memory = avg_latency = 0
                
                return jsonify({
                    'success': True,
                    'performance': {
                        'network_utilization': self.orchestrator.network_metrics['network_utilization'],
                        'average_cpu_usage': avg_cpu,
                        'average_memory_usage': avg_memory,
                        'average_network_latency': avg_latency,
                        'total_nodes': len(self.orchestrator.nodes),
                        'active_nodes': len(active_nodes),
                        'task_throughput': self._calculate_task_throughput(),
                        'success_rate': self._calculate_success_rate()
                    }
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # Control endpoints
        @self.app.route('/api/v1/control/start', methods=['POST'])
        def start_orchestrator():
            """Start the orchestrator"""
            try:
                if not self.orchestrator.running:
                    self._start_orchestrator_background()
                    return jsonify({
                        'success': True,
                        'message': 'Orchestrator started'
                    })
                else:
                    return jsonify({
                        'success': True,
                        'message': 'Orchestrator already running'
                    })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/v1/control/stop', methods=['POST'])
        def stop_orchestrator():
            """Stop the orchestrator"""
            try:
                if self.orchestrator.running:
                    future = asyncio.run_coroutine_threadsafe(
                        self.orchestrator.stop_orchestrator(), 
                        self.loop
                    )
                    future.result(timeout=30)
                    
                    return jsonify({
                        'success': True,
                        'message': 'Orchestrator stopped'
                    })
                else:
                    return jsonify({
                        'success': True,
                        'message': 'Orchestrator not running'
                    })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/v1/control/restart', methods=['POST'])
        def restart_orchestrator():
            """Restart the orchestrator"""
            try:
                # Stop if running
                if self.orchestrator.running:
                    future = asyncio.run_coroutine_threadsafe(
                        self.orchestrator.stop_orchestrator(), 
                        self.loop
                    )
                    future.result(timeout=30)
                
                # Start again
                self._start_orchestrator_background()
                
                return jsonify({
                    'success': True,
                    'message': 'Orchestrator restarted'
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
    
    def _calculate_task_throughput(self) -> float:
        """Calculate tasks per minute"""
        uptime_minutes = (datetime.now().timestamp() - self.orchestrator.network_metrics['uptime']) / 60
        if uptime_minutes > 0:
            return self.orchestrator.network_metrics['tasks_completed'] / uptime_minutes
        return 0.0
    
    def _calculate_success_rate(self) -> float:
        """Calculate task success rate"""
        total_tasks = (self.orchestrator.network_metrics['tasks_completed'] + 
                      self.orchestrator.network_metrics['tasks_failed'])
        if total_tasks > 0:
            return (self.orchestrator.network_metrics['tasks_completed'] / total_tasks) * 100
        return 100.0
    
    def _start_orchestrator_background(self):
        """Start orchestrator in background thread"""
        def run_orchestrator():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.orchestrator.start_orchestrator())
        
        self.orchestrator_thread = threading.Thread(target=run_orchestrator, daemon=True)
        self.orchestrator_thread.start()
    
    def run(self, host=None, port=None, debug=False):
        """Run the API server"""
        host = host or self.config.get('orchestrator.host', '0.0.0.0')
        port = port or self.config.get('orchestrator.port', 9000)
        
        logger.info(f"🚀 Starting Web4AI Orchestrator API on {host}:{port}")
        
        # Start orchestrator in background
        self._start_orchestrator_background()
        
        # Run Flask app
        self.app.run(host=host, port=port, debug=debug, threaded=True)

# Example configuration file generator
def generate_config_file():
    """Generate example configuration file"""
    config = OrchestratorConfig()
    config.save_config()
    print("📝 Generated orchestrator_config.yaml")

# CLI interface
def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Web4AI Network Orchestrator')
    parser.add_argument('--config', default='orchestrator_config.yaml', 
                       help='Configuration file path')
    parser.add_argument('--generate-config', action='store_true',
                       help='Generate example configuration file')
    parser.add_argument('--host', default='0.0.0.0', help='API host')
    parser.add_argument('--port', type=int, default=9000, help='API port')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    if args.generate_config:
        generate_config_file()
        return
    
    # Load configuration
    config = OrchestratorConfig(args.config)
    
    # Create and run API
    api = OrchestratorAPI(config)
    api.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()