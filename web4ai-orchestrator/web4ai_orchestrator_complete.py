#!/usr/bin/env python3
"""
Web4AI Network Orchestrator - Complete Implementation
Enterprise-grade orchestrator for managing the web4ai distributed network

Architecture:
- Orchestrator (Top Level) -> Manages entire network
- Node Managers (Middle Level) -> Control multiple agents per node  
- Agents (Bottom Level) -> Execute specific tasks

Features:
- Global network topology management
- Intelligent load balancing and resource allocation
- Fault tolerance and automatic recovery
- Performance optimization and scaling
- Security and access control
- Real-time monitoring and analytics
"""

import asyncio
import time
import json
import logging
import threading
import uuid
import requests
import websocket
import socket
from typing import Dict, Any, List, Optional, Set, Tuple, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import hashlib
import hmac

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkTier(Enum):
    """Network hierarchy levels"""
    ORCHESTRATOR = "orchestrator"    # Top-level global control
    NODE_MANAGER = "node_manager"    # Regional/zone node control
    AGENT = "agent"                  # Individual task execution

class NodeStatus(Enum):
    """Node operational states"""
    ACTIVE = "active"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"
    ERROR = "error"

class TaskPriority(Enum):
    """Task execution priorities"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5

class TaskStatus(Enum):
    """Task execution states"""
    PENDING = "pending"
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

@dataclass
class NodeInfo:
    """Comprehensive node information"""
    node_id: str
    host: str
    port: int
    node_type: str
    status: NodeStatus
    capabilities: List[str]
    agents_count: int
    cpu_usage: float
    memory_usage: float
    gpu_usage: float
    network_latency: float
    last_heartbeat: float
    version: str
    location: Optional[str] = None
    load_score: float = 0.0
    reliability_score: float = 1.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    uptime: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class AgentInfo:
    """Agent information within nodes"""
    agent_id: str
    node_id: str
    agent_type: str
    status: str
    capabilities: List[str]
    tasks_running: int
    tasks_completed: int
    efficiency_score: float
    specialized_models: List[str]
    last_activity: float = 0.0
    resource_usage: Dict[str, float] = None

    def __post_init__(self):
        if self.resource_usage is None:
            self.resource_usage = {}

@dataclass
class TaskRequest:
    """Global task request structure"""
    task_id: str
    task_type: str
    priority: TaskPriority
    requirements: Dict[str, Any]
    input_data: Any
    timeout: float
    retry_count: int = 0
    max_retries: int = 3
    assigned_nodes: List[str] = None
    created_at: float = 0
    deadline: Optional[float] = None
    callback_url: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.assigned_nodes is None:
            self.assigned_nodes = []
        if self.metadata is None:
            self.metadata = {}
        if self.created_at == 0:
            self.created_at = time.time()

@dataclass
class TaskResult:
    """Task execution result"""
    task_id: str
    status: TaskStatus
    result_data: Any
    execution_time: float
    node_id: str
    agent_id: Optional[str]
    error_message: Optional[str] = None
    performance_metrics: Dict[str, Any] = None
    completed_at: float = 0

    def __post_init__(self):
        if self.performance_metrics is None:
            self.performance_metrics = {}
        if self.completed_at == 0:
            self.completed_at = time.time()

class NetworkLoadBalancer:
    """Advanced load balancing for the network"""
    
    def __init__(self):
        self.node_weights = defaultdict(float)
        self.historical_performance = defaultdict(list)
        self.load_algorithms = {
            'round_robin': self._round_robin,
            'weighted_round_robin': self._weighted_round_robin,
            'least_connections': self._least_connections,
            'resource_aware': self._resource_aware,
            'latency_optimized': self._latency_optimized
        }
        self.current_algorithm = 'weighted_round_robin'
        
    def select_node(self, nodes: Dict[str, NodeInfo], task: TaskRequest) -> Optional[str]:
        """Select optimal node for task execution"""
        available_nodes = {
            node_id: node for node_id, node in nodes.items()
            if node.status == NodeStatus.ACTIVE and self._can_handle_task(node, task)
        }
        
        if not available_nodes:
            return None
            
        algorithm = self.load_algorithms.get(self.current_algorithm, self._weighted_round_robin)
        return algorithm(available_nodes, task)
    
    def _can_handle_task(self, node: NodeInfo, task: TaskRequest) -> bool:
        """Check if node can handle the task"""
        # Check capabilities
        required_capabilities = task.requirements.get('capabilities', [])
        if not all(cap in node.capabilities for cap in required_capabilities):
            return False
            
        # Check resource requirements
        if task.requirements.get('min_cpu', 0) > (100 - node.cpu_usage):
            return False
        if task.requirements.get('min_memory', 0) > (100 - node.memory_usage):
            return False
            
        # Check load threshold
        if node.load_score > 0.9:  # Don't assign to overloaded nodes
            return False
            
        return True
    
    def _round_robin(self, nodes: Dict[str, NodeInfo], task: TaskRequest) -> str:
        """Simple round-robin selection"""
        node_ids = list(nodes.keys())
        if not hasattr(self, '_rr_index'):
            self._rr_index = 0
        node_id = node_ids[self._rr_index % len(node_ids)]
        self._rr_index += 1
        return node_id
    
    def _weighted_round_robin(self, nodes: Dict[str, NodeInfo], task: TaskRequest) -> str:
        """Weighted round-robin based on node performance"""
        total_weight = 0
        weighted_nodes = []
        
        for node_id, node in nodes.items():
            # Calculate weight based on inverse load and reliability
            weight = (1.0 - node.load_score) * node.reliability_score
            total_weight += weight
            weighted_nodes.append((node_id, weight, total_weight))
        
        if total_weight == 0:
            return list(nodes.keys())[0]
            
        import random
        r = random.uniform(0, total_weight)
        for node_id, weight, cumulative_weight in weighted_nodes:
            if r <= cumulative_weight:
                return node_id
        
        return weighted_nodes[-1][0]
    
    def _least_connections(self, nodes: Dict[str, NodeInfo], task: TaskRequest) -> str:
        """Select node with least active connections/tasks"""
        min_load = float('inf')
        selected_node = None
        
        for node_id, node in nodes.items():
            current_load = node.agents_count + node.load_score
            if current_load < min_load:
                min_load = current_load
                selected_node = node_id
                
        return selected_node
    
    def _resource_aware(self, nodes: Dict[str, NodeInfo], task: TaskRequest) -> str:
        """Select based on resource availability"""
        best_score = -1
        selected_node = None
        
        for node_id, node in nodes.items():
            # Calculate resource fitness score
            cpu_fitness = (100 - node.cpu_usage) / 100
            memory_fitness = (100 - node.memory_usage) / 100
            gpu_fitness = (100 - node.gpu_usage) / 100 if node.gpu_usage > 0 else 1.0
            
            overall_fitness = (cpu_fitness + memory_fitness + gpu_fitness) / 3
            
            if overall_fitness > best_score:
                best_score = overall_fitness
                selected_node = node_id
                
        return selected_node
    
    def _latency_optimized(self, nodes: Dict[str, NodeInfo], task: TaskRequest) -> str:
        """Select node with lowest latency"""
        min_latency = float('inf')
        selected_node = None
        
        for node_id, node in nodes.items():
            if node.network_latency < min_latency:
                min_latency = node.network_latency
                selected_node = node_id
                
        return selected_node
    
    def update_node_performance(self, node_id: str, task_result: TaskResult):
        """Update node performance metrics"""
        if task_result.status == TaskStatus.COMPLETED:
            self.node_weights[node_id] = min(1.0, self.node_weights[node_id] + 0.1)
        else:
            self.node_weights[node_id] = max(0.1, self.node_weights[node_id] - 0.1)
        
        # Store historical performance
        self.historical_performance[node_id].append({
            'timestamp': time.time(),
            'execution_time': task_result.execution_time,
            'success': task_result.status == TaskStatus.COMPLETED
        })
        
        # Keep only recent history (last 100 tasks)
        if len(self.historical_performance[node_id]) > 100:
            self.historical_performance[node_id] = self.historical_performance[node_id][-100:]

class FaultDetector:
    """Network fault detection and recovery"""
    
    def __init__(self):
        self.node_failures = defaultdict(list)
        self.failure_patterns = {}
        self.recovery_strategies = {
            'node_restart': self._restart_node,
            'task_redistribution': self._redistribute_tasks,
            'health_check': self._perform_health_check
        }
        
    def detect_node_failure(self, node_id: str, last_heartbeat: float) -> bool:
        """Detect if a node has failed"""
        current_time = time.time()
        heartbeat_age = current_time - last_heartbeat
        
        # Consider node failed if no heartbeat for 2 minutes
        if heartbeat_age > 120:
            self.node_failures[node_id].append(current_time)
            logger.warning(f"Node {node_id} marked as failed (no heartbeat for {heartbeat_age:.1f}s)")
            return True
        
        return False
    
    def get_failure_rate(self, node_id: str, window_hours: int = 24) -> float:
        """Calculate node failure rate in given time window"""
        cutoff_time = time.time() - (window_hours * 3600)
        recent_failures = [f for f in self.node_failures[node_id] if f > cutoff_time]
        return len(recent_failures) / window_hours  # failures per hour
    
    def _restart_node(self, node_id: str) -> bool:
        """Attempt to restart a failed node"""
        logger.info(f"Attempting to restart node {node_id}")
        # Implementation would depend on deployment method
        return True
    
    def _redistribute_tasks(self, failed_node_id: str, active_tasks: List[str]) -> bool:
        """Redistribute tasks from failed node"""
        logger.info(f"Redistributing {len(active_tasks)} tasks from failed node {failed_node_id}")
        # Implementation would move tasks to other nodes
        return True
    
    def _perform_health_check(self, node_id: str) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        return {
            'timestamp': time.time(),
            'node_id': node_id,
            'status': 'checking',
            'checks': ['network', 'resources', 'services']
        }

class PerformanceOptimizer:
    """Network performance optimization"""
    
    def __init__(self):
        self.optimization_rules = []
        self.performance_history = []
        self.optimization_strategies = {
            'auto_scaling': self._auto_scaling,
            'load_rebalancing': self._load_rebalancing,
            'resource_optimization': self._resource_optimization
        }
        
    def analyze_performance(self, network_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze network performance and suggest optimizations"""
        analysis = {
            'timestamp': time.time(),
            'network_utilization': network_metrics.get('network_utilization', 0),
            'avg_response_time': network_metrics.get('average_response_time', 0),
            'task_throughput': network_metrics.get('tasks_completed', 0),
            'recommendations': []
        }
        
        # High utilization optimization
        if network_metrics.get('network_utilization', 0) > 0.8:
            analysis['recommendations'].append({
                'type': 'auto_scaling',
                'priority': 'high',
                'description': 'Network utilization is high, consider scaling up'
            })
        
        # Low utilization optimization  
        if network_metrics.get('network_utilization', 0) < 0.2:
            analysis['recommendations'].append({
                'type': 'auto_scaling',
                'priority': 'low',
                'description': 'Network utilization is low, consider scaling down'
            })
        
        # Response time optimization
        if network_metrics.get('average_response_time', 0) > 5000:  # 5 seconds
            analysis['recommendations'].append({
                'type': 'load_rebalancing',
                'priority': 'medium',
                'description': 'High response times detected, rebalance load'
            })
        
        return analysis
    
    def _auto_scaling(self, nodes: Dict[str, NodeInfo], target_utilization: float = 0.7) -> Dict[str, Any]:
        """Implement auto-scaling logic"""
        current_utilization = sum(node.load_score for node in nodes.values()) / len(nodes)
        
        if current_utilization > target_utilization + 0.1:
            return {'action': 'scale_up', 'reason': 'High utilization'}
        elif current_utilization < target_utilization - 0.1:
            return {'action': 'scale_down', 'reason': 'Low utilization'}
        
        return {'action': 'maintain', 'reason': 'Optimal utilization'}
    
    def _load_rebalancing(self, nodes: Dict[str, NodeInfo]) -> Dict[str, Any]:
        """Implement load rebalancing"""
        avg_load = sum(node.load_score for node in nodes.values()) / len(nodes)
        overloaded_nodes = [nid for nid, node in nodes.items() if node.load_score > avg_load + 0.2]
        underloaded_nodes = [nid for nid, node in nodes.items() if node.load_score < avg_load - 0.2]
        
        return {
            'overloaded_nodes': overloaded_nodes,
            'underloaded_nodes': underloaded_nodes,
            'rebalance_needed': len(overloaded_nodes) > 0 and len(underloaded_nodes) > 0
        }
    
    def _resource_optimization(self, nodes: Dict[str, NodeInfo]) -> Dict[str, Any]:
        """Optimize resource allocation"""
        resource_recommendations = []
        
        for node_id, node in nodes.items():
            if node.cpu_usage > 90:
                resource_recommendations.append({
                    'node_id': node_id,
                    'resource': 'cpu',
                    'action': 'increase_allocation',
                    'current_usage': node.cpu_usage
                })
            
            if node.memory_usage > 90:
                resource_recommendations.append({
                    'node_id': node_id,
                    'resource': 'memory', 
                    'action': 'increase_allocation',
                    'current_usage': node.memory_usage
                })
        
        return {'recommendations': resource_recommendations}

