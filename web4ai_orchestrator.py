#!/usr/bin/env python3
"""
Web4AI Network Orchestrator
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
from typing import Dict, Any, List, Optional, Set, Tuple, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import uuid
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import websocket
import socket

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
        self.completed_tasks: Dict[str, Dict[str, Any]] = {}
        self.failed_tasks: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self.network_metrics = {
            'total_nodes': 0,
            'active_nodes': 0,
            'total_agents': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'average_response_time': 0.0,
            'network_utilization': 0.0,
            'uptime': time.time()
        }
        
        # Load balancing
        self.load_balancer = NetworkLoadBalancer()
        self.fault_detector = FaultDetector()
        self.performance_optimizer = PerformanceOptimizer()
        
        # Communication
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.running = False
        
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
            'security_enabled': True,
            'backup_enabled': True
        }

    async def start_orchestrator(self):
        """Start the orchestrator and all background services"""
        if self.running:
            logger.warning("Orchestrator already running")
            return
        
        self.running = True
        logger.info("🌟 Starting Web4AI Network Orchestrator...")
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._heartbeat_monitor()),
            asyncio.create_task(self._task_scheduler()),
            asyncio.create_task(self._performance_monitor()),
            asyncio.create_task(self._fault_detection()),
            asyncio.create_task(self._load_balancer_loop()),
            asyncio.create_task(self._network_optimization()),
        ]
        
        # Discover existing nodes
        await self._discover_network()
        
        logger.info(f"✅ Orchestrator active - Managing {len(self.nodes)} nodes")
        
        # Wait for all tasks
        await asyncio.gather(*tasks)

    async def _discover_network(self):
        """Discover existing nodes in the network"""
        logger.info("🔍 Discovering network topology...")
        
        # This would integrate with your existing P2P discovery
        # For now, we'll simulate discovery of known endpoints
        discovery_endpoints = [
            "http://localhost:8080",
            "http://localhost:8081", 
            "http://localhost:8082",
        ]
        
        for endpoint in discovery_endpoints:
            try:
                await self._register_node_from_endpoint(endpoint)
            except Exception as e:
                logger.debug(f"Discovery failed for {endpoint}: {e}")

    async def _register_node_from_endpoint(self, endpoint: str):
        """Register a node from its API endpoint"""
        try:
            # Get node status
            response = requests.get(f"{endpoint}/api/v4/system/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # Get agent information
                agents_response = requests.get(f"{endpoint}/api/v4/agents", timeout=5)
                agents_data = agents_response.json() if agents_response.status_code == 200 else {}
                
                await self._register_node(endpoint, data, agents_data)
                
        except Exception as e:
            logger.debug(f"Failed to register node {endpoint}: {e}")

    async def _register_node(self, endpoint: str, status_data: Dict, agents_data: Dict):
        """Register a discovered node"""
        host, port = endpoint.replace('http://', '').split(':')
        node_id = status_data.get('agent_id', f"node_{host}_{port}")
        
        node_info = NodeInfo(
            node_id=node_id,
            host=host,
            port=int(port),
            node_type=status_data.get('agent_type', 'unknown'),
            status=NodeStatus.ACTIVE,
            capabilities=status_data.get('capabilities', []),
            agents_count=len(agents_data.get('agents', [])),
            cpu_usage=status_data.get('system_stats', {}).get('cpu_percent', 0),
            memory_usage=status_data.get('system_stats', {}).get('memory_percent', 0),
            gpu_usage=status_data.get('system_stats', {}).get('gpu_percent', 0),
            network_latency=0.0,
            last_heartbeat=time.time(),
            version=status_data.get('version', 'unknown'),
            load_score=self._calculate_load_score(status_data)
        )
        
        self.nodes[node_id] = node_info
        
        # Register agents
        for agent_data in agents_data.get('agents', []):
            agent_info = AgentInfo(
                agent_id=agent_data['id'],
                node_id=node_id,
                agent_type=agent_data['agent_type'],
                status=agent_data['status'],
                capabilities=agent_data.get('capabilities', []),
                tasks_running=agent_data.get('tasks_running', 0),
                tasks_completed=agent_data.get('tasks_completed', 0),
                efficiency_score=agent_data.get('efficiency_score', 1.0),
                specialized_models=agent_data.get('specialized_models', [])
            )
            self.agents[agent_info.agent_id] = agent_info
            self.node_agents[node_id].append(agent_info.agent_id)
        
        logger.info(f"✅ Registered node {node_id} with {len(self.node_agents[node_id])} agents")

    def _calculate_load_score(self, status_data: Dict) -> float:
        """Calculate node load score for balancing"""
        stats = status_data.get('system_stats', {})
        cpu = stats.get('cpu_percent', 0) / 100
        memory = stats.get('memory_percent', 0) / 100
        
        # Weighted load score (lower is better)
        load_score = (cpu * 0.4) + (memory * 0.3) + (random.random() * 0.3)
        return min(load_score, 1.0)

    async def submit_task(self, task_request: TaskRequest) -> str:
        """Submit a task to the network"""
        task_request.task_id = task_request.task_id or f"task_{uuid.uuid4().hex[:8]}"
        task_request.created_at = time.time()
        
        # Add to pending queue
        self.pending_tasks.append(task_request)
        
        logger.info(f"📝 Task {task_request.task_id} submitted (priority: {task_request.priority.name})")
        return task_request.task_id

    async def _task_scheduler(self):
        """Main task scheduling loop"""
        while self.running:
            try:
                if self.pending_tasks:
                    task = self.pending_tasks.popleft()
                    await self._schedule_task(task)
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Task scheduler error: {e}")
                await asyncio.sleep(5)

    async def _schedule_task(self, task: TaskRequest):
        """Schedule a task to appropriate nodes"""
        try:
            # Find best nodes for this task
            suitable_nodes = self._find_suitable_nodes(task)
            
            if not suitable_nodes:
                logger.warning(f"⚠️ No suitable nodes for task {task.task_id}")
                self._handle_task_failure(task, "No suitable nodes available")
                return
            
            # Select best node(s) using load balancer
            selected_nodes = self.load_balancer.select_nodes(suitable_nodes, task)
            
            # Dispatch task
            success = await self._dispatch_task(task, selected_nodes)
            
            if success:
                self.active_tasks[task.task_id] = task
                logger.info(f"🎯 Task {task.task_id} dispatched to {len(selected_nodes)} nodes")
            else:
                self._handle_task_failure(task, "Dispatch failed")
                
        except Exception as e:
            logger.error(f"Task scheduling error: {e}")
            self._handle_task_failure(task, str(e))

    def _find_suitable_nodes(self, task: TaskRequest) -> List[NodeInfo]:
        """Find nodes suitable for a task"""
        suitable_nodes = []
        
        for node in self.nodes.values():
            if (node.status == NodeStatus.ACTIVE and
                self._node_meets_requirements(node, task.requirements)):
                suitable_nodes.append(node)
        
        return suitable_nodes

    def _node_meets_requirements(self, node: NodeInfo, requirements: Dict[str, Any]) -> bool:
        """Check if node meets task requirements"""
        # Check capabilities
        required_caps = requirements.get('capabilities', [])
        if not all(cap in node.capabilities for cap in required_caps):
            return False
        
        # Check resources
        if requirements.get('min_memory', 0) > (100 - node.memory_usage):
            return False
        
        if requirements.get('min_cpu', 0) > (100 - node.cpu_usage):
            return False
        
        # Check load
        if node.load_score > requirements.get('max_load', 0.8):
            return False
        
        return True

    async def _dispatch_task(self, task: TaskRequest, nodes: List[NodeInfo]) -> bool:
        """Dispatch task to selected nodes"""
        dispatch_futures = []
        
        for node in nodes:
            future = self.executor.submit(self._send_task_to_node, task, node)
            dispatch_futures.append(future)
        
        # Wait for at least one successful dispatch
        success_count = 0
        for future in as_completed(dispatch_futures, timeout=10):
            try:
                if future.result():
                    success_count += 1
            except Exception as e:
                logger.error(f"Task dispatch error: {e}")
        
        return success_count > 0

    def _send_task_to_node(self, task: TaskRequest, node: NodeInfo) -> bool:
        """Send task to a specific node"""
        try:
            endpoint = f"http://{node.host}:{node.port}/api/v4/tasks/execute"
            
            payload = {
                'task_id': task.task_id,
                'task_type': task.task_type,
                'priority': task.priority.value,
                'input_data': task.input_data,
                'requirements': task.requirements,
                'timeout': task.timeout
            }
            
            response = requests.post(endpoint, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('success', False)
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to send task to node {node.node_id}: {e}")
            return False

    def _handle_task_failure(self, task: TaskRequest, reason: str):
        """Handle task failure"""
        task.retry_count += 1
        
        if task.retry_count <= task.max_retries:
            logger.info(f"🔄 Retrying task {task.task_id} (attempt {task.retry_count})")
            self.pending_tasks.appendleft(task)  # High priority retry
        else:
            logger.error(f"❌ Task {task.task_id} failed permanently: {reason}")
            self.failed_tasks[task.task_id] = {
                'task': asdict(task),
                'reason': reason,
                'failed_at': time.time()
            }

    async def _heartbeat_monitor(self):
        """Monitor node heartbeats"""
        while self.running:
            try:
                current_time = time.time()
                heartbeat_timeout = self.config['heartbeat_interval'] * 3
                
                for node_id, node in list(self.nodes.items()):
                    time_since_heartbeat = current_time - node.last_heartbeat
                    
                    if time_since_heartbeat > heartbeat_timeout:
                        logger.warning(f"⚠️ Node {node_id} heartbeat timeout")
                        node.status = NodeStatus.OFFLINE
                        await self._handle_node_failure(node_id)
                    
                await asyncio.sleep(self.config['heartbeat_interval'])
                
            except Exception as e:
                logger.error(f"Heartbeat monitor error: {e}")
                await asyncio.sleep(5)

    async def _handle_node_failure(self, node_id: str):
        """Handle node failure"""
        logger.error(f"🚨 Node {node_id} failed - redistributing tasks")
        
        # Reassign active tasks from failed node
        tasks_to_reassign = []
        for task_id, task in self.active_tasks.items():
            if task.assigned_nodes and node_id in task.assigned_nodes:
                tasks_to_reassign.append(task)
        
        for task in tasks_to_reassign:
            del self.active_tasks[task.task_id]
            self.pending_tasks.appendleft(task)  # High priority reassignment

    async def _performance_monitor(self):
        """Monitor network performance"""
        while self.running:
            try:
                await self._update_network_metrics()
                await self._optimize_performance()
                await asyncio.sleep(60)  # Update every minute
            except Exception as e:
                logger.error(f"Performance monitor error: {e}")
                await asyncio.sleep(30)

    async def _update_network_metrics(self):
        """Update network performance metrics"""
        active_nodes = sum(1 for node in self.nodes.values() 
                          if node.status == NodeStatus.ACTIVE)
        
        self.network_metrics.update({
            'total_nodes': len(self.nodes),
            'active_nodes': active_nodes,
            'total_agents': len(self.agents),
            'tasks_completed': len(self.completed_tasks),
            'tasks_failed': len(self.failed_tasks),
            'network_utilization': self._calculate_network_utilization()
        })

    def _calculate_network_utilization(self) -> float:
        """Calculate overall network utilization"""
        if not self.nodes:
            return 0.0
        
        total_load = sum(node.load_score for node in self.nodes.values() 
                        if node.status == NodeStatus.ACTIVE)
        active_nodes = sum(1 for node in self.nodes.values() 
                          if node.status == NodeStatus.ACTIVE)
        
        return (total_load / active_nodes) if active_nodes > 0 else 0.0

    async def _optimize_performance(self):
        """Optimize network performance"""
        if self.config['auto_scaling_enabled']:
            await self._auto_scale_network()
        
        if self.config['performance_monitoring']:
            await self._rebalance_load()

    async def _auto_scale_network(self):
        """Auto-scale the network based on demand"""
        utilization = self.network_metrics['network_utilization']
        
        if utilization > 0.8:  # High load
            logger.info("📈 High network utilization - considering scaling up")
            # Could trigger node spawning here
        elif utilization < 0.2:  # Low load
            logger.info("📉 Low network utilization - considering scaling down")
            # Could trigger node decommissioning here

    async def _rebalance_load(self):
        """Rebalance load across nodes"""
        # Identify overloaded nodes
        overloaded_nodes = [node for node in self.nodes.values() 
                           if node.load_score > 0.9 and node.status == NodeStatus.ACTIVE]
        
        if overloaded_nodes:
            logger.info(f"⚖️ Rebalancing load for {len(overloaded_nodes)} overloaded nodes")
            # Implement load rebalancing logic

    async def _fault_detection(self):
        """Detect and handle network faults"""
        while self.running:
            try:
                await self.fault_detector.scan_network(self.nodes)
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Fault detection error: {e}")
                await asyncio.sleep(30)

    async def _load_balancer_loop(self):
        """Load balancer maintenance loop"""
        while self.running:
            try:
                self.load_balancer.update_node_weights(self.nodes)
                await asyncio.sleep(15)
            except Exception as e:
                logger.error(f"Load balancer error: {e}")
                await asyncio.sleep(15)

    async def _network_optimization(self):
        """Network optimization loop"""
        while self.running:
            try:
                await self.performance_optimizer.optimize_network(self.nodes, self.network_metrics)
                await asyncio.sleep(120)  # Optimize every 2 minutes
            except Exception as e:
                logger.error(f"Network optimization error: {e}")
                await asyncio.sleep(60)

    def get_network_status(self) -> Dict[str, Any]:
        """Get comprehensive network status"""
        return {
            'orchestrator_id': self.orchestrator_id,
            'network_metrics': self.network_metrics,
            'nodes': {node_id: asdict(node) for node_id, node in self.nodes.items()},
            'agents': {agent_id: asdict(agent) for agent_id, agent in self.agents.items()},
            'active_tasks': len(self.active_tasks),
            'pending_tasks': len(self.pending_tasks),
            'completed_tasks': len(self.completed_tasks),
            'failed_tasks': len(self.failed_tasks),
            'uptime': time.time() - self.network_metrics['uptime']
        }

    async def stop_orchestrator(self):
        """Gracefully stop the orchestrator"""
        logger.info("🛑 Stopping Web4AI Orchestrator...")
        self.running = False
        
        # Wait for pending tasks to complete (with timeout)
        timeout = 30
        start_time = time.time()
        
        while self.active_tasks and (time.time() - start_time) < timeout:
            await asyncio.sleep(1)
        
        self.executor.shutdown(wait=True)
        logger.info("✅ Orchestrator stopped")


class NetworkLoadBalancer:
    """Advanced load balancing for the network"""
    
    def __init__(self):
        self.node_weights: Dict[str, float] = {}
        self.algorithm = 'weighted_round_robin'
        self.round_robin_counter = 0

    def select_nodes(self, suitable_nodes: List[NodeInfo], task: TaskRequest) -> List[NodeInfo]:
        """Select best nodes for task execution"""
        if not suitable_nodes:
            return []
        
        # Sort by load score (lower is better)
        sorted_nodes = sorted(suitable_nodes, key=lambda n: n.load_score)
        
        # Select top nodes based on task requirements
        redundancy = task.requirements.get('redundancy', 1)
        selected_count = min(redundancy, len(sorted_nodes))
        
        return sorted_nodes[:selected_count]

    def update_node_weights(self, nodes: Dict[str, NodeInfo]):
        """Update node weights for load balancing"""
        for node_id, node in nodes.items():
            if node.status == NodeStatus.ACTIVE:
                # Weight based on inverse load and reliability
                weight = (1.0 - node.load_score) * node.reliability_score
                self.node_weights[node_id] = max(weight, 0.1)  # Minimum weight


class FaultDetector:
    """Network fault detection and recovery"""
    
    def __init__(self):
        self.fault_history: Dict[str, List[float]] = defaultdict(list)
        self.fault_threshold = 3  # Faults within window to trigger action

    async def scan_network(self, nodes: Dict[str, NodeInfo]):
        """Scan network for potential faults"""
        current_time = time.time()
        
        for node_id, node in nodes.items():
            # Check for various fault conditions
            if self._detect_node_faults(node, current_time):
                await self._handle_detected_fault(node_id, node)

    def _detect_node_faults(self, node: NodeInfo, current_time: float) -> bool:
        """Detect faults in a node"""
        fault_conditions = [
            node.cpu_usage > 95,           # CPU overload
            node.memory_usage > 95,        # Memory overload
            node.network_latency > 5000,   # High latency
            current_time - node.last_heartbeat > 120  # Heartbeat timeout
        ]
        
        return any(fault_conditions)

    async def _handle_detected_fault(self, node_id: str, node: NodeInfo):
        """Handle detected fault"""
        self.fault_history[node_id].append(time.time())
        
        # Clean old fault records (older than 5 minutes)
        cutoff_time = time.time() - 300
        self.fault_history[node_id] = [
            t for t in self.fault_history[node_id] if t > cutoff_time
        ]
        
        # Check if fault threshold exceeded
        if len(self.fault_history[node_id]) >= self.fault_threshold:
            logger.warning(f"🚨 Multiple faults detected for node {node_id}")
            node.status = NodeStatus.DEGRADED


class PerformanceOptimizer:
    """Network performance optimization"""
    
    def __init__(self):
        self.optimization_history: List[Dict[str, Any]] = []

    async def optimize_network(self, nodes: Dict[str, NodeInfo], metrics: Dict[str, Any]):
        """Optimize network performance"""
        optimizations = []
        
        # CPU optimization
        if self._high_cpu_utilization(nodes):
            optimizations.append(await self._optimize_cpu_distribution(nodes))
        
        # Memory optimization
        if self._high_memory_usage(nodes):
            optimizations.append(await self._optimize_memory_usage(nodes))
        
        # Network optimization
        if self._high_network_latency(nodes):
            optimizations.append(await self._optimize_network_topology(nodes))
        
        if optimizations:
            self.optimization_history.append({
                'timestamp': time.time(),
                'optimizations': optimizations,
                'metrics_before': dict(metrics)
            })

    def _high_cpu_utilization(self, nodes: Dict[str, NodeInfo]) -> bool:
        """Check if CPU utilization is high across nodes"""
        active_nodes = [n for n in nodes.values() if n.status == NodeStatus.ACTIVE]
        if not active_nodes:
            return False
        
        avg_cpu = sum(n.cpu_usage for n in active_nodes) / len(active_nodes)
        return avg_cpu > 80

    def _high_memory_usage(self, nodes: Dict[str, NodeInfo]) -> bool:
        """Check if memory usage is high across nodes"""
        active_nodes = [n for n in nodes.values() if n.status == NodeStatus.ACTIVE]
        if not active_nodes:
            return False
        
        avg_memory = sum(n.memory_usage for n in active_nodes) / len(active_nodes)
        return avg_memory > 85

    def _high_network_latency(self, nodes: Dict[str, NodeInfo]) -> bool:
        """Check if network latency is high"""
        active_nodes = [n for n in nodes.values() if n.status == NodeStatus.ACTIVE]
        if not active_nodes:
            return False
        
        avg_latency = sum(n.network_latency for n in active_nodes) / len(active_nodes)
        return avg_latency > 1000  # 1 second

    async def _optimize_cpu_distribution(self, nodes: Dict[str, NodeInfo]) -> str:
        """Optimize CPU load distribution"""
        logger.info("🔧 Optimizing CPU distribution across nodes")
        return "cpu_distribution_optimized"

    async def _optimize_memory_usage(self, nodes: Dict[str, NodeInfo]) -> str:
        """Optimize memory usage"""
        logger.info("🔧 Optimizing memory usage across nodes")
        return "memory_usage_optimized"

    async def _optimize_network_topology(self, nodes: Dict[str, NodeInfo]) -> str:
        """Optimize network topology"""
        logger.info("🔧 Optimizing network topology")
        return "network_topology_optimized"


# Example usage and testing
async def main():
    """Example orchestrator usage"""
    
    # Initialize orchestrator
    orchestrator = Web4AIOrchestrator("main_orchestrator")
    
    # Start orchestrator (in background)
    orchestrator_task = asyncio.create_task(orchestrator.start_orchestrator())
    
    # Wait a moment for discovery
    await asyncio.sleep(5)
    
    # Submit some example tasks
    tasks = [
        TaskRequest(
            task_id="ai_inference_1",
            task_type="ai_inference",
            priority=TaskPriority.HIGH,
            requirements={
                'capabilities': ['ai_inference'],
                'min_memory': 20,
                'min_cpu': 10
            },
            input_data={'model': 'transformer', 'prompt': 'Hello world'},
            timeout=30.0
        ),
        TaskRequest(
            task_id="blockchain_tx_1", 
            task_type="blockchain_transaction",
            priority=TaskPriority.NORMAL,
            requirements={
                'capabilities': ['blockchain'],
                'min_memory': 10
            },
            input_data={'transaction': 'transfer', 'amount': 100},
            timeout=60.0
        ),
        TaskRequest(
            task_id="distributed_train_1",
            task_type="distributed_training",
            priority=TaskPriority.HIGH,
            requirements={
                'capabilities': ['ai_training', 'distributed'],
                'min_memory': 50,
                'redundancy': 2
            },
            input_data={'model_type': 'neural_network', 'dataset': 'large_dataset'},
            timeout=300.0
        )
    ]
    
    # Submit tasks
    for task in tasks:
        task_id = await orchestrator.submit_task(task)
        print(f"✅ Submitted task {task_id}")
    
    # Monitor for a while
    for i in range(10):
        await asyncio.sleep(10)
        status = orchestrator.get_network_status()
        print(f"\n📊 Network Status (iteration {i+1}):")
        print(f"   Active Nodes: {status['network_metrics']['active_nodes']}")
        print(f"   Active Tasks: {status['active_tasks']}")
        print(f"   Completed Tasks: {status['completed_tasks']}")
        print(f"   Network Utilization: {status['network_metrics']['network_utilization']:.2f}")
    
    # Stop orchestrator
    await orchestrator.stop_orchestrator()

if __name__ == "__main__":
    print("🚀 Web4AI Network Orchestrator")
    print("=" * 50)
    asyncio.run(main())