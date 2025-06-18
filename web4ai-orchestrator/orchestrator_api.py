#!/usr/bin/env python3
"""
Web4AI Orchestrator API Server - COMPLETE FIXED VERSION
RESTful API interface and configuration management for the orchestrator
"""

from flask import Flask, request, jsonify, g, send_from_directory, render_template
from flask_cors import CORS
import asyncio
import threading
import json
import os
import yaml
import argparse
import signal
import websockets
import time  # Added missing import
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from functools import wraps
import traceback
import psutil
import random

# Import the main orchestrator
from web4ai_orchestrator import Web4AIOrchestrator, TaskRequest, TaskPriority, NodeStatus, TaskStatus

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
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f)
                logger.info(f"✅ Loaded configuration from {self.config_file}")
                return config
            except Exception as e:
                logger.error(f"❌ Failed to load config file: {e}")
        
        # Return default configuration
        return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration"""
        return {
            'orchestrator': {
                'id': 'web4ai_main_orchestrator',
                'port': 9000,
                'host': '0.0.0.0',
                'heartbeat_interval': 30,
                'task_timeout': 300,
                'max_retries': 3,
                'auto_discovery': True,
                'security_enabled': False,
                'auto_start': True
            },
            'network': {
                'discovery_endpoints': [
                    'http://localhost:8080',
                    'http://localhost:8081', 
                    'http://localhost:8082',
                    'http://localhost:8090'
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
                'metrics_retention_hours': 24,
                'performance_threshold': 0.8,
                'cpu_threshold': 80,
                'memory_threshold': 85,
                'latency_threshold': 1000
            },
            'security': {
                'api_key_required': False,
                'rate_limiting': True,
                'max_requests_per_minute': 1000,
                'encryption_enabled': False,
                'audit_logging': True
            },
            'storage': {
                'type': 'memory',
                'backup_enabled': False,
                'backup_interval_hours': 6
            },
            'websocket': {
                'enabled': True,
                'port': 9001,
                'max_connections': 100
            }
        }
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            logger.info(f"✅ Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"❌ Failed to save configuration: {e}")

class OrchestratorAPI:
    """Flask API server for the orchestrator"""
    
    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.orchestrator = None
        
        # Create Flask app with proper template configuration
        template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
        if not os.path.exists(template_dir):
            os.makedirs(template_dir, exist_ok=True)
            logger.info(f"Created templates directory: {template_dir}")
        
        self.app = Flask(__name__, template_folder=template_dir)
        CORS(self.app)
        
        # API statistics
        self.api_stats = {
            'requests_total': 0,
            'requests_success': 0,
            'requests_error': 0,
            'start_time': datetime.now()
        }
        
        # WebSocket server
        self.websocket_server = None
        self.websocket_clients = set()
        
        # Setup routes and middleware
        self._setup_middleware()
        self._setup_routes()
        
        logger.info("🌐 Orchestrator API initialized")
    
    def _setup_middleware(self):
        """Setup Flask middleware"""
        
        @self.app.before_request
        def before_request():
            """Pre-request processing"""
            self.api_stats['requests_total'] += 1
            g.start_time = datetime.now()
            
            # Rate limiting (if enabled)
            if self.config.config.get('security', {}).get('rate_limiting', False):
                client_ip = request.remote_addr
                # Simple rate limiting implementation
                # In production, use Redis or proper rate limiting library
        
        @self.app.after_request
        def after_request(response):
            """Post-request processing"""
            if response.status_code < 400:
                self.api_stats['requests_success'] += 1
            else:
                self.api_stats['requests_error'] += 1
            
            # Add CORS headers
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            
            return response
        
        @self.app.errorhandler(Exception)
        def handle_exception(e):
            """Global exception handler"""
            logger.error(f"❌ API Error: {e}")
            logger.error(traceback.format_exc())
            
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    def _setup_routes(self):
        """Setup all API routes"""
        
        @self.app.route('/dashboard')
        @self.app.route('/')
        def dashboard():
            """Serve the advanced dashboard"""
            try:
                return render_template('web4ai_advanced_dashboard.html')
            except Exception as e:
                logger.error(f"Dashboard template error: {e}")
                return self._create_basic_dashboard(), 200, {'Content-Type': 'text/html'}
        
        @self.app.route('/api/v1/dashboard/config')
        def dashboard_config():
            """Dashboard configuration"""
            return jsonify({
                'success': True,
                'config': {
                    'orchestrator_url': request.host_url.rstrip('/'),
                    'websocket_url': f"ws://{request.host.split(':')[0]}:9001",
                    'refresh_interval': 5000,
                    'auto_refresh': True
                }
            })
        
        @self.app.route('/api/v1/dashboard/alerts')
        def dashboard_alerts():
            """Get active alerts for dashboard"""
            alerts = []
            
            if self.orchestrator:
                # Check for system alerts
                network_metrics = self.orchestrator.network_metrics
                
                # No active nodes alert
                if network_metrics.get('active_nodes', 0) == 0:
                    alerts.append({
                        'id': 'no_nodes',
                        'type': 'critical',
                        'title': 'No Active Nodes',
                        'message': 'No nodes are currently active in the network',
                        'timestamp': datetime.utcnow().isoformat(),
                        'severity': 'critical'
                    })
                
                # Low success rate alert
                success_rate = network_metrics.get('success_rate', 1.0)
                if success_rate < 0.9:
                    alerts.append({
                        'id': 'low_success_rate',
                        'type': 'warning',
                        'title': 'Low Success Rate',
                        'message': f'Task success rate is {success_rate:.1%}',
                        'timestamp': datetime.utcnow().isoformat(),
                        'severity': 'warning'
                    })
                
                # High response time alert
                avg_response_time = network_metrics.get('average_response_time', 0)
                if avg_response_time > 5000:  # 5 seconds
                    alerts.append({
                        'id': 'high_response_time',
                        'type': 'warning',
                        'title': 'High Response Time',
                        'message': f'Average response time is {avg_response_time:.0f}ms',
                        'timestamp': datetime.utcnow().isoformat(),
                        'severity': 'warning'
                    })
                
                # High utilization alert
                utilization = network_metrics.get('network_utilization', 0)
                if utilization > 0.85:
                    alerts.append({
                        'id': 'high_utilization',
                        'type': 'warning',
                        'title': 'High Network Utilization',
                        'message': f'Network utilization is {utilization:.1%}',
                        'timestamp': datetime.utcnow().isoformat(),
                        'severity': 'warning'
                    })
            
            return jsonify({
                'success': True,
                'alerts': alerts,
                'total_alerts': len(alerts)
            })
        
        @self.app.route('/api/v1/dashboard/nodes/detailed')
        def dashboard_nodes_detailed():
            """Get detailed node information for dashboard"""
            nodes_data = []
            
            if self.orchestrator:
                for node_id, node in self.orchestrator.nodes.items():
                    # Get agents for this node
                    agents = []
                    for agent_id in self.orchestrator.node_agents.get(node_id, []):
                        if agent_id in self.orchestrator.agents:
                            agent = self.orchestrator.agents[agent_id]
                            agents.append({
                                'agent_id': agent.agent_id,
                                'agent_type': agent.agent_type,
                                'status': agent.status,
                                'capabilities': agent.capabilities,
                                'tasks_running': agent.tasks_running,
                                'tasks_completed': agent.tasks_completed,
                                'efficiency_score': agent.efficiency_score,
                                'specialized_models': agent.specialized_models,
                                'last_activity': agent.last_activity
                            })
                    
                    # Calculate uptime
                    current_time = time.time()
                    uptime_hours = (current_time - node.last_heartbeat) / 3600 if node.last_heartbeat else 0
                    
                    nodes_data.append({
                        'node_id': node.node_id,
                        'host': node.host,
                        'port': node.port,
                        'node_type': node.node_type,
                        'status': node.status.value,
                        'capabilities': node.capabilities,
                        'agents_count': node.agents_count,
                        'cpu_usage': node.cpu_usage,
                        'memory_usage': node.memory_usage,
                        'gpu_usage': node.gpu_usage,
                        'network_latency': node.network_latency,
                        'load_score': node.load_score,
                        'reliability_score': node.reliability_score,
                        'last_heartbeat': node.last_heartbeat,
                        'uptime_hours': max(0, uptime_hours),
                        'version': node.version,
                        'location': node.location,
                        'tasks_completed': node.tasks_completed,
                        'tasks_failed': node.tasks_failed,
                        'agents': agents,
                        'metadata': node.metadata
                    })
            
            return jsonify({
                'success': True,
                'nodes': nodes_data,
                'total_nodes': len(nodes_data)
            })
        
        @self.app.route('/api/v1/dashboard/performance/history')
        def dashboard_performance_history():
            """Get performance history for charts"""
            # Generate sample performance history
            # In production, this would come from your monitoring system
            history = []
            current_time = datetime.utcnow()
            
            for i in range(20):  # Last 20 data points
                timestamp = current_time - timedelta(minutes=i * 5)  # Every 5 minutes
                
                if self.orchestrator:
                    metrics = self.orchestrator.network_metrics
                    base_success_rate = metrics.get('success_rate', 0.95)
                    base_response_time = metrics.get('average_response_time', 1000)
                    base_utilization = metrics.get('network_utilization', 0.6)
                else:
                    base_success_rate = 0.95
                    base_response_time = 1000
                    base_utilization = 0.6
                
                # Add some realistic variation
                history.append({
                    'timestamp': timestamp.isoformat(),
                    'success_rate': min(1.0, max(0.8, base_success_rate + random.uniform(-0.05, 0.05))),
                    'response_time': max(100, base_response_time + random.uniform(-200, 300)),
                    'network_utilization': min(1.0, max(0.1, base_utilization + random.uniform(-0.1, 0.1))),
                    'throughput': random.uniform(40, 60),
                    'active_nodes': self.orchestrator.network_metrics.get('active_nodes', 0) if self.orchestrator else 0,
                    'tasks_completed': random.randint(80, 120),
                    'cpu_avg': random.uniform(30, 70),
                    'memory_avg': random.uniform(40, 80),
                    'gpu_avg': random.uniform(20, 60)
                })
            
            # Reverse to get chronological order
            history.reverse()
            
            return jsonify({
                'success': True,
                'history': history,
                'total_points': len(history)
            })
        
        @self.app.route('/api/v1/dashboard/tasks/queue')
        def dashboard_task_queue():
            """Get task queue information for dashboard"""
            queue_data = {
                'pending': [],
                'active': [],
                'recent_completed': [],
                'recent_failed': []
            }
            
            if self.orchestrator:
                # Pending tasks
                for task in list(self.orchestrator.pending_tasks)[:10]:  # Last 10
                    queue_data['pending'].append({
                        'task_id': task.task_id,
                        'task_type': task.task_type,
                        'priority': task.priority.name,
                        'created_at': task.created_at,
                        'timeout': task.timeout,
                        'requirements': task.requirements
                    })
                
                # Active tasks
                for task_id, task in list(self.orchestrator.active_tasks.items())[:10]:
                    queue_data['active'].append({
                        'task_id': task.task_id,
                        'task_type': task.task_type,
                        'priority': task.priority.name,
                        'assigned_nodes': task.assigned_nodes,
                        'created_at': task.created_at,
                        'timeout': task.timeout
                    })
                
                # Recent completed (last 10)
                completed_tasks = list(self.orchestrator.completed_tasks.values())[-10:]
                for result in completed_tasks:
                    queue_data['recent_completed'].append({
                        'task_id': result.task_id,
                        'status': result.status.value,
                        'execution_time': result.execution_time,
                        'node_id': result.node_id,
                        'agent_id': result.agent_id,
                        'completed_at': result.completed_at
                    })
                
                # Recent failed (last 10)
                failed_tasks = list(self.orchestrator.failed_tasks.values())[-10:]
                for result in failed_tasks:
                    queue_data['recent_failed'].append({
                        'task_id': result.task_id,
                        'status': result.status.value,
                        'error_message': result.error_message,
                        'node_id': result.node_id,
                        'completed_at': result.completed_at
                    })
            
            return jsonify({
                'success': True,
                'queue': queue_data,
                'summary': {
                    'pending_count': len(queue_data['pending']),
                    'active_count': len(queue_data['active']),
                    'completed_count': len(queue_data['recent_completed']),
                    'failed_count': len(queue_data['recent_failed'])
                }
            })
        
        @self.app.route('/api/v1/dashboard/system/info')
        def dashboard_system_info():
            """Get system information for dashboard"""
            import platform
            
            system_info = {
                'orchestrator': {
                    'id': self.orchestrator.orchestrator_id if self.orchestrator else 'unknown',
                    'version': '1.0.0',
                    'uptime': time.time() - self.orchestrator.network_metrics.get('uptime', time.time()) if self.orchestrator else 0,
                    'running': self.orchestrator.running if self.orchestrator else False
                },
                'system': {
                    'platform': platform.system(),
                    'platform_version': platform.version(),
                    'python_version': platform.python_version(),
                    'cpu_count': psutil.cpu_count(),
                    'memory_total': psutil.virtual_memory().total,
                    'disk_total': psutil.disk_usage('/').total,
                    'hostname': platform.node()
                },
                'resources': {
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_percent': psutil.disk_usage('/').percent,
                    'network_connections': len(psutil.net_connections())
                }
            }
            
            return jsonify({
                'success': True,
                'system_info': system_info
            })
        
        @self.app.route('/api/v1/dashboard/export/<format>')
        def dashboard_export(format):
            """Export dashboard data in various formats"""
            if format not in ['json', 'csv', 'xml']:
                return jsonify({'success': False, 'error': 'Unsupported format'}), 400
            
            # Collect all dashboard data
            data = {
                'timestamp': datetime.utcnow().isoformat(),
                'orchestrator_id': self.orchestrator.orchestrator_id if self.orchestrator else 'unknown',
                'network_metrics': self.orchestrator.network_metrics if self.orchestrator else {},
                'nodes': [node.__dict__ for node in self.orchestrator.nodes.values()] if self.orchestrator else [],
                'tasks_summary': {
                    'pending': len(self.orchestrator.pending_tasks) if self.orchestrator else 0,
                    'active': len(self.orchestrator.active_tasks) if self.orchestrator else 0,
                    'completed': len(self.orchestrator.completed_tasks) if self.orchestrator else 0,
                    'failed': len(self.orchestrator.failed_tasks) if self.orchestrator else 0
                }
            }
            
            if format == 'json':
                return jsonify({
                    'success': True,
                    'data': data,
                    'export_format': 'json'
                })
            elif format == 'csv':
                # Convert to CSV format (simplified)
                csv_data = "metric,value\n"
                csv_data += f"active_nodes,{data['network_metrics'].get('active_nodes', 0)}\n"
                csv_data += f"tasks_completed,{data['network_metrics'].get('tasks_completed', 0)}\n"
                csv_data += f"success_rate,{data['network_metrics'].get('success_rate', 0)}\n"
                
                return csv_data, 200, {'Content-Type': 'text/csv'}
            
            return jsonify({'success': False, 'error': 'Format implementation pending'}), 501
        
        # Health and status endpoints
        @self.app.route('/api/v1/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            try:
                system_info = {
                    'cpu_usage': psutil.cpu_percent(),
                    'memory_usage': psutil.virtual_memory().percent,
                    'disk_usage': psutil.disk_usage('/').percent,
                    'uptime': str(datetime.now() - self.api_stats['start_time'])
                }
                
                return jsonify({
                    'status': 'healthy',
                    'orchestrator_id': self.orchestrator.orchestrator_id if self.orchestrator else 'not_started',
                    'timestamp': datetime.now().isoformat(),
                    'version': '1.0.0',
                    'system': system_info
                })
            except Exception as e:
                logger.error(f"Health check error: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/v1/status', methods=['GET'])
        def status():
            """Get comprehensive orchestrator status"""
            try:
                if not self.orchestrator:
                    return jsonify({
                        'success': False,
                        'error': 'Orchestrator not started'
                    }), 503
                
                # Run async function in current thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    network_status = loop.run_until_complete(self.orchestrator.get_network_status())
                finally:
                    loop.close()
                
                return jsonify({
                    'success': True,
                    'data': network_status,
                    'api_stats': self.api_stats
                })
            except Exception as e:
                logger.error(f"Status error: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # Node management endpoints
        @self.app.route('/api/v1/nodes', methods=['GET'])
        def get_nodes():
            """Get all nodes in the network"""
            try:
                if not self.orchestrator:
                    return jsonify({'success': False, 'error': 'Orchestrator not started'}), 503
                
                nodes_data = {}
                for node_id, node in self.orchestrator.nodes.items():
                    nodes_data[node_id] = {
                        'node_id': node.node_id,
                        'host': node.host,
                        'port': node.port,
                        'node_type': node.node_type,
                        'status': node.status.value,
                        'capabilities': node.capabilities,
                        'agents_count': node.agents_count,
                        'cpu_usage': node.cpu_usage,
                        'memory_usage': node.memory_usage,
                        'gpu_usage': node.gpu_usage,
                        'load_score': node.load_score,
                        'last_heartbeat': node.last_heartbeat,
                        'version': node.version,
                        'location': node.location,
                        'uptime': time.time() - node.last_heartbeat if node.last_heartbeat else 0
                    }
                
                return jsonify({
                    'success': True,
                    'nodes': nodes_data,
                    'total_nodes': len(nodes_data),
                    'active_nodes': len([n for n in self.orchestrator.nodes.values() if n.status == NodeStatus.ACTIVE])
                })
            except Exception as e:
                logger.error(f"Get nodes error: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/v1/nodes/<node_id>', methods=['GET'])
        def get_node(node_id):
            """Get specific node information"""
            try:
                if not self.orchestrator:
                    return jsonify({'success': False, 'error': 'Orchestrator not started'}), 503
                
                if node_id not in self.orchestrator.nodes:
                    return jsonify({'success': False, 'error': 'Node not found'}), 404
                
                node = self.orchestrator.nodes[node_id]
                agents_data = []
                
                for agent_id in self.orchestrator.node_agents.get(node_id, []):
                    if agent_id in self.orchestrator.agents:
                        agent = self.orchestrator.agents[agent_id]
                        agents_data.append({
                            'agent_id': agent.agent_id,
                            'agent_type': agent.agent_type,
                            'status': agent.status,
                            'capabilities': agent.capabilities,
                            'tasks_running': agent.tasks_running,
                            'tasks_completed': agent.tasks_completed,
                            'efficiency_score': agent.efficiency_score,
                            'specialized_models': agent.specialized_models,
                            'last_activity': agent.last_activity
                        })
                
                node_data = {
                    'node_id': node.node_id,
                    'host': node.host,
                    'port': node.port,
                    'node_type': node.node_type,
                    'status': node.status.value,
                    'capabilities': node.capabilities,
                    'agents_count': node.agents_count,
                    'cpu_usage': node.cpu_usage,
                    'memory_usage': node.memory_usage,
                    'gpu_usage': node.gpu_usage,
                    'load_score': node.load_score,
                    'reliability_score': node.reliability_score,
                    'last_heartbeat': node.last_heartbeat,
                    'version': node.version,
                    'location': node.location,
                    'tasks_completed': node.tasks_completed,
                    'tasks_failed': node.tasks_failed,
                    'agents': agents_data
                }
                
                return jsonify({
                    'success': True,
                    'node': node_data
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/v1/nodes/<node_id>/register', methods=['POST'])
        def register_node(node_id):
            """Register a new node"""
            try:
                if not self.orchestrator:
                    return jsonify({'success': False, 'error': 'Orchestrator not started'}), 503
                
                node_data = request.get_json()
                if not node_data:
                    return jsonify({'success': False, 'error': 'No data provided'}), 400
                
                # Ensure node_id matches
                node_data['node_id'] = node_id
                
                # Run async registration
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    success = loop.run_until_complete(self.orchestrator.register_node(node_data))
                finally:
                    loop.close()
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': f'Node {node_id} registered successfully',
                        'node_id': node_id
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to register node'
                    }), 400
                    
            except Exception as e:
                logger.error(f"Register node error: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/v1/nodes/<node_id>/heartbeat', methods=['POST'])
        def node_heartbeat(node_id):
            """Update node heartbeat"""
            try:
                if not self.orchestrator:
                    return jsonify({'success': False, 'error': 'Orchestrator not started'}), 503
                
                heartbeat_data = request.get_json() or {}
                
                # Run async heartbeat update
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    success = loop.run_until_complete(
                        self.orchestrator.update_node_heartbeat(node_id, heartbeat_data)
                    )
                finally:
                    loop.close()
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': 'Heartbeat updated'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to update heartbeat'
                    }), 400
                    
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/v1/nodes/<node_id>/status', methods=['PUT'])
        def update_node_status(node_id):
            """Update node status"""
            try:
                if not self.orchestrator:
                    return jsonify({'success': False, 'error': 'Orchestrator not started'}), 503
                
                data = request.get_json()
                if not data or 'status' not in data:
                    return jsonify({'success': False, 'error': 'Status required'}), 400
                
                if node_id not in self.orchestrator.nodes:
                    return jsonify({'success': False, 'error': 'Node not found'}), 404
                
                node = self.orchestrator.nodes[node_id]
                old_status = node.status.value
                new_status = data['status']
                
                try:
                    node.status = NodeStatus(new_status)
                    logger.info(f"📊 Node {node_id} status updated: {old_status} -> {new_status}")
                    
                    return jsonify({
                        'success': True,
                        'message': f'Node status updated to {new_status}',
                        'old_status': old_status,
                        'new_status': new_status
                    })
                except ValueError:
                    return jsonify({
                        'success': False,
                        'error': f'Invalid status: {new_status}'
                    }), 400
                    
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/v1/nodes/<node_id>', methods=['DELETE'])
        def unregister_node(node_id):
            """Unregister a node"""
            try:
                if not self.orchestrator:
                    return jsonify({'success': False, 'error': 'Orchestrator not started'}), 503
                
                if node_id not in self.orchestrator.nodes:
                    return jsonify({'success': False, 'error': 'Node not found'}), 404
                
                # Remove node and its agents
                del self.orchestrator.nodes[node_id]
                
                # Remove agents
                for agent_id in self.orchestrator.node_agents.get(node_id, []):
                    if agent_id in self.orchestrator.agents:
                        del self.orchestrator.agents[agent_id]
                
                if node_id in self.orchestrator.node_agents:
                    del self.orchestrator.node_agents[node_id]
                
                logger.info(f"🗑️ Node {node_id} unregistered")
                
                return jsonify({
                    'success': True,
                    'message': f'Node {node_id} unregistered successfully'
                })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # Task management endpoints
        @self.app.route('/api/v1/tasks', methods=['POST'])
        def submit_task():
            """Submit a new task"""
            try:
                if not self.orchestrator:
                    return jsonify({'success': False, 'error': 'Orchestrator not started'}), 503
                
                task_data = request.get_json()
                if not task_data:
                    return jsonify({'success': False, 'error': 'No task data provided'}), 400
                
                # Validate required fields
                if 'task_type' not in task_data:
                    return jsonify({'success': False, 'error': 'task_type is required'}), 400
                
                # Run async task submission
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    task_id = loop.run_until_complete(self.orchestrator.submit_task(task_data))
                finally:
                    loop.close()
                
                return jsonify({
                    'success': True,
                    'task_id': task_id,
                    'message': 'Task submitted successfully'
                })
                
            except Exception as e:
                logger.error(f"Submit task error: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/v1/tasks', methods=['GET'])
        def get_tasks():
            """Get all tasks"""
            try:
                if not self.orchestrator:
                    return jsonify({'success': False, 'error': 'Orchestrator not started'}), 503
                
                tasks_data = {
                    'pending': [],
                    'active': [],
                    'completed': [],
                    'failed': []
                }
                
                # Pending tasks
                for task in self.orchestrator.pending_tasks:
                    tasks_data['pending'].append({
                        'task_id': task.task_id,
                        'task_type': task.task_type,
                        'priority': task.priority.value,
                        'created_at': task.created_at,
                        'timeout': task.timeout
                    })
                
                # Active tasks
                for task in self.orchestrator.active_tasks.values():
                    tasks_data['active'].append({
                        'task_id': task.task_id,
                        'task_type': task.task_type,
                        'priority': task.priority.value,
                        'assigned_nodes': task.assigned_nodes,
                        'created_at': task.created_at,
                        'timeout': task.timeout
                    })
                
                # Completed tasks (last 50)
                completed_tasks = list(self.orchestrator.completed_tasks.values())[-50:]
                for result in completed_tasks:
                    tasks_data['completed'].append({
                        'task_id': result.task_id,
                        'status': result.status.value,
                        'execution_time': result.execution_time,
                        'node_id': result.node_id,
                        'completed_at': result.completed_at
                    })
                
                # Failed tasks (last 50)
                failed_tasks = list(self.orchestrator.failed_tasks.values())[-50:]
                for result in failed_tasks:
                    tasks_data['failed'].append({
                        'task_id': result.task_id,
                        'status': result.status.value,
                        'error_message': result.error_message,
                        'node_id': result.node_id,
                        'completed_at': result.completed_at
                    })
                
                return jsonify({
                    'success': True,
                    'tasks': tasks_data,
                    'summary': {
                        'pending_count': len(tasks_data['pending']),
                        'active_count': len(tasks_data['active']),
                        'completed_count': len(self.orchestrator.completed_tasks),
                        'failed_count': len(self.orchestrator.failed_tasks)
                    }
                })
                
            except Exception as e:
                logger.error(f"Get tasks error: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/v1/tasks/<task_id>', methods=['GET'])
        def get_task(task_id):
            """Get specific task information"""
            try:
                if not self.orchestrator:
                    return jsonify({'success': False, 'error': 'Orchestrator not started'}), 503
                
                # Check active tasks
                if task_id in self.orchestrator.active_tasks:
                    task = self.orchestrator.active_tasks[task_id]
                    return jsonify({
                        'success': True,
                        'task': {
                            'task_id': task.task_id,
                            'task_type': task.task_type,
                            'status': 'active',
                            'priority': task.priority.value,
                            'assigned_nodes': task.assigned_nodes,
                            'created_at': task.created_at,
                            'timeout': task.timeout,
                            'retry_count': task.retry_count,
                            'requirements': task.requirements,
                            'metadata': task.metadata
                        }
                    })
                
                # Check completed tasks
                if task_id in self.orchestrator.completed_tasks:
                    result = self.orchestrator.completed_tasks[task_id]
                    return jsonify({
                        'success': True,
                        'task': {
                            'task_id': result.task_id,
                            'status': result.status.value,
                            'execution_time': result.execution_time,
                            'node_id': result.node_id,
                            'agent_id': result.agent_id,
                            'completed_at': result.completed_at,
                            'performance_metrics': result.performance_metrics
                        }
                    })
                
                # Check failed tasks
                if task_id in self.orchestrator.failed_tasks:
                    result = self.orchestrator.failed_tasks[task_id]
                    return jsonify({
                        'success': True,
                        'task': {
                            'task_id': result.task_id,
                            'status': result.status.value,
                            'error_message': result.error_message,
                            'node_id': result.node_id,
                            'completed_at': result.completed_at
                        }
                    })
                
                # Check pending tasks
                for task in self.orchestrator.pending_tasks:
                    if task.task_id == task_id:
                        return jsonify({
                            'success': True,
                            'task': {
                                'task_id': task.task_id,
                                'task_type': task.task_type,
                                'status': 'pending',
                                'priority': task.priority.value,
                                'created_at': task.created_at,
                                'timeout': task.timeout,
                                'requirements': task.requirements
                            }
                        })
                
                return jsonify({'success': False, 'error': 'Task not found'}), 404
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # Metrics and monitoring endpoints
        @self.app.route('/api/v1/metrics', methods=['GET'])
        def get_metrics():
            """Get orchestrator metrics"""
            try:
                if not self.orchestrator:
                    return jsonify({'success': False, 'error': 'Orchestrator not started'}), 503
                
                # Calculate additional metrics
                active_nodes = [n for n in self.orchestrator.nodes.values() 
                               if n.status == NodeStatus.ACTIVE]
                
                metrics = {
                    'timestamp': datetime.now().isoformat(),
                    'network': self.orchestrator.network_metrics.copy(),
                    'nodes': {
                        'total': len(self.orchestrator.nodes),
                        'active': len(active_nodes),
                        'avg_cpu_usage': sum(n.cpu_usage for n in active_nodes) / len(active_nodes) if active_nodes else 0,
                        'avg_memory_usage': sum(n.memory_usage for n in active_nodes) / len(active_nodes) if active_nodes else 0,
                        'avg_load_score': sum(n.load_score for n in active_nodes) / len(active_nodes) if active_nodes else 0
                    },
                    'tasks': {
                        'pending': len(self.orchestrator.pending_tasks),
                        'active': len(self.orchestrator.active_tasks),
                        'completed_total': len(self.orchestrator.completed_tasks),
                        'failed_total': len(self.orchestrator.failed_tasks),
                        'success_rate': self.orchestrator.network_metrics.get('success_rate', 0)
                    },
                    'api': self.api_stats.copy(),
                    'load_balancer': {
                        'algorithm': self.orchestrator.load_balancer.current_algorithm,
                        'node_weights': dict(self.orchestrator.load_balancer.node_weights)
                    }
                }
                
                return jsonify({
                    'success': True,
                    'metrics': metrics
                })
                
            except Exception as e:
                logger.error(f"Get metrics error: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/v1/metrics/performance', methods=['GET'])
        def get_performance_metrics():
            """Get detailed performance metrics"""
            try:
                if not self.orchestrator:
                    return jsonify({'success': False, 'error': 'Orchestrator not started'}), 503
                
                # Calculate performance analysis
                network_metrics = self.orchestrator.network_metrics
                analysis = self.orchestrator.performance_optimizer.analyze_performance(network_metrics)
                
                return jsonify({
                    'success': True,
                    'performance_analysis': analysis,
                    'recommendations': analysis.get('recommendations', [])
                })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # Control endpoints
        @self.app.route('/api/v1/control/start', methods=['POST'])
        def start_orchestrator():
            """Start the orchestrator"""
            try:
                if self.orchestrator and self.orchestrator.running:
                    return jsonify({
                        'success': True,
                        'message': 'Orchestrator already running'
                    })
                
                # Create and start orchestrator
                orch_config = self.config.config.get('orchestrator', {})
                self.orchestrator = Web4AIOrchestrator(
                    orchestrator_id=orch_config.get('id'),
                    config=self.config.config
                )
                
                # Start orchestrator in background thread
                def start_orchestrator_thread():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(self.orchestrator.start_orchestrator())
                        loop.run_forever()
                    except Exception as e:
                        logger.error(f"Orchestrator thread error: {e}")
                    finally:
                        loop.close()
                
                thread = threading.Thread(target=start_orchestrator_thread, daemon=True)
                thread.start()
                
                # Wait a moment for startup
                time.sleep(2)
                
                return jsonify({
                    'success': True,
                    'message': 'Orchestrator started successfully',
                    'orchestrator_id': self.orchestrator.orchestrator_id
                })
                
            except Exception as e:
                logger.error(f"Start orchestrator error: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/v1/control/stop', methods=['POST'])
        def stop_orchestrator():
            """Stop the orchestrator"""
            try:
                if not self.orchestrator or not self.orchestrator.running:
                    return jsonify({
                        'success': True,
                        'message': 'Orchestrator not running'
                    })
                
                # Stop orchestrator
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.orchestrator.stop_orchestrator())
                finally:
                    loop.close()
                
                return jsonify({
                    'success': True,
                    'message': 'Orchestrator stopped successfully'
                })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # Configuration endpoints
        @self.app.route('/api/v1/config', methods=['GET'])
        def get_config():
            """Get current configuration"""
            return jsonify({
                'success': True,
                'config': self.config.config
            })
        
        @self.app.route('/api/v1/config', methods=['PUT'])
        def update_config():
            """Update configuration"""
            try:
                new_config = request.get_json()
                if not new_config:
                    return jsonify({'success': False, 'error': 'No configuration provided'}), 400
                
                # Validate configuration
                # (Add validation logic here)
                
                # Update configuration
                self.config.config.update(new_config)
                self.config.save_config()
                
                return jsonify({
                    'success': True,
                    'message': 'Configuration updated',
                    'config': self.config.config
                })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # WebSocket endpoint info
        @self.app.route('/api/v1/websocket/info', methods=['GET'])
        def websocket_info():
            """Get WebSocket connection information"""
            ws_config = self.config.config.get('websocket', {})
            return jsonify({
                'success': True,
                'websocket': {
                    'enabled': ws_config.get('enabled', True),
                    'url': f"ws://localhost:{ws_config.get('port', 9001)}",
                    'connected_clients': len(self.websocket_clients),
                    'max_connections': ws_config.get('max_connections', 100)
                }
            })
    
    def _create_basic_dashboard(self):
        """Create a basic dashboard when template is not available"""
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Web4AI Orchestrator</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: #333; }
                .container { background: rgba(255,255,255,0.9); padding: 30px; border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); }
                .status { background: #f0f0f0; padding: 20px; border-radius: 8px; margin: 20px 0; }
                .metric { display: inline-block; margin: 10px; padding: 10px; background: white; border-radius: 4px; }
                .healthy { color: green; }
                .warning { color: orange; }
                .error { color: red; }
                a { color: #007cba; text-decoration: none; }
                a:hover { text-decoration: underline; }
                .error-msg { background: #fef2f2; color: #dc2626; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ef4444; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 Web4AI Orchestrator</h1>
                <div class="error-msg">
                    <h3>Dashboard Template Missing</h3>
                    <p>The advanced dashboard template is not available. This is a basic fallback interface.</p>
                    <p>To fix: Ensure <code>templates/web4ai_advanced_dashboard.html</code> exists in the correct location.</p>
                </div>
                
                <div class="status">
                    <h2>Status: <span class="healthy">API Running</span></h2>
                    <p>API server is operational. WebSocket may need configuration.</p>
                </div>
                
                <h3>🔗 API Endpoints</h3>
                <ul>
                    <li><a href="/api/v1/health">Health Check</a></li>
                    <li><a href="/api/v1/status">Network Status</a></li>
                    <li><a href="/api/v1/nodes">Nodes</a></li>
                    <li><a href="/api/v1/tasks">Tasks</a></li>
                    <li><a href="/api/v1/metrics">Metrics</a></li>
                    <li><a href="/api/v1/config">Configuration</a></li>
                </ul>
                
                <h3>📊 Quick Metrics</h3>
                <div id="metrics">Loading...</div>
                
                <script>
                    function updateMetrics() {
                        fetch('/api/v1/metrics')
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    const metrics = data.metrics;
                                    document.getElementById('metrics').innerHTML = `
                                        <div class="metric">Nodes: ${metrics.nodes.active}/${metrics.nodes.total}</div>
                                        <div class="metric">Tasks: ${metrics.tasks.active} active</div>
                                        <div class="metric">Success Rate: ${(metrics.tasks.success_rate * 100).toFixed(1)}%</div>
                                        <div class="metric">Utilization: ${(metrics.network.network_utilization * 100).toFixed(1)}%</div>
                                    `;
                                } else {
                                    document.getElementById('metrics').innerHTML = '<div class="error">Failed to load metrics: ' + data.error + '</div>';
                                }
                            })
                            .catch(err => {
                                document.getElementById('metrics').innerHTML = '<div class="error">Orchestrator not started or error occurred</div>';
                            });
                    }
                    
                    updateMetrics();
                    setInterval(updateMetrics, 5000);
                </script>
            </div>
        </body>
        </html>
        '''
    
    async def start_websocket_server(self):
        """Start WebSocket server for real-time updates"""
        ws_config = self.config.config.get('websocket', {})
        if not ws_config.get('enabled', True):
            logger.info("WebSocket server disabled in configuration")
            return
        
        port = ws_config.get('port', 9001)
        
        async def handle_websocket(websocket, path):
            """Handle WebSocket connections"""
            self.websocket_clients.add(websocket)
            logger.info(f"📡 WebSocket client connected (total: {len(self.websocket_clients)})")
            
            try:
                # Send initial status
                if self.orchestrator:
                    status = await self.orchestrator.get_network_status()
                    await websocket.send(json.dumps({
                        'type': 'initial_status',
                        'data': status
                    }))
                
                # Keep connection alive
                async for message in websocket:
                    # Handle incoming messages if needed
                    try:
                        data = json.loads(message)
                        logger.info(f"Received WebSocket message: {data}")
                    except:
                        pass
                    
            except websockets.exceptions.ConnectionClosed:
                logger.info("WebSocket connection closed normally")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            finally:
                self.websocket_clients.discard(websocket)
                logger.info(f"📡 WebSocket client disconnected (total: {len(self.websocket_clients)})")
        
        try:
            server = await websockets.serve(handle_websocket, "0.0.0.0", port)
            logger.info(f"🔌 WebSocket server started on ws://0.0.0.0:{port}")
            return server
        except Exception as e:
            logger.error(f"❌ Failed to start WebSocket server: {e}")
            return None
    
    def run(self, host='0.0.0.0', port=9000, debug=False):
        """Run the API server"""
        logger.info(f"🌐 Starting API server on http://{host}:{port}")
        
        # Start WebSocket server if enabled
        if self.config.config.get('websocket', {}).get('enabled', True):
            def start_websocket():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    self.websocket_server = loop.run_until_complete(self.start_websocket_server())
                    if self.websocket_server:
                        loop.run_forever()
                except Exception as e:
                    logger.error(f"WebSocket server error: {e}")
            
            ws_thread = threading.Thread(target=start_websocket, daemon=True)
            ws_thread.start()
        
        # Auto-start orchestrator if configured
        if self.config.config.get('orchestrator', {}).get('auto_start', True):
            logger.info("🚀 Auto-starting orchestrator...")
            try:
                orch_config = self.config.config.get('orchestrator', {})
                self.orchestrator = Web4AIOrchestrator(
                    orchestrator_id=orch_config.get('id'),
                    config=self.config.config
                )
                
                def start_orchestrator_thread():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(self.orchestrator.start_orchestrator())
                        loop.run_forever()
                    except Exception as e:
                        logger.error(f"Orchestrator startup error: {e}")
                
                thread = threading.Thread(target=start_orchestrator_thread, daemon=True)
                thread.start()
                
                # Give it time to start
                time.sleep(3)
                logger.info("✅ Orchestrator auto-start initiated")
                
            except Exception as e:
                logger.error(f"❌ Failed to auto-start orchestrator: {e}")
        
        # Run Flask app
        try:
            self.app.run(host=host, port=port, debug=debug, threaded=True)
        except Exception as e:
            logger.error(f"❌ Failed to start Flask app: {e}")
            raise

def create_default_config():
    """Create default configuration file"""
    config = OrchestratorConfig()
    config.save_config()
    print(f"✅ Created default configuration: {config.config_file}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Web4AI Orchestrator API Server')
    parser.add_argument('--config', default='orchestrator_config.yaml', help='Configuration file')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=9000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--generate-config', action='store_true', help='Generate default configuration')
    
    args = parser.parse_args()
    
    if args.generate_config:
        create_default_config()
        return
    
    # Load configuration
    config = OrchestratorConfig(args.config)
    
    # Override with command line arguments
    config.config['orchestrator']['host'] = args.host
    config.config['orchestrator']['port'] = args.port
    
    # Create and run API server
    api = OrchestratorAPI(config)
    
    # Handle shutdown gracefully
    def signal_handler(signum, frame):
        logger.info("🛑 Received shutdown signal")
        if api.orchestrator:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(api.orchestrator.stop_orchestrator())
            except Exception as e:
                logger.error(f"Shutdown error: {e}")
            finally:
                loop.close()
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        api.run(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down...")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")

if __name__ == '