class Web4AIOrchestrator:
    """
    Main orchestrator for the web4ai network
    Manages nodes, coordinates tasks, and optimizes performance
    """
    
    def __init__(self, orchestrator_id: str = None, config: Dict[str, Any] = None):
        self.orchestrator_id = orchestrator_id or f"orch_{uuid.uuid4().hex[:8]}"
        self.config = config or self._default_config()
        
        # Network state
        self.nodes: Dict[str, NodeInfo] = {}
        self.agents: Dict[str, AgentInfo] = {}
        self.node_agents: Dict[str, List[str]] = defaultdict(list)
        
        # Task management
        self.pending_tasks: deque = deque()
        self.active_tasks: Dict[str, TaskRequest] = {}
        self.completed_tasks: Dict[str, TaskResult] = {}
        self.failed_tasks: Dict[str, TaskResult] = {}
        self.task_history: List[TaskResult] = []
        
        # Performance tracking
        self.network_metrics = {
            'total_nodes': 0,
            'active_nodes': 0,
            'total_agents': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'average_response_time': 0.0,
            'network_utilization': 0.0,
            'uptime': time.time(),
            'throughput_per_minute': 0.0,
            'success_rate': 1.0
        }
        
        # Core services
        self.load_balancer = NetworkLoadBalancer()
        self.fault_detector = FaultDetector()
        self.performance_optimizer = PerformanceOptimizer()
        
        # Communication and threading
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.running = False
        self.websocket_connections = set()
        
        # Security
        self.api_keys = set()
        self.rate_limits = defaultdict(list)
        
        logger.info(f"🚀 Web4AI Orchestrator {self.orchestrator_id} initialized")

    def _default_config(self) -> Dict[str, Any]:
        """Default orchestrator configuration"""
        return {
            'heartbeat_interval': 30,
            'task_timeout': 300,
            'max_retries': 3,
            'load_balance_algorithm': 'weighted_round_robin',
            'fault_tolerance_enabled': True,
            'auto_scaling_enabled': True,
            'performance_monitoring': True,
            'security_enabled': False,
            'backup_enabled': True,
            'max_nodes': 100,
            'min_nodes': 1,
            'websocket_enabled': True,
            'metrics_retention_hours': 24
        }

    async def start_orchestrator(self):
        """Start the orchestrator and all background services"""
        if self.running:
            logger.warning("Orchestrator already running")
            return
        
        self.running = True
        logger.info("🌟 Starting Web4AI Orchestrator...")
        
        # Start background services
        asyncio.create_task(self._heartbeat_monitor())
        asyncio.create_task(self._task_processor())
        asyncio.create_task(self._performance_monitor())
        asyncio.create_task(self._fault_detector_service())
        asyncio.create_task(self._cleanup_service())
        
        if self.config.get('websocket_enabled', True):
            asyncio.create_task(self._websocket_broadcaster())
        
        logger.info("✅ Orchestrator services started")
        
        # Initialize network discovery
        await self._discover_existing_nodes()
        
        logger.info(f"🎉 Web4AI Orchestrator {self.orchestrator_id} is now running")

    async def stop_orchestrator(self):
        """Stop the orchestrator gracefully"""
        logger.info("🛑 Stopping Web4AI Orchestrator...")
        self.running = False
        
        # Cancel pending tasks
        for task in self.pending_tasks:
            task.status = TaskStatus.CANCELLED
        
        # Notify all nodes
        for node_id in self.nodes:
            await self._notify_node_shutdown(node_id)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("✅ Orchestrator stopped gracefully")

    async def register_node(self, node_data: Dict[str, Any]) -> bool:
        """Register a new node in the network"""
        try:
            node_id = node_data.get('node_id')
            if not node_id:
                raise ValueError("Node ID is required")
            
            # Create node info
            node_info = NodeInfo(
                node_id=node_id,
                host=node_data.get('host', 'localhost'),
                port=node_data.get('port', 8080),
                node_type=node_data.get('node_type', 'worker'),
                status=NodeStatus.ACTIVE,
                capabilities=node_data.get('capabilities', []),
                agents_count=node_data.get('agents_count', 0),
                cpu_usage=node_data.get('cpu_usage', 0.0),
                memory_usage=node_data.get('memory_usage', 0.0),
                gpu_usage=node_data.get('gpu_usage', 0.0),
                network_latency=0.0,
                last_heartbeat=time.time(),
                version=node_data.get('version', '1.0.0'),
                location=node_data.get('location'),
                metadata=node_data.get('metadata', {})
            )
            
            # Register agents if provided
            agents = node_data.get('agents', [])
            for agent_data in agents:
                await self.register_agent(agent_data, node_id)
            
            self.nodes[node_id] = node_info
            self._update_network_metrics()
            
            logger.info(f"✅ Node {node_id} registered successfully")
            await self._broadcast_network_update('node_registered', {'node_id': node_id})
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to register node: {e}")
            return False

    async def register_agent(self, agent_data: Dict[str, Any], node_id: str) -> bool:
        """Register an agent within a node"""
        try:
            agent_id = agent_data.get('agent_id')
            if not agent_id:
                raise ValueError("Agent ID is required")
            
            agent_info = AgentInfo(
                agent_id=agent_id,
                node_id=node_id,
                agent_type=agent_data.get('agent_type', 'generic'),
                status=agent_data.get('status', 'active'),
                capabilities=agent_data.get('capabilities', []),
                tasks_running=0,
                tasks_completed=0,
                efficiency_score=1.0,
                specialized_models=agent_data.get('specialized_models', []),
                last_activity=time.time(),
                resource_usage=agent_data.get('resource_usage', {})
            )
            
            self.agents[agent_id] = agent_info
            self.node_agents[node_id].append(agent_id)
            
            # Update node agent count
            if node_id in self.nodes:
                self.nodes[node_id].agents_count = len(self.node_agents[node_id])
            
            logger.info(f"✅ Agent {agent_id} registered on node {node_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to register agent: {e}")
            return False

    async def submit_task(self, task_data: Dict[str, Any]) -> str:
        """Submit a task for execution"""
        try:
            task_id = task_data.get('task_id') or f"task_{uuid.uuid4().hex[:12]}"
            
            task = TaskRequest(
                task_id=task_id,
                task_type=task_data.get('task_type', 'generic'),
                priority=TaskPriority(task_data.get('priority', TaskPriority.NORMAL.value)),
                requirements=task_data.get('requirements', {}),
                input_data=task_data.get('input_data'),
                timeout=task_data.get('timeout', 300),
                max_retries=task_data.get('max_retries', 3),
                deadline=task_data.get('deadline'),
                callback_url=task_data.get('callback_url'),
                metadata=task_data.get('metadata', {})
            )
            
            # Add to pending queue
            self.pending_tasks.append(task)
            
            logger.info(f"📝 Task {task_id} submitted (type: {task.task_type}, priority: {task.priority.name})")
            await self._broadcast_network_update('task_submitted', {'task_id': task_id})
            
            return task_id
            
        except Exception as e:
            logger.error(f"❌ Failed to submit task: {e}")
            raise

    async def update_node_heartbeat(self, node_id: str, heartbeat_data: Dict[str, Any]) -> bool:
        """Update node heartbeat and status"""
        try:
            if node_id not in self.nodes:
                logger.warning(f"⚠️ Heartbeat from unknown node: {node_id}")
                return False
            
            node = self.nodes[node_id]
            
            # Update heartbeat timestamp
            node.last_heartbeat = time.time()
            
            # Update metrics if provided
            if 'cpu_usage' in heartbeat_data:
                node.cpu_usage = heartbeat_data['cpu_usage']
            if 'memory_usage' in heartbeat_data:
                node.memory_usage = heartbeat_data['memory_usage']
            if 'gpu_usage' in heartbeat_data:
                node.gpu_usage = heartbeat_data['gpu_usage']
            if 'load_score' in heartbeat_data:
                node.load_score = heartbeat_data['load_score']
            if 'tasks_running' in heartbeat_data:
                # Update running task count from agents
                pass
            
            # Update status if changed
            new_status = heartbeat_data.get('status', 'active')
            if node.status.value != new_status:
                old_status = node.status
                node.status = NodeStatus(new_status)
                logger.info(f"📊 Node {node_id} status changed: {old_status.value} -> {new_status}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update heartbeat for node {node_id}: {e}")
            return False

    async def get_network_status(self) -> Dict[str, Any]:
        """Get comprehensive network status"""
        self._update_network_metrics()
        
        active_nodes = [node for node in self.nodes.values() if node.status == NodeStatus.ACTIVE]
        
        return {
            'orchestrator_id': self.orchestrator_id,
            'timestamp': time.time(),
            'uptime': time.time() - self.network_metrics['uptime'],
            'network_metrics': self.network_metrics.copy(),
            'nodes': {
                'total': len(self.nodes),
                'active': len(active_nodes),
                'by_status': {status.value: len([n for n in self.nodes.values() if n.status == status]) 
                             for status in NodeStatus}
            },
            'agents': {
                'total': len(self.agents),
                'by_node': {node_id: len(agent_ids) for node_id, agent_ids in self.node_agents.items()}
            },
            'tasks': {
                'pending': len(self.pending_tasks),
                'active': len(self.active_tasks),
                'completed': len(self.completed_tasks),
                'failed': len(self.failed_tasks)
            },
            'performance': {
                'avg_cpu_usage': sum(n.cpu_usage for n in active_nodes) / len(active_nodes) if active_nodes else 0,
                'avg_memory_usage': sum(n.memory_usage for n in active_nodes) / len(active_nodes) if active_nodes else 0,
                'avg_network_latency': sum(n.network_latency for n in active_nodes) / len(active_nodes) if active_nodes else 0,
                'network_utilization': self.network_metrics['network_utilization']
            }
        }

    def _update_network_metrics(self):
        """Update network-wide metrics"""
        current_time = time.time()
        
        self.network_metrics.update({
            'total_nodes': len(self.nodes),
            'active_nodes': len([n for n in self.nodes.values() if n.status == NodeStatus.ACTIVE]),
            'total_agents': len(self.agents),
            'tasks_completed': len(self.completed_tasks),
            'tasks_failed': len(self.failed_tasks)
        })
        
        # Calculate success rate
        total_tasks = len(self.completed_tasks) + len(self.failed_tasks)
        if total_tasks > 0:
            self.network_metrics['success_rate'] = len(self.completed_tasks) / total_tasks
        
        # Calculate network utilization
        if self.nodes:
            total_load = sum(node.load_score for node in self.nodes.values())
            self.network_metrics['network_utilization'] = total_load / len(self.nodes)
        
        # Calculate throughput (tasks per minute)
        if hasattr(self, '_last_throughput_calculation'):
            time_diff = current_time - self._last_throughput_calculation
            if time_diff >= 60:  # Calculate every minute
                recent_tasks = [t for t in self.task_history if t.completed_at > current_time - 60]
                self.network_metrics['throughput_per_minute'] = len(recent_tasks)
                self._last_throughput_calculation = current_time
        else:
            self._last_throughput_calculation = current_time

    async def _heartbeat_monitor(self):
        """Monitor node heartbeats and detect failures"""
        while self.running:
            try:
                current_time = time.time()
                failed_nodes = []
                
                for node_id, node in self.nodes.items():
                    if self.fault_detector.detect_node_failure(node_id, node.last_heartbeat):
                        if node.status != NodeStatus.OFFLINE:
                            node.status = NodeStatus.OFFLINE
                            failed_nodes.append(node_id)
                            await self._handle_node_failure(node_id)
                
                if failed_nodes:
                    logger.warning(f"⚠️ Detected failed nodes: {failed_nodes}")
                
                await asyncio.sleep(self.config.get('heartbeat_interval', 30))
                
            except Exception as e:
                logger.error(f"❌ Heartbeat monitor error: {e}")
                await asyncio.sleep(60)

    async def _task_processor(self):
        """Process pending tasks and assign them to nodes"""
        while self.running:
            try:
                if self.pending_tasks:
                    task = self.pending_tasks.popleft()
                    
                    # Select optimal node
                    selected_node = self.load_balancer.select_node(self.nodes, task)
                    
                    if selected_node:
                        task.assigned_nodes = [selected_node]
                        self.active_tasks[task.task_id] = task
                        
                        # Send task to node
                        success = await self._send_task_to_node(selected_node, task)
                        
                        if success:
                            logger.info(f"📤 Task {task.task_id} assigned to node {selected_node}")
                        else:
                            # Put task back in queue
                            self.pending_tasks.appendleft(task)
                            del self.active_tasks[task.task_id]
                    else:
                        # No available nodes, put task back
                        self.pending_tasks.appendleft(task)
                        logger.warning(f"⚠️ No available nodes for task {task.task_id}")
                
                await asyncio.sleep(1)  # Process tasks every second
                
            except Exception as e:
                logger.error(f"❌ Task processor error: {e}")
                await asyncio.sleep(5)

    async def _performance_monitor(self):
        """Monitor and optimize network performance"""
        while self.running:
            try:
                # Analyze performance
                analysis = self.performance_optimizer.analyze_performance(self.network_metrics)
                
                # Apply optimizations
                for recommendation in analysis.get('recommendations', []):
                    await self._apply_optimization(recommendation)
                
                await asyncio.sleep(60)  # Monitor every minute
                
            except Exception as e:
                logger.error(f"❌ Performance monitor error: {e}")
                await asyncio.sleep(300)

    async def _fault_detector_service(self):
        """Background fault detection service"""
        while self.running:
            try:
                # Check for patterns in failures
                for node_id in self.nodes:
                    failure_rate = self.fault_detector.get_failure_rate(node_id)
                    if failure_rate > 0.5:  # More than 0.5 failures per hour
                        logger.warning(f"⚠️ High failure rate for node {node_id}: {failure_rate:.2f}/hour")
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"❌ Fault detector error: {e}")
                await asyncio.sleep(600)

    async def _cleanup_service(self):
        """Cleanup old data and maintain system health"""
        while self.running:
            try:
                current_time = time.time()
                retention_hours = self.config.get('metrics_retention_hours', 24)
                cutoff_time = current_time - (retention_hours * 3600)
                
                # Clean old task history
                self.task_history = [t for t in self.task_history if t.completed_at > cutoff_time]
                
                # Clean old completed/failed tasks
                old_completed = [tid for tid, task in self.completed_tasks.items() 
                               if task.completed_at < cutoff_time]
                old_failed = [tid for tid, task in self.failed_tasks.items() 
                             if task.completed_at < cutoff_time]
                
                for tid in old_completed:
                    del self.completed_tasks[tid]
                for tid in old_failed:
                    del self.failed_tasks[tid]
                
                if old_completed or old_failed:
                    logger.info(f"🧹 Cleaned {len(old_completed)} completed and {len(old_failed)} failed tasks")
                
                await asyncio.sleep(3600)  # Clean every hour
                
            except Exception as e:
                logger.error(f"❌ Cleanup service error: {e}")
                await asyncio.sleep(3600)

    async def _websocket_broadcaster(self):
        """Broadcast real-time updates via WebSocket"""
        while self.running:
            try:
                if self.websocket_connections:
                    status = await self.get_network_status()
                    message = json.dumps({
                        'type': 'network_status',
                        'data': status,
                        'timestamp': time.time()
                    })
                    
                    # Send to all connected clients
                    disconnected = set()
                    for ws in self.websocket_connections:
                        try:
                            await ws.send(message)
                        except:
                            disconnected.add(ws)
                    
                    # Remove disconnected clients
                    self.websocket_connections -= disconnected
                
                await asyncio.sleep(5)  # Broadcast every 5 seconds
                
            except Exception as e:
                logger.error(f"❌ WebSocket broadcaster error: {e}")
                await asyncio.sleep(10)

    async def _discover_existing_nodes(self):
        """Discover existing nodes in the network"""
        discovery_endpoints = self.config.get('discovery_endpoints', [])
        
        for endpoint in discovery_endpoints:
            try:
                response = requests.get(f"{endpoint}/api/health", timeout=5)
                if response.status_code == 200:
                    logger.info(f"🔍 Discovered potential node at {endpoint}")
                    # Could implement automatic registration here
            except:
                pass

    async def _send_task_to_node(self, node_id: str, task: TaskRequest) -> bool:
        """Send task to specific node"""
        try:
            node = self.nodes[node_id]
            endpoint = f"http://{node.host}:{node.port}/api/tasks"
            
            task_data = {
                'task_id': task.task_id,
                'task_type': task.task_type,
                'priority': task.priority.value,
                'requirements': task.requirements,
                'input_data': task.input_data,
                'timeout': task.timeout,
                'metadata': task.metadata
            }
            
            response = requests.post(endpoint, json=task_data, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"❌ Failed to send task to node {node_id}: {e}")
            return False

    async def _handle_node_failure(self, node_id: str):
        """Handle node failure"""
        logger.warning(f"🚨 Handling failure of node {node_id}")
        
        # Redistribute active tasks from failed node
        failed_tasks = [task for task in self.active_tasks.values() 
                       if node_id in task.assigned_nodes]
        
        for task in failed_tasks:
            task.assigned_nodes.remove(node_id)
            task.retry_count += 1
            
            if task.retry_count <= task.max_retries:
                self.pending_tasks.appendleft(task)
                del self.active_tasks[task.task_id]
                logger.info(f"🔄 Retrying task {task.task_id} (attempt {task.retry_count})")
            else:
                # Mark as failed
                result = TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    result_data=None,
                    execution_time=0,
                    node_id=node_id,
                    agent_id=None,
                    error_message=f"Node {node_id} failed, max retries exceeded"
                )
                self.failed_tasks[task.task_id] = result
                del self.active_tasks[task.task_id]
                logger.error(f"❌ Task {task.task_id} failed permanently")

    async def _notify_node_shutdown(self, node_id: str):
        """Notify node of orchestrator shutdown"""
        try:
            node = self.nodes[node_id]
            endpoint = f"http://{node.host}:{node.port}/api/shutdown"
            requests.post(endpoint, json={'message': 'Orchestrator shutting down'}, timeout=5)
        except:
            pass

    async def _broadcast_network_update(self, event_type: str, data: Dict[str, Any]):
        """Broadcast network updates to connected clients"""
        if self.websocket_connections:
            message = json.dumps({
                'type': event_type,
                'data': data,
                'timestamp': time.time()
            })
            
            disconnected = set()
            for ws in self.websocket_connections:
                try:
                    await ws.send(message)
                except:
                    disconnected.add(ws)
            
            self.websocket_connections -= disconnected

    async def _apply_optimization(self, recommendation: Dict[str, Any]):
        """Apply performance optimization"""
        opt_type = recommendation.get('type')
        
        if opt_type == 'auto_scaling':
            await self._handle_auto_scaling(recommendation)
        elif opt_type == 'load_rebalancing':
            await self._handle_load_rebalancing(recommendation)
        elif opt_type == 'resource_optimization':
            await self._handle_resource_optimization(recommendation)

    async def _handle_auto_scaling(self, recommendation: Dict[str, Any]):
        """Handle auto-scaling recommendation"""
        logger.info(f"🔧 Auto-scaling recommendation: {recommendation['description']}")
        # Implementation would depend on deployment infrastructure

    async def _handle_load_rebalancing(self, recommendation: Dict[str, Any]):
        """Handle load rebalancing recommendation"""
        logger.info(f"🔧 Load rebalancing recommendation: {recommendation['description']}")
        # Could implement task migration between nodes

    async def _handle_resource_optimization(self, recommendation: Dict[str, Any]):
        """Handle resource optimization recommendation"""
        logger.info(f"🔧 Resource optimization recommendation: {recommendation['description']}")
        # Could adjust resource allocation on nodes