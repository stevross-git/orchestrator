# scaling/auto_scaler.py - Advanced Auto-scaling System
"""
Advanced auto-scaling system for Web4AI Orchestrator
Handles dynamic node scaling based on load, performance metrics, and predictive analysis
"""

import asyncio
import time
import json
import logging
import statistics
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import requests
import docker
import boto3
from kubernetes import client, config

logger = logging.getLogger(__name__)

class ScalingAction(Enum):
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    MAINTAIN = "maintain"

class ScalingProvider(Enum):
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    AWS_EC2 = "aws_ec2"
    MANUAL = "manual"

@dataclass
class ScalingRule:
    """Auto-scaling rule definition"""
    name: str
    metric_name: str
    threshold_up: float
    threshold_down: float
    comparison: str  # greater, less, equal
    window_minutes: int
    cooldown_minutes: int
    min_nodes: int
    max_nodes: int
    scale_up_count: int = 1
    scale_down_count: int = 1
    enabled: bool = True

@dataclass
class ScalingEvent:
    """Scaling event record"""
    timestamp: datetime
    action: ScalingAction
    rule_name: str
    current_nodes: int
    target_nodes: int
    metric_value: float
    threshold_value: float
    reason: str

class AutoScaler:
    """Main auto-scaling engine"""
    
    def __init__(self, orchestrator, config: Dict[str, Any]):
        self.orchestrator = orchestrator
        self.config = config
        self.scaling_rules: Dict[str, ScalingRule] = {}
        self.scaling_events: List[ScalingEvent] = []
        self.last_scaling_action: Dict[str, datetime] = {}
        self.running = False
        
        # Initialize scaling providers
        self.providers = {
            ScalingProvider.DOCKER: DockerScalingProvider(config),
            ScalingProvider.KUBERNETES: KubernetesScalingProvider(config),
            ScalingProvider.AWS_EC2: AWSScalingProvider(config),
            ScalingProvider.MANUAL: ManualScalingProvider(config)
        }
        
        self.active_provider = ScalingProvider(
            config.get('auto_scaling', {}).get('provider', 'manual')
        )
        
        # Setup default scaling rules
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default auto-scaling rules"""
        default_rules = [
            ScalingRule(
                name="high_utilization",
                metric_name="network_utilization",
                threshold_up=0.8,
                threshold_down=0.3,
                comparison="greater",
                window_minutes=5,
                cooldown_minutes=10,
                min_nodes=2,
                max_nodes=20,
                scale_up_count=2,
                scale_down_count=1
            ),
            ScalingRule(
                name="high_task_queue",
                metric_name="pending_tasks_ratio",
                threshold_up=0.5,  # 50% of tasks pending
                threshold_down=0.1,
                comparison="greater",
                window_minutes=3,
                cooldown_minutes=5,
                min_nodes=1,
                max_nodes=15,
                scale_up_count=3,
                scale_down_count=1
            ),
            ScalingRule(
                name="response_time",
                metric_name="average_response_time",
                threshold_up=3000,  # 3 seconds
                threshold_down=1000,
                comparison="greater",
                window_minutes=2,
                cooldown_minutes=8,
                min_nodes=1,
                max_nodes=10,
                scale_up_count=1,
                scale_down_count=1
            )
        ]
        
        for rule in default_rules:
            self.scaling_rules[rule.name] = rule
    
    def add_scaling_rule(self, rule: ScalingRule):
        """Add custom scaling rule"""
        self.scaling_rules[rule.name] = rule
        logger.info(f"Added scaling rule: {rule.name}")
    
    def remove_scaling_rule(self, rule_name: str):
        """Remove scaling rule"""
        if rule_name in self.scaling_rules:
            del self.scaling_rules[rule_name]
            logger.info(f"Removed scaling rule: {rule_name}")
    
    async def start_auto_scaling(self):
        """Start auto-scaling loop"""
        if self.running:
            return
        
        self.running = True
        logger.info("Auto-scaling started")
        
        while self.running:
            try:
                await self._evaluate_scaling_rules()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Auto-scaling error: {e}")
                await asyncio.sleep(60)
    
    def stop_auto_scaling(self):
        """Stop auto-scaling"""
        self.running = False
        logger.info("Auto-scaling stopped")
    
    async def _evaluate_scaling_rules(self):
        """Evaluate all scaling rules"""
        current_time = datetime.utcnow()
        current_nodes = len([n for n in self.orchestrator.nodes.values() 
                           if n.status.value == 'active'])
        
        for rule_name, rule in self.scaling_rules.items():
            if not rule.enabled:
                continue
            
            # Check cooldown period
            last_action_time = self.last_scaling_action.get(rule_name)
            if (last_action_time and 
                (current_time - last_action_time).seconds < rule.cooldown_minutes * 60):
                continue
            
            # Get metric values for the time window
            metric_values = await self._get_metric_values(
                rule.metric_name, 
                window_minutes=rule.window_minutes
            )
            
            if not metric_values:
                continue
            
            # Calculate average metric value
            avg_metric_value = statistics.mean(metric_values)
            
            # Determine scaling action
            action = self._determine_scaling_action(rule, avg_metric_value, current_nodes)
            
            if action != ScalingAction.MAINTAIN:
                await self._execute_scaling_action(action, rule, avg_metric_value, current_nodes)
    
    async def _get_metric_values(self, metric_name: str, window_minutes: int) -> List[float]:
        """Get metric values for the specified time window"""
        if not hasattr(self.orchestrator, 'monitoring_manager'):
            # Fallback to orchestrator metrics
            return [self.orchestrator.network_metrics.get(metric_name, 0)]
        
        since = datetime.utcnow() - timedelta(minutes=window_minutes)
        metric_data = self.orchestrator.monitoring_manager.metric_collector.get_metric_values(
            metric_name, since=since
        )
        
        return [data['value'] for data in metric_data]
    
    def _determine_scaling_action(self, rule: ScalingRule, metric_value: float, 
                                 current_nodes: int) -> ScalingAction:
        """Determine what scaling action to take"""
        
        # Check scale up condition
        if self._compare_metric(metric_value, rule.threshold_up, rule.comparison):
            if current_nodes < rule.max_nodes:
                return ScalingAction.SCALE_UP
        
        # Check scale down condition (opposite comparison)
        opposite_comparison = self._get_opposite_comparison(rule.comparison)
        if self._compare_metric(metric_value, rule.threshold_down, opposite_comparison):
            if current_nodes > rule.min_nodes:
                return ScalingAction.SCALE_DOWN
        
        return ScalingAction.MAINTAIN
    
    def _compare_metric(self, value: float, threshold: float, comparison: str) -> bool:
        """Compare metric value against threshold"""
        if comparison == "greater":
            return value > threshold
        elif comparison == "less":
            return value < threshold
        elif comparison == "equal":
            return abs(value - threshold) < 0.001
        return False
    
    def _get_opposite_comparison(self, comparison: str) -> str:
        """Get opposite comparison for scale down logic"""
        if comparison == "greater":
            return "less"
        elif comparison == "less":
            return "greater"
        return comparison
    
    async def _execute_scaling_action(self, action: ScalingAction, rule: ScalingRule,
                                    metric_value: float, current_nodes: int):
        """Execute the determined scaling action"""
        
        if action == ScalingAction.SCALE_UP:
            target_nodes = min(current_nodes + rule.scale_up_count, rule.max_nodes)
            nodes_to_add = target_nodes - current_nodes
            
            if nodes_to_add > 0:
                success = await self._scale_up(nodes_to_add)
                if success:
                    self._record_scaling_event(
                        action, rule.name, current_nodes, target_nodes,
                        metric_value, rule.threshold_up,
                        f"Scaled up {nodes_to_add} nodes due to {rule.metric_name} = {metric_value:.2f}"
                    )
        
        elif action == ScalingAction.SCALE_DOWN:
            target_nodes = max(current_nodes - rule.scale_down_count, rule.min_nodes)
            nodes_to_remove = current_nodes - target_nodes
            
            if nodes_to_remove > 0:
                success = await self._scale_down(nodes_to_remove)
                if success:
                    self._record_scaling_event(
                        action, rule.name, current_nodes, target_nodes,
                        metric_value, rule.threshold_down,
                        f"Scaled down {nodes_to_remove} nodes due to {rule.metric_name} = {metric_value:.2f}"
                    )
        
        # Update last action time
        self.last_scaling_action[rule.name] = datetime.utcnow()
    
    async def _scale_up(self, nodes_to_add: int) -> bool:
        """Scale up by adding nodes"""
        try:
            provider = self.providers[self.active_provider]
            success = await provider.scale_up(nodes_to_add)
            
            if success:
                logger.info(f"Successfully scaled up {nodes_to_add} nodes")
            else:
                logger.error(f"Failed to scale up {nodes_to_add} nodes")
            
            return success
            
        except Exception as e:
            logger.error(f"Scale up error: {e}")
            return False
    
    async def _scale_down(self, nodes_to_remove: int) -> bool:
        """Scale down by removing nodes"""
        try:
            # Select nodes for removal (prefer nodes with lowest utilization)
            nodes_to_remove_list = self._select_nodes_for_removal(nodes_to_remove)
            
            provider = self.providers[self.active_provider]
            success = await provider.scale_down(nodes_to_remove_list)
            
            if success:
                logger.info(f"Successfully scaled down {nodes_to_remove} nodes")
            else:
                logger.error(f"Failed to scale down {nodes_to_remove} nodes")
            
            return success
            
        except Exception as e:
            logger.error(f"Scale down error: {e}")
            return False
    
    def _select_nodes_for_removal(self, count: int) -> List[str]:
        """Select nodes for removal based on utilization"""
        active_nodes = [(node_id, node) for node_id, node in self.orchestrator.nodes.items() 
                       if node.status.value == 'active']
        
        # Sort by load score (ascending - remove least loaded nodes first)
        active_nodes.sort(key=lambda x: x[1].load_score)
        
        return [node_id for node_id, _ in active_nodes[:count]]
    
    def _record_scaling_event(self, action: ScalingAction, rule_name: str,
                            current_nodes: int, target_nodes: int,
                            metric_value: float, threshold_value: float, reason: str):
        """Record scaling event"""
        event = ScalingEvent(
            timestamp=datetime.utcnow(),
            action=action,
            rule_name=rule_name,
            current_nodes=current_nodes,
            target_nodes=target_nodes,
            metric_value=metric_value,
            threshold_value=threshold_value,
            reason=reason
        )
        
        self.scaling_events.append(event)
        
        # Keep only recent events (last 100)
        if len(self.scaling_events) > 100:
            self.scaling_events = self.scaling_events[-100:]
        
        logger.info(f"Scaling event: {reason}")
    
    def get_scaling_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get scaling history"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_events = [
            {
                'timestamp': event.timestamp.isoformat(),
                'action': event.action.value,
                'rule_name': event.rule_name,
                'current_nodes': event.current_nodes,
                'target_nodes': event.target_nodes,
                'metric_value': event.metric_value,
                'threshold_value': event.threshold_value,
                'reason': event.reason
            }
            for event in self.scaling_events
            if event.timestamp >= cutoff_time
        ]
        
        return recent_events

# Scaling provider implementations
class ScalingProvider:
    """Base class for scaling providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    async def scale_up(self, count: int) -> bool:
        """Scale up by adding nodes"""
        raise NotImplementedError
    
    async def scale_down(self, node_ids: List[str]) -> bool:
        """Scale down by removing specific nodes"""
        raise NotImplementedError

