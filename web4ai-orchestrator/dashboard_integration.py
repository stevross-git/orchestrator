# dashboard_integration.py - Dashboard Integration for Web4AI Orchestrator

from flask import Flask, render_template, send_from_directory, jsonify, request
import os
import json
from datetime import datetime

def setup_dashboard_routes(app, orchestrator_instance):
    """
    Setup dashboard routes and integration with the orchestrator
    Add this to your orchestrator_api.py file
    """
    
    # Configure template directory
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    app.template_folder = template_dir
    
    @app.route('/')
    @app.route('/dashboard')
    def dashboard():
        """Serve the advanced dashboard"""
        return render_template('web4ai_advanced_dashboard.html')
    
    @app.route('/api/v1/dashboard/config')
    def dashboard_config():
        """Provide dashboard configuration"""
        return jsonify({
            'success': True,
            'config': {
                'orchestrator_url': request.host_url.rstrip('/'),
                'websocket_url': f"ws://{request.host.split(':')[0]}:9001",
                'refresh_interval': 5000,
                'auto_refresh': True,
                'theme': 'light'
            }
        })
    
    @app.route('/api/v1/dashboard/alerts')
    def dashboard_alerts():
        """Get active alerts for dashboard"""
        alerts = []
        
        if orchestrator_instance:
            # Check for system alerts
            network_metrics = orchestrator_instance.network_metrics
            
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
    
    @app.route('/api/v1/dashboard/nodes/detailed')
    def dashboard_nodes_detailed():
        """Get detailed node information for dashboard"""
        nodes_data = []
        
        if orchestrator_instance:
            for node_id, node in orchestrator_instance.nodes.items():
                # Get agents for this node
                agents = []
                for agent_id in orchestrator_instance.node_agents.get(node_id, []):
                    if agent_id in orchestrator_instance.agents:
                        agent = orchestrator_instance.agents[agent_id]
                        agents.append({
                            'agent_id': agent.agent_id,
                            'agent_type': agent.agent_type,
                            'status': agent.status,
                            'capabilities': agent.capabilities,
                            'tasks_running': agent.tasks_running,
                            'tasks_completed': agent.tasks_completed,
                            'efficiency_score': agent.efficiency_score,
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
    
    @app.route('/api/v1/dashboard/performance/history')
    def dashboard_performance_history():
        """Get performance history for charts"""
        # Generate sample performance history
        # In production, this would come from your monitoring system
        import random
        from datetime import datetime, timedelta
        
        history = []
        current_time = datetime.utcnow()
        
        for i in range(20):  # Last 20 data points
            timestamp = current_time - timedelta(minutes=i * 5)  # Every 5 minutes
            
            if orchestrator_instance:
                metrics = orchestrator_instance.network_metrics
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
                'active_nodes': orchestrator_instance.network_metrics.get('active_nodes', 0) if orchestrator_instance else 0,
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
    
    @app.route('/api/v1/dashboard/tasks/queue')
    def dashboard_task_queue():
        """Get task queue information for dashboard"""
        queue_data = {
            'pending': [],
            'active': [],
            'recent_completed': [],
            'recent_failed': []
        }
        
        if orchestrator_instance:
            # Pending tasks
            for task in list(orchestrator_instance.pending_tasks)[:10]:  # Last 10
                queue_data['pending'].append({
                    'task_id': task.task_id,
                    'task_type': task.task_type,
                    'priority': task.priority.name,
                    'created_at': task.created_at,
                    'timeout': task.timeout,
                    'requirements': task.requirements
                })
            
            # Active tasks
            for task_id, task in list(orchestrator_instance.active_tasks.items())[:10]:
                queue_data['active'].append({
                    'task_id': task.task_id,
                    'task_type': task.task_type,
                    'priority': task.priority.name,
                    'assigned_nodes': task.assigned_nodes,
                    'created_at': task.created_at,
                    'timeout': task.timeout
                })
            
            # Recent completed (last 10)
            completed_tasks = list(orchestrator_instance.completed_tasks.values())[-10:]
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
            failed_tasks = list(orchestrator_instance.failed_tasks.values())[-10:]
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
    
    @app.route('/api/v1/dashboard/system/info')
    def dashboard_system_info():
        """Get system information for dashboard"""
        import psutil
        import platform
        
        system_info = {
            'orchestrator': {
                'id': orchestrator_instance.orchestrator_id if orchestrator_instance else 'unknown',
                'version': '1.0.0',
                'uptime': time.time() - orchestrator_instance.network_metrics.get('uptime', time.time()) if orchestrator_instance else 0,
                'running': orchestrator_instance.running if orchestrator_instance else False
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
    
    @app.route('/api/v1/dashboard/export/<format>')
    def dashboard_export(format):
        """Export dashboard data in various formats"""
        if format not in ['json', 'csv', 'xml']:
            return jsonify({'success': False, 'error': 'Unsupported format'}), 400
        
        # Collect all dashboard data
        data = {
            'timestamp': datetime.utcnow().isoformat(),
            'orchestrator_id': orchestrator_instance.orchestrator_id if orchestrator_instance else 'unknown',
            'network_metrics': orchestrator_instance.network_metrics if orchestrator_instance else {},
            'nodes': [node.__dict__ for node in orchestrator_instance.nodes.values()] if orchestrator_instance else [],
            'tasks_summary': {
                'pending': len(orchestrator_instance.pending_tasks) if orchestrator_instance else 0,
                'active': len(orchestrator_instance.active_tasks) if orchestrator_instance else 0,
                'completed': len(orchestrator_instance.completed_tasks) if orchestrator_instance else 0,
                'failed': len(orchestrator_instance.failed_tasks) if orchestrator_instance else 0
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

# WebSocket Enhancement for Dashboard
class DashboardWebSocketHandler:
    """Enhanced WebSocket handler for dashboard real-time updates"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.dashboard_clients = set()
        
    async def handle_dashboard_connection(self, websocket, path):
        """Handle dashboard WebSocket connections"""
        self.dashboard_clients.add(websocket)
        logger.info(f"Dashboard client connected: {websocket.remote_address}")
        
        try:
            # Send initial data
            await self.send_initial_data(websocket)
            
            # Handle incoming messages
            async for message in websocket:
                await self.handle_dashboard_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.dashboard_clients.discard(websocket)
            logger.info(f"Dashboard client disconnected: {websocket.remote_address}")
    
    async def send_initial_data(self, websocket):
        """Send initial dashboard data to new client"""
        if self.orchestrator:
            status = await self.orchestrator.get_network_status()
            await websocket.send(json.dumps({
                'type': 'initial_data',
                'data': status,
                'timestamp': time.time()
            }))
    
    async def handle_dashboard_message(self, websocket, message):
        """Handle incoming dashboard messages"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'subscribe_to_alerts':
                # Handle alert subscription
                await websocket.send(json.dumps({
                    'type': 'subscription_confirmed',
                    'subscription': 'alerts',
                    'timestamp': time.time()
                }))
            
            elif message_type == 'request_node_details':
                node_id = data.get('node_id')
                if node_id in self.orchestrator.nodes:
                    node = self.orchestrator.nodes[node_id]
                    await websocket.send(json.dumps({
                        'type': 'node_details',
                        'node_id': node_id,
                        'data': node.__dict__,
                        'timestamp': time.time()
                    }))
            
        except json.JSONDecodeError:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON message',
                'timestamp': time.time()
            }))
    
    async def broadcast_to_dashboard(self, message_type, data):
        """Broadcast updates to all dashboard clients"""
        if not self.dashboard_clients:
            return
        
        message = json.dumps({
            'type': message_type,
            'data': data,
            'timestamp': time.time()
        })
        
        disconnected_clients = set()
        for client in self.dashboard_clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        self.dashboard_clients -= disconnected_clients