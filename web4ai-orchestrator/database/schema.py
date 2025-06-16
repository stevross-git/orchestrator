# database/schema.py - Database Schema Definitions
"""
Database schema definitions and migrations for Web4AI Orchestrator
Supports PostgreSQL, MongoDB, and Redis storage backends
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

# SQLAlchemy for PostgreSQL
try:
    from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, Boolean, JSON
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, relationship
    from sqlalchemy.dialects.postgresql import UUID
    import sqlalchemy as sa
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

# MongoDB
try:
    import pymongo
    from pymongo import MongoClient
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

# Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

# PostgreSQL Schema Definitions
if SQLALCHEMY_AVAILABLE:
    Base = declarative_base()
    
    class OrchestratorModel(Base):
        """Orchestrator instance information"""
        __tablename__ = 'orchestrators'
        
        orchestrator_id = Column(String(64), primary_key=True)
        host = Column(String(255), nullable=False)
        port = Column(Integer, nullable=False)
        status = Column(String(32), nullable=False)
        version = Column(String(32))
        config = Column(JSON)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        last_heartbeat = Column(DateTime, default=datetime.utcnow)
    
    class NodeModel(Base):
        """Node information"""
        __tablename__ = 'nodes'
        
        node_id = Column(String(64), primary_key=True)
        orchestrator_id = Column(String(64), nullable=False)
        host = Column(String(255), nullable=False)
        port = Column(Integer, nullable=False)
        node_type = Column(String(64), nullable=False)
        status = Column(String(32), nullable=False)
        capabilities = Column(JSON)
        agents_count = Column(Integer, default=0)
        cpu_usage = Column(Float, default=0.0)
        memory_usage = Column(Float, default=0.0)
        gpu_usage = Column(Float, default=0.0)
        network_latency = Column(Float, default=0.0)
        load_score = Column(Float, default=0.0)
        reliability_score = Column(Float, default=1.0)
        version = Column(String(32))
        location = Column(String(255))
        metadata = Column(JSON)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        last_heartbeat = Column(DateTime, default=datetime.utcnow)
        tasks_completed = Column(Integer, default=0)
        tasks_failed = Column(Integer, default=0)
    
    class AgentModel(Base):
        """Agent information"""
        __tablename__ = 'agents'
        
        agent_id = Column(String(64), primary_key=True)
        node_id = Column(String(64), nullable=False)
        agent_type = Column(String(64), nullable=False)
        status = Column(String(32), nullable=False)
        capabilities = Column(JSON)
        specialized_models = Column(JSON)
        tasks_running = Column(Integer, default=0)
        tasks_completed = Column(Integer, default=0)
        efficiency_score = Column(Float, default=1.0)
        resource_usage = Column(JSON)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        last_activity = Column(DateTime, default=datetime.utcnow)
    
    class TaskModel(Base):
        """Task information"""
        __tablename__ = 'tasks'
        
        task_id = Column(String(64), primary_key=True)
        task_type = Column(String(64), nullable=False)
        status = Column(String(32), nullable=False)
        priority = Column(Integer, default=3)
        requirements = Column(JSON)
        input_data = Column(JSON)
        result_data = Column(JSON)
        error_message = Column(Text)
        assigned_nodes = Column(JSON)
        node_id = Column(String(64))
        agent_id = Column(String(64))
        created_at = Column(DateTime, default=datetime.utcnow)
        started_at = Column(DateTime)
        completed_at = Column(DateTime)
        deadline = Column(DateTime)
        timeout = Column(Integer, default=300)
        retry_count = Column(Integer, default=0)
        max_retries = Column(Integer, default=3)
        execution_time = Column(Float)
        callback_url = Column(String(512))
        metadata = Column(JSON)
    
    class MetricModel(Base):
        """Metrics storage"""
        __tablename__ = 'metrics'
        
        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        metric_name = Column(String(128), nullable=False, index=True)
        metric_value = Column(Float, nullable=False)
        tags = Column(JSON)
        source = Column(String(64))
        timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    class AlertModel(Base):
        """Alert information"""
        __tablename__ = 'alerts'
        
        alert_id = Column(String(64), primary_key=True)
        title = Column(String(255), nullable=False)
        description = Column(Text)
        severity = Column(String(32), nullable=False)
        status = Column(String(32), nullable=False)
        source = Column(String(64))
        metric_name = Column(String(128))
        metric_value = Column(Float)
        threshold_value = Column(Float)
        tags = Column(JSON)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        resolved_at = Column(DateTime)
        acknowledged_by = Column(String(64))

class DatabaseManager:
    """Unified database manager supporting multiple backends"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.storage_type = config.get('storage', {}).get('type', 'memory')
        self.connection = None
        self.session = None
        
        if self.storage_type == 'postgresql' and SQLALCHEMY_AVAILABLE:
            self._setup_postgresql()
        elif self.storage_type == 'mongodb' and PYMONGO_AVAILABLE:
            self._setup_mongodb()
        elif self.storage_type == 'redis' and REDIS_AVAILABLE:
            self._setup_redis()
        else:
            logger.info("Using in-memory storage")
            self._setup_memory()
    
    def _setup_postgresql(self):
        """Setup PostgreSQL connection"""
        try:
            db_config = self.config['storage']['postgresql']
            connection_string = (
                f"postgresql://{db_config['username']}:{db_config['password']}"
                f"@{db_config['host']}:{db_config.get('port', 5432)}"
                f"/{db_config['database']}"
            )
            
            self.engine = create_engine(connection_string, pool_size=20, max_overflow=30)
            Base.metadata.create_all(self.engine)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
            
            logger.info("PostgreSQL database connected")
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            self._setup_memory()
    
    def _setup_mongodb(self):
        """Setup MongoDB connection"""
        try:
            db_config = self.config['storage']['mongodb']
            client = MongoClient(
                host=db_config['host'],
                port=db_config.get('port', 27017),
                username=db_config.get('username'),
                password=db_config.get('password')
            )
            
            self.connection = client[db_config['database']]
            
            # Create indexes
            self._create_mongodb_indexes()
            
            logger.info("MongoDB database connected")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self._setup_memory()
    
    def _setup_redis(self):
        """Setup Redis connection"""
        try:
            redis_config = self.config['storage']['redis']
            self.connection = redis.Redis(
                host=redis_config['host'],
                port=redis_config.get('port', 6379),
                password=redis_config.get('password'),
                db=redis_config.get('db', 0),
                decode_responses=True
            )
            
            # Test connection
            self.connection.ping()
            
            logger.info("Redis database connected")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._setup_memory()
    
    def _setup_memory(self):
        """Setup in-memory storage"""
        self.storage_type = 'memory'
        self.memory_store = {
            'nodes': {},
            'agents': {},
            'tasks': {},
            'metrics': [],
            'alerts': {}
        }
        logger.info("Using in-memory storage")
    
    def _create_mongodb_indexes(self):
        """Create MongoDB indexes for performance"""
        # Nodes collection indexes
        self.connection.nodes.create_index([("orchestrator_id", 1), ("status", 1)])
        self.connection.nodes.create_index([("last_heartbeat", 1)])
        
        # Tasks collection indexes
        self.connection.tasks.create_index([("status", 1), ("created_at", -1)])
        self.connection.tasks.create_index([("task_type", 1), ("status", 1)])
        self.connection.tasks.create_index([("node_id", 1), ("status", 1)])
        
        # Metrics collection indexes
        self.connection.metrics.create_index([("metric_name", 1), ("timestamp", -1)])
        self.connection.metrics.create_index([("source", 1), ("timestamp", -1)])
        
        # Alerts collection indexes
        self.connection.alerts.create_index([("status", 1), ("severity", 1)])
        self.connection.alerts.create_index([("created_at", -1)])
    
    # Node operations
    def save_node(self, node_data: Dict[str, Any]) -> bool:
        """Save node information"""
        try:
            if self.storage_type == 'postgresql':
                node = NodeModel(**node_data)
                self.session.merge(node)
                self.session.commit()
                
            elif self.storage_type == 'mongodb':
                self.connection.nodes.replace_one(
                    {"node_id": node_data["node_id"]},
                    node_data,
                    upsert=True
                )
                
            elif self.storage_type == 'redis':
                self.connection.hset(
                    f"node:{node_data['node_id']}",
                    mapping=node_data
                )
                
            else:  # memory
                self.memory_store['nodes'][node_data['node_id']] = node_data
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save node: {e}")
            return False
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get node information"""
        try:
            if self.storage_type == 'postgresql':
                node = self.session.query(NodeModel).filter_by(node_id=node_id).first()
                return self._model_to_dict(node) if node else None
                
            elif self.storage_type == 'mongodb':
                node = self.connection.nodes.find_one({"node_id": node_id})
                if node:
                    node.pop('_id', None)  # Remove MongoDB ID
                return node
                
            elif self.storage_type == 'redis':
                node_data = self.connection.hgetall(f"node:{node_id}")
                return dict(node_data) if node_data else None
                
            else:  # memory
                return self.memory_store['nodes'].get(node_id)
                
        except Exception as e:
            logger.error(f"Failed to get node: {e}")
            return None
    
    def get_all_nodes(self, orchestrator_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all nodes"""
        try:
            if self.storage_type == 'postgresql':
                query = self.session.query(NodeModel)
                if orchestrator_id:
                    query = query.filter_by(orchestrator_id=orchestrator_id)
                nodes = query.all()
                return [self._model_to_dict(node) for node in nodes]
                
            elif self.storage_type == 'mongodb':
                filter_dict = {"orchestrator_id": orchestrator_id} if orchestrator_id else {}
                nodes = list(self.connection.nodes.find(filter_dict))
                for node in nodes:
                    node.pop('_id', None)
                return nodes
                
            elif self.storage_type == 'redis':
                nodes = []
                for key in self.connection.scan_iter(match="node:*"):
                    node_data = self.connection.hgetall(key)
                    if not orchestrator_id or node_data.get('orchestrator_id') == orchestrator_id:
                        nodes.append(dict(node_data))
                return nodes
                
            else:  # memory
                nodes = list(self.memory_store['nodes'].values())
                if orchestrator_id:
                    nodes = [n for n in nodes if n.get('orchestrator_id') == orchestrator_id]
                return nodes
                
        except Exception as e:
            logger.error(f"Failed to get nodes: {e}")
            return []
    
    def delete_node(self, node_id: str) -> bool:
        """Delete node"""
        try:
            if self.storage_type == 'postgresql':
                self.session.query(NodeModel).filter_by(node_id=node_id).delete()
                self.session.commit()
                
            elif self.storage_type == 'mongodb':
                self.connection.nodes.delete_one({"node_id": node_id})
                
            elif self.storage_type == 'redis':
                self.connection.delete(f"node:{node_id}")
                
            else:  # memory
                self.memory_store['nodes'].pop(node_id, None)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete node: {e}")
            return False
    
    # Task operations
    def save_task(self, task_data: Dict[str, Any]) -> bool:
        """Save task information"""
        try:
            if self.storage_type == 'postgresql':
                task = TaskModel(**task_data)
                self.session.merge(task)
                self.session.commit()
                
            elif self.storage_type == 'mongodb':
                self.connection.tasks.replace_one(
                    {"task_id": task_data["task_id"]},
                    task_data,
                    upsert=True
                )
                
            elif self.storage_type == 'redis':
                self.connection.hset(
                    f"task:{task_data['task_id']}",
                    mapping=task_data
                )
                
            else:  # memory
                self.memory_store['tasks'][task_data['task_id']] = task_data
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save task: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task information"""
        try:
            if self.storage_type == 'postgresql':
                task = self.session.query(TaskModel).filter_by(task_id=task_id).first()
                return self._model_to_dict(task) if task else None
                
            elif self.storage_type == 'mongodb':
                task = self.connection.tasks.find_one({"task_id": task_id})
                if task:
                    task.pop('_id', None)
                return task
                
            elif self.storage_type == 'redis':
                task_data = self.connection.hgetall(f"task:{task_id}")
                return dict(task_data) if task_data else None
                
            else:  # memory
                return self.memory_store['tasks'].get(task_id)
                
        except Exception as e:
            logger.error(f"Failed to get task: {e}")
            return None
    
    def get_tasks_by_status(self, status: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get tasks by status"""
        try:
            if self.storage_type == 'postgresql':
                tasks = (self.session.query(TaskModel)
                        .filter_by(status=status)
                        .order_by(TaskModel.created_at.desc())
                        .limit(limit)
                        .all())
                return [self._model_to_dict(task) for task in tasks]
                
            elif self.storage_type == 'mongodb':
                tasks = list(self.connection.tasks
                           .find({"status": status})
                           .sort("created_at", -1)
                           .limit(limit))
                for task in tasks:
                    task.pop('_id', None)
                return tasks
                
            elif self.storage_type == 'redis':
                # Redis doesn't have efficient querying, so we scan all tasks
                tasks = []
                for key in self.connection.scan_iter(match="task:*"):
                    task_data = self.connection.hgetall(key)
                    if task_data.get('status') == status:
                        tasks.append(dict(task_data))
                
                # Sort and limit
                tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                return tasks[:limit]
                
            else:  # memory
                tasks = [t for t in self.memory_store['tasks'].values() if t.get('status') == status]
                tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                return tasks[:limit]
                
        except Exception as e:
            logger.error(f"Failed to get tasks by status: {e}")
            return []
    
    # Metrics operations
    def save_metric(self, metric_data: Dict[str, Any]) -> bool:
        """Save metric data"""
        try:
            if self.storage_type == 'postgresql':
                metric = MetricModel(**metric_data)
                self.session.add(metric)
                self.session.commit()
                
            elif self.storage_type == 'mongodb':
                self.connection.metrics.insert_one(metric_data)
                
            elif self.storage_type == 'redis':
                # Store metrics with timestamp-based keys for time series
                timestamp = int(time.time())
                key = f"metric:{metric_data['metric_name']}:{timestamp}"
                self.connection.hset(key, mapping=metric_data)
                self.connection.expire(key, 86400 * 7)  # 7 days TTL
                
            else:  # memory
                self.memory_store['metrics'].append(metric_data)
                
                # Keep only recent metrics in memory
                cutoff_time = time.time() - (24 * 3600)  # 24 hours
                self.memory_store['metrics'] = [
                    m for m in self.memory_store['metrics']
                    if m.get('timestamp', 0) > cutoff_time
                ]
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save metric: {e}")
            return False
    
    def get_metrics(self, metric_name: str, since: Optional[datetime] = None,
                   until: Optional[datetime] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get metrics within time range"""
        try:
            if self.storage_type == 'postgresql':
                query = self.session.query(MetricModel).filter_by(metric_name=metric_name)
                
                if since:
                    query = query.filter(MetricModel.timestamp >= since)
                if until:
                    query = query.filter(MetricModel.timestamp <= until)
                
                metrics = query.order_by(MetricModel.timestamp.desc()).limit(limit).all()
                return [self._model_to_dict(metric) for metric in metrics]
                
            elif self.storage_type == 'mongodb':
                filter_dict = {"metric_name": metric_name}
                
                if since or until:
                    timestamp_filter = {}
                    if since:
                        timestamp_filter["$gte"] = since
                    if until:
                        timestamp_filter["$lte"] = until
                    filter_dict["timestamp"] = timestamp_filter
                
                metrics = list(self.connection.metrics
                             .find(filter_dict)
                             .sort("timestamp", -1)
                             .limit(limit))
                for metric in metrics:
                    metric.pop('_id', None)
                return metrics
                
            elif self.storage_type == 'redis':
                metrics = []
                pattern = f"metric:{metric_name}:*"
                
                for key in self.connection.scan_iter(match=pattern):
                    metric_data = self.connection.hgetall(key)
                    
                    # Filter by time range if specified
                    metric_time = metric_data.get('timestamp')
                    if metric_time:
                        try:
                            metric_timestamp = datetime.fromisoformat(metric_time)
                            if since and metric_timestamp < since:
                                continue
                            if until and metric_timestamp > until:
                                continue
                        except:
                            continue
                    
                    metrics.append(dict(metric_data))
                
                # Sort and limit
                metrics.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                return metrics[:limit]
                
            else:  # memory
                metrics = [m for m in self.memory_store['metrics'] 
                          if m.get('metric_name') == metric_name]
                
                if since or until:
                    filtered_metrics = []
                    for metric in metrics:
                        metric_time = metric.get('timestamp')
                        if isinstance(metric_time, str):
                            try:
                                metric_timestamp = datetime.fromisoformat(metric_time)
                            except:
                                continue
                        else:
                            metric_timestamp = metric_time
                        
                        if since and metric_timestamp < since:
                            continue
                        if until and metric_timestamp > until:
                            continue
                        
                        filtered_metrics.append(metric)
                    
                    metrics = filtered_metrics
                
                metrics.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                return metrics[:limit]
                
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return []
    
    def cleanup_old_data(self, retention_days: int = 7):
        """Clean up old data"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            if self.storage_type == 'postgresql':
                # Clean old metrics
                self.session.query(MetricModel).filter(
                    MetricModel.timestamp < cutoff_date
                ).delete()
                
                # Clean old completed tasks
                self.session.query(TaskModel).filter(
                    TaskModel.completed_at < cutoff_date,
                    TaskModel.status.in_(['completed', 'failed', 'cancelled'])
                ).delete()
                
                self.session.commit()
                
            elif self.storage_type == 'mongodb':
                # Clean old metrics
                self.connection.metrics.delete_many({
                    "timestamp": {"$lt": cutoff_date}
                })
                
                # Clean old completed tasks
                self.connection.tasks.delete_many({
                    "completed_at": {"$lt": cutoff_date},
                    "status": {"$in": ["completed", "failed", "cancelled"]}
                })
                
            elif self.storage_type == 'redis':
                # Redis handles TTL automatically for metrics
                # Clean old tasks
                for key in self.connection.scan_iter(match="task:*"):
                    task_data = self.connection.hgetall(key)
                    completed_at = task_data.get('completed_at')
                    if completed_at:
                        try:
                            completed_time = datetime.fromisoformat(completed_at)
                            if completed_time < cutoff_date:
                                self.connection.delete(key)
                        except:
                            pass
                
            else:  # memory
                cutoff_timestamp = cutoff_date.timestamp()
                
                # Clean old metrics
                self.memory_store['metrics'] = [
                    m for m in self.memory_store['metrics']
                    if m.get('timestamp', cutoff_timestamp + 1) > cutoff_timestamp
                ]
                
                # Clean old tasks
                tasks_to_keep = {}
                for task_id, task in self.memory_store['tasks'].items():
                    completed_at = task.get('completed_at')
                    if completed_at:
                        try:
                            if isinstance(completed_at, str):
                                completed_time = datetime.fromisoformat(completed_at)
                            else:
                                completed_time = completed_at
                            
                            if completed_time >= cutoff_date:
                                tasks_to_keep[task_id] = task
                        except:
                            tasks_to_keep[task_id] = task
                    else:
                        tasks_to_keep[task_id] = task
                
                self.memory_store['tasks'] = tasks_to_keep
            
            logger.info(f"Cleaned up data older than {retention_days} days")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
    
    def _model_to_dict(self, model) -> Dict[str, Any]:
        """Convert SQLAlchemy model to dictionary"""
        if not model:
            return None
        
        result = {}
        for column in model.__table__.columns:
            value = getattr(model, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        
        return result
    
    def close(self):
        """Close database connections"""
        try:
            if self.storage_type == 'postgresql' and self.session:
                self.session.close()
            elif self.storage_type == 'redis' and self.connection:
                self.connection.close()
            elif self.storage_type == 'mongodb' and self.connection:
                self.connection.client.close()
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")

# Performance optimization tools
class PerformanceOptimizer:
    """Performance optimization and tuning tools"""
    
    def __init__(self, database_manager: DatabaseManager):
        self.db = database_manager
        self.optimization_rules = []
        
    def analyze_task_patterns(self, days: int = 7) -> Dict[str, Any]:
        """Analyze task execution patterns for optimization"""
        since = datetime.utcnow() - timedelta(days=days)
        
        # Get recent tasks
        completed_tasks = self.db.get_tasks_by_status('completed', limit=10000)
        failed_tasks = self.db.get_tasks_by_status('failed', limit=1000)
        
        analysis = {
            'task_types': defaultdict(int),
            'execution_times': defaultdict(list),
            'failure_patterns': defaultdict(int),
            'node_performance': defaultdict(lambda: {'completed': 0, 'failed': 0, 'total_time': 0}),
            'peak_hours': defaultdict(int),
            'recommendations': []
        }
        
        # Analyze completed tasks
        for task in completed_tasks:
            task_type = task.get('task_type', 'unknown')
            execution_time = task.get('execution_time', 0)
            node_id = task.get('node_id')
            
            analysis['task_types'][task_type] += 1
            
            if execution_time:
                analysis['execution_times'][task_type].append(execution_time)
            
            if node_id:
                analysis['node_performance'][node_id]['completed'] += 1
                analysis['node_performance'][node_id]['total_time'] += execution_time
            
            # Extract hour from created_at for peak analysis
            created_at = task.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        created_time = datetime.fromisoformat(created_at)
                    else:
                        created_time = created_at
                    analysis['peak_hours'][created_time.hour] += 1
                except:
                    pass
        
        # Analyze failed tasks
        for task in failed_tasks:
            error_message = task.get('error_message', 'unknown error')
            node_id = task.get('node_id')
            
            analysis['failure_patterns'][error_message] += 1
            
            if node_id:
                analysis['node_performance'][node_id]['failed'] += 1
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_performance_recommendations(analysis)
        
        return analysis
    
    def _generate_performance_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # Check for slow task types
        for task_type, times in analysis['execution_times'].items():
            if times:
                avg_time = sum(times) / len(times)
                if avg_time > 300:  # 5 minutes
                    recommendations.append(
                        f"Task type '{task_type}' has high average execution time ({avg_time:.1f}s). "
                        f"Consider optimizing or adding more specialized nodes."
                    )
        
        # Check for high failure rates
        total_tasks = sum(analysis['task_types'].values())
        total_failures = sum(count for count in analysis['failure_patterns'].values())
        
        if total_tasks > 0:
            failure_rate = total_failures / total_tasks
            if failure_rate > 0.1:  # 10% failure rate
                recommendations.append(
                    f"High task failure rate ({failure_rate:.1%}). "
                    f"Review error patterns and node health."
                )
        
        # Check for unbalanced node performance
        node_performances = {}
        for node_id, stats in analysis['node_performance'].items():
            total_tasks = stats['completed'] + stats['failed']
            if total_tasks > 10:  # Only consider nodes with significant activity
                success_rate = stats['completed'] / total_tasks
                avg_time = stats['total_time'] / stats['completed'] if stats['completed'] > 0 else 0
                node_performances[node_id] = {'success_rate': success_rate, 'avg_time': avg_time}
        
        if len(node_performances) > 1:
            success_rates = [p['success_rate'] for p in node_performances.values()]
            if max(success_rates) - min(success_rates) > 0.2:  # 20% difference
                recommendations.append(
                    "Significant performance variation between nodes detected. "
                    "Consider load rebalancing or node health investigation."
                )
        
        # Check for peak hour patterns
        if analysis['peak_hours']:
            max_hour = max(analysis['peak_hours'], key=analysis['peak_hours'].get)
            min_hour = min(analysis['peak_hours'], key=analysis['peak_hours'].get)
            
            if analysis['peak_hours'][max_hour] > analysis['peak_hours'][min_hour] * 3:
                recommendations.append(
                    f"Peak usage detected at hour {max_hour}. "
                    f"Consider auto-scaling or pre-scaling resources during peak hours."
                )
        
        return recommendations
    
    def optimize_database_queries(self):
        """Optimize database queries and indexes"""
        optimization_results = {
            'indexes_created': [],
            'queries_optimized': [],
            'storage_cleaned': False
        }
        
        if self.db.storage_type == 'postgresql':
            # Create additional indexes for common queries
            indexes_to_create = [
                "CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks(status, created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_tasks_node_status ON tasks(node_id, status);",
                "CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp ON metrics(metric_name, timestamp DESC);",
                "CREATE INDEX IF NOT EXISTS idx_nodes_status_heartbeat ON nodes(status, last_heartbeat);"
            ]
            
            try:
                for index_sql in indexes_to_create:
                    self.db.session.execute(index_sql)
                    optimization_results['indexes_created'].append(index_sql)
                
                self.db.session.commit()
                
            except Exception as e:
                logger.error(f"Failed to create database indexes: {e}")
        
        elif self.db.storage_type == 'mongodb':
            # MongoDB indexes are created in _create_mongodb_indexes
            optimization_results['indexes_created'].append("MongoDB indexes verified")
        
        # Clean up old data
        try:
            self.db.cleanup_old_data(retention_days=7)
            optimization_results['storage_cleaned'] = True
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
        
        return optimization_results
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'task_analysis': self.analyze_task_patterns(),
            'database_optimization': self.optimize_database_queries(),
            'system_health': self._check_system_health(),
            'recommendations': []
        }
        
        # Combine all recommendations
        report['recommendations'].extend(report['task_analysis']['recommendations'])
        
        return report
    
    def _check_system_health(self) -> Dict[str, Any]:
        """Check overall system health"""
        import psutil
        
        return {
            'cpu_usage': psutil.cpu_percent(interval=1),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'network_connections': len(psutil.net_connections()),
            'processes': len(psutil.pids())
        }

# Database migration tools
class MigrationManager:
    """Handle database schema migrations"""
    
    def __init__(self, database_manager: DatabaseManager):
        self.db = database_manager
        self.migrations = [
            self._migration_001_initial_schema,
            self._migration_002_add_performance_indexes,
            self._migration_003_add_alert_tables,
        ]
    
    def run_migrations(self):
        """Run all pending migrations"""
        if self.db.storage_type != 'postgresql':
            logger.info("Migrations only supported for PostgreSQL")
            return
        
        # Create migrations table if it doesn't exist
        self.db.session.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db.session.commit()
        
        # Get applied migrations
        result = self.db.session.execute("SELECT version FROM schema_migrations")
        applied_versions = {row[0] for row in result}
        
        # Run pending migrations
        for i, migration in enumerate(self.migrations, 1):
            if i not in applied_versions:
                try:
                    logger.info(f"Running migration {i}")
                    migration()
                    
                    # Mark migration as applied
                    self.db.session.execute(
                        "INSERT INTO schema_migrations (version) VALUES (%s)",
                        (i,)
                    )
                    self.db.session.commit()
                    logger.info(f"Migration {i} completed")
                    
                except Exception as e:
                    logger.error(f"Migration {i} failed: {e}")
                    self.db.session.rollback()
                    raise
    
    def _migration_001_initial_schema(self):
        """Initial schema creation"""
        # Tables are created by SQLAlchemy, this is a placeholder
        pass
    
    def _migration_002_add_performance_indexes(self):
        """Add performance indexes"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_tasks_performance ON tasks(status, created_at, execution_time);",
            "CREATE INDEX IF NOT EXISTS idx_nodes_performance ON nodes(status, load_score, last_heartbeat);",
            "CREATE INDEX IF NOT EXISTS idx_metrics_performance ON metrics(metric_name, timestamp, metric_value);"
        ]
        
        for index_sql in indexes:
            self.db.session.execute(index_sql)
    
    def _migration_003_add_alert_tables(self):
        """Add alert-related tables and indexes"""
        # Alert table is already created by SQLAlchemy
        self.db.session.execute(
            "CREATE INDEX IF NOT EXISTS idx_alerts_status_severity ON alerts(status, severity, created_at);"
        )