class DockerScalingProvider(ScalingProvider):
    """Docker-based scaling provider"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        try:
            self.client = docker.from_env()
            self.image_name = config.get('docker', {}).get('image_name', 'web4ai-node:latest')
            self.network_name = config.get('docker', {}).get('network_name', 'web4ai-network')
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.client = None
    
    async def scale_up(self, count: int) -> bool:
        """Scale up by creating new Docker containers"""
        if not self.client:
            return False
        
        try:
            for i in range(count):
                container_name = f"web4ai-node-auto-{int(time.time())}-{i}"
                
                # Create container with orchestrator URL
                orchestrator_url = self.config.get('orchestrator_url', 'http://orchestrator:9000')
                
                container = self.client.containers.run(
                    self.image_name,
                    name=container_name,
                    network=self.network_name,
                    environment={
                        'ORCHESTRATOR_URL': orchestrator_url,
                        'NODE_ID': f'auto-scaled-{container_name}'
                    },
                    detach=True,
                    restart_policy={"Name": "unless-stopped"}
                )
                
                logger.info(f"Created Docker container: {container_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Docker scale up failed: {e}")
            return False
    
    async def scale_down(self, node_ids: List[str]) -> bool:
        """Scale down by stopping Docker containers"""
        if not self.client:
            return False
        
        try:
            for node_id in node_ids:
                # Find container by node ID
                containers = self.client.containers.list(
                    filters={"label": f"node_id={node_id}"}
                )
                
                for container in containers:
                    container.stop()
                    container.remove()
                    logger.info(f"Removed Docker container for node: {node_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Docker scale down failed: {e}")
            return False

class KubernetesScalingProvider(ScalingProvider):
    """Kubernetes-based scaling provider"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        try:
            config.load_incluster_config()  # For in-cluster usage
            self.apps_v1 = client.AppsV1Api()
            self.deployment_name = config.get('kubernetes', {}).get('deployment_name', 'web4ai-nodes')
            self.namespace = config.get('kubernetes', {}).get('namespace', 'default')
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            self.apps_v1 = None
    
    async def scale_up(self, count: int) -> bool:
        """Scale up Kubernetes deployment"""
        if not self.apps_v1:
            return False
        
        try:
            # Get current deployment
            deployment = self.apps_v1.read_namespaced_deployment(
                name=self.deployment_name,
                namespace=self.namespace
            )
            
            # Update replica count
            current_replicas = deployment.spec.replicas or 0
            new_replicas = current_replicas + count
            
            deployment.spec.replicas = new_replicas
            
            # Update deployment
            self.apps_v1.patch_namespaced_deployment(
                name=self.deployment_name,
                namespace=self.namespace,
                body=deployment
            )
            
            logger.info(f"Scaled Kubernetes deployment to {new_replicas} replicas")
            return True
            
        except Exception as e:
            logger.error(f"Kubernetes scale up failed: {e}")
            return False
    
    async def scale_down(self, node_ids: List[str]) -> bool:
        """Scale down Kubernetes deployment"""
        if not self.apps_v1:
            return False
        
        try:
            # Get current deployment
            deployment = self.apps_v1.read_namespaced_deployment(
                name=self.deployment_name,
                namespace=self.namespace
            )
            
            # Update replica count
            current_replicas = deployment.spec.replicas or 0
            new_replicas = max(0, current_replicas - len(node_ids))
            
            deployment.spec.replicas = new_replicas
            
            # Update deployment
            self.apps_v1.patch_namespaced_deployment(
                name=self.deployment_name,
                namespace=self.namespace,
                body=deployment
            )
            
            logger.info(f"Scaled Kubernetes deployment to {new_replicas} replicas")
            return True
            
        except Exception as e:
            logger.error(f"Kubernetes scale down failed: {e}")
            return False

class AWSScalingProvider(ScalingProvider):
    """AWS EC2-based scaling provider"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        try:
            aws_config = config.get('aws', {})
            self.ec2 = boto3.client(
                'ec2',
                region_name=aws_config.get('region', 'us-east-1'),
                aws_access_key_id=aws_config.get('access_key_id'),
                aws_secret_access_key=aws_config.get('secret_access_key')
            )
            self.ami_id = aws_config.get('ami_id')
            self.instance_type = aws_config.get('instance_type', 't3.medium')
            self.security_group_ids = aws_config.get('security_group_ids', [])
            self.subnet_id = aws_config.get('subnet_id')
            self.key_name = aws_config.get('key_name')
        except Exception as e:
            logger.error(f"Failed to initialize AWS client: {e}")
            self.ec2 = None
    
    async def scale_up(self, count: int) -> bool:
        """Scale up by launching EC2 instances"""
        if not self.ec2 or not self.ami_id:
            return False
        
        try:
            # Launch instances
            response = self.ec2.run_instances(
                ImageId=self.ami_id,
                MinCount=count,
                MaxCount=count,
                InstanceType=self.instance_type,
                SecurityGroupIds=self.security_group_ids,
                SubnetId=self.subnet_id,
                KeyName=self.key_name,
                UserData=self._get_user_data_script(),
                TagSpecifications=[
                    {
                        'ResourceType': 'instance',
                        'Tags': [
                            {'Key': 'Name', 'Value': f'web4ai-auto-scaled-{int(time.time())}'},
                            {'Key': 'AutoScaled', 'Value': 'true'},
                            {'Key': 'Project', 'Value': 'web4ai'}
                        ]
                    }
                ]
            )
            
            instance_ids = [instance['InstanceId'] for instance in response['Instances']]
            logger.info(f"Launched AWS instances: {instance_ids}")
            return True
            
        except Exception as e:
            logger.error(f"AWS scale up failed: {e}")
            return False
    
    async def scale_down(self, node_ids: List[str]) -> bool:
        """Scale down by terminating EC2 instances"""
        if not self.ec2:
            return False
        
        try:
            # Find instances by node IDs (this would need custom tagging)
            # For now, we'll terminate the most recent auto-scaled instances
            
            response = self.ec2.describe_instances(
                Filters=[
                    {'Name': 'tag:AutoScaled', 'Values': ['true']},
                    {'Name': 'instance-state-name', 'Values': ['running']}
                ]
            )
            
            instances_to_terminate = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances_to_terminate.append(instance['InstanceId'])
                    if len(instances_to_terminate) >= len(node_ids):
                        break
                if len(instances_to_terminate) >= len(node_ids):
                    break
            
            if instances_to_terminate:
                self.ec2.terminate_instances(InstanceIds=instances_to_terminate)
                logger.info(f"Terminated AWS instances: {instances_to_terminate}")
            
            return True
            
        except Exception as e:
            logger.error(f"AWS scale down failed: {e}")
            return False
    
    def _get_user_data_script(self) -> str:
        """Get user data script for EC2 instances"""
        orchestrator_url = self.config.get('orchestrator_url', 'http://orchestrator:9000')
        
        return f"""#!/bin/bash
# Install and start Web4AI node
cd /opt/web4ai
export ORCHESTRATOR_URL="{orchestrator_url}"
export NODE_ID="aws-auto-$(hostname)-$(date +%s)"
python3 enhanced_node/node_server.py --port 8080 &
"""

class ManualScalingProvider(ScalingProvider):
    """Manual scaling provider - logs scaling requests"""
    
    async def scale_up(self, count: int) -> bool:
        """Log scale up request"""
        logger.info(f"MANUAL SCALING: Need to add {count} nodes")
        # In a real implementation, this could send notifications
        # or create tickets in a ticketing system
        return True
    
    async def scale_down(self, node_ids: List[str]) -> bool:
        """Log scale down request"""
        logger.info(f"MANUAL SCALING: Need to remove nodes: {node_ids}")
        return True