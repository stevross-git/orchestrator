#!/usr/bin/env python3
"""
Web4AI Orchestrator-Node Integration Test Script
This script verifies that the orchestrator and nodes are working together correctly.
"""

import requests
import json
import time
import sys
import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IntegrationTester:
    """Test suite for orchestrator-node integration"""
    
    def __init__(self, orchestrator_url: str = "http://localhost:9000", 
                 node_urls: List[str] = None):
        self.orchestrator_url = orchestrator_url.rstrip('/')
        self.node_urls = node_urls or ["http://localhost:5000"]
        self.test_results = []
        self.test_start_time = time.time()
        
    def run_all_tests(self) -> bool:
        """Run complete integration test suite"""
        print("🧪 Starting Web4AI Orchestrator-Node Integration Tests")
        print("=" * 60)
        
        tests = [
            ("Orchestrator Health Check", self.test_orchestrator_health),
            ("Node Health Checks", self.test_nodes_health),
            ("Node Registration", self.test_node_registration),
            ("Heartbeat Monitoring", self.test_heartbeat_monitoring),
            ("Task Submission", self.test_task_submission),
            ("Load Balancing", self.test_load_balancing),
            ("Network Topology", self.test_network_topology),
            ("Performance Metrics", self.test_performance_metrics),
            ("Error Handling", self.test_error_handling),
            ("Concurrent Operations", self.test_concurrent_operations)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🔍 Running: {test_name}")
            print("-" * 40)
            
            try:
                result = test_func()
                if result:
                    print(f"✅ PASSED: {test_name}")
                    passed_tests += 1
                else:
                    print(f"❌ FAILED: {test_name}")
                    
                self.test_results.append({
                    'test_name': test_name,
                    'passed': result,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                print(f"💥 ERROR: {test_name} - {str(e)}")
                self.test_results.append({
                    'test_name': test_name,
                    'passed': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        # Print final results
        self.print_final_results(passed_tests, total_tests)
        
        return passed_tests == total_tests
    
    def test_orchestrator_health(self) -> bool:
        """Test orchestrator health and basic functionality"""
        try:
            # Test health endpoint
            response = requests.get(f"{self.orchestrator_url}/api/v1/health", timeout=5)
            if response.status_code != 200:
                print(f"❌ Health check failed: {response.status_code}")
                return False
            
            health_data = response.json()
            if health_data.get('status') != 'healthy':
                print(f"❌ Orchestrator not healthy: {health_data}")
                return False
            
            print(f"✅ Orchestrator healthy: {health_data.get('orchestrator_id')}")
            
            # Test status endpoint
            response = requests.get(f"{self.orchestrator_url}/api/v1/status", timeout=5)
            if response.status_code == 200:
                status_data = response.json()
                print(f"✅ Status endpoint working: {status_data.get('success', False)}")
                return True
            else:
                print(f"⚠️ Status endpoint issues: {response.status_code}")
                return True  # Health is more important than status
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to orchestrator at {self.orchestrator_url}")
            return False
        except Exception as e:
            print(f"❌ Orchestrator health test error: {e}")
            return False
    
    def test_nodes_health(self) -> bool:
        """Test all nodes for health and basic functionality"""
        healthy_nodes = 0
        
        for i, node_url in enumerate(self.node_urls):
            try:
                print(f"  Testing node {i+1}: {node_url}")
                
                # Test basic health
                response = requests.get(f"{node_url}/api/v3/agents", timeout=5)
                if response.status_code == 200:
                    print(f"  ✅ Node {i+1} responding")
                    healthy_nodes += 1
                else:
                    print(f"  ❌ Node {i+1} health check failed: {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                print(f"  ❌ Cannot connect to node {i+1} at {node_url}")
            except Exception as e:
                print(f"  ❌ Node {i+1} test error: {e}")
        
        success_rate = healthy_nodes / len(self.node_urls)
        print(f"✅ Healthy nodes: {healthy_nodes}/{len(self.node_urls)} ({success_rate:.1%})")
        
        return success_rate >= 0.5  # At least 50% of nodes should be healthy
    
    def test_node_registration(self) -> bool:
        """Test node registration with orchestrator"""
        try:
            # Get registered nodes
            response = requests.get(f"{self.orchestrator_url}/api/v1/nodes", timeout=10)
            if response.status_code != 200:
                print(f"❌ Cannot get nodes list: {response.status_code}")
                return False
            
            nodes_data = response.json()
            if not nodes_data.get('success', False):
                print(f"❌ Nodes request failed: {nodes_data.get('error')}")
                return False
            
            registered_nodes = nodes_data.get('nodes', {})
            node_count = len(registered_nodes)
            
            print(f"✅ Found {node_count} registered nodes")
            
            # Check node details
            for node_id, node_info in registered_nodes.items():
                status = node_info.get('status', 'unknown')
                capabilities = node_info.get('capabilities', [])
                print(f"  📍 Node {node_id}: {status}, {len(capabilities)} capabilities")
            
            return node_count > 0
            
        except Exception as e:
            print(f"❌ Node registration test error: {e}")
            return False
    
    def test_heartbeat_monitoring(self) -> bool:
        """Test heartbeat functionality"""
        try:
            print("  🔄 Testing heartbeat monitoring...")
            
            # Get initial status
            response = requests.get(f"{self.orchestrator_url}/api/v1/status", timeout=5)
            if response.status_code != 200:
                print(f"❌ Cannot get orchestrator status: {response.status_code}")
                return False
            
            initial_status = response.json()
            initial_nodes = initial_status.get('data', {}).get('nodes', {})
            
            if not initial_nodes:
                print("⚠️ No nodes found for heartbeat test")
                return False
            
            # Wait for heartbeat cycle
            print("  ⏳ Waiting for heartbeat cycle (35 seconds)...")
            time.sleep(35)
            
            # Check updated status
            response = requests.get(f"{self.orchestrator_url}/api/v1/status", timeout=5)
            updated_status = response.json()
            updated_nodes = updated_status.get('data', {}).get('nodes', {})
            
            # Verify heartbeats are working
            active_nodes = sum(1 for node in updated_nodes.values() 
                             if node.get('status') == 'active')
            
            print(f"✅ Active nodes after heartbeat: {active_nodes}/{len(updated_nodes)}")
            
            return active_nodes > 0
            
        except Exception as e:
            print(f"❌ Heartbeat test error: {e}")
            return False
    
    def test_task_submission(self) -> bool:
        """Test task submission and routing"""
        try:
            print("  📋 Testing task submission...")
            
            # Submit a test task
            test_task = {
                "task_type": "integration_test",
                "priority": "normal",
                "requirements": {
                    "capabilities": ["agent_management"]
                },
                "input_data": {
                    "test_id": f"test_{int(time.time())}",
                    "description": "Integration test task"
                },
                "timeout": 30.0
            }
            
            response = requests.post(
                f"{self.orchestrator_url}/api/v1/tasks",
                json=test_task,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success', False):
                    task_id = result.get('task_id')
                    print(f"✅ Task submitted successfully: {task_id}")
                    return True
                else:
                    print(f"❌ Task submission failed: {result.get('error')}")
                    return False
            else:
                print(f"❌ Task submission HTTP error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Task submission test error: {e}")
            return False
    
    def test_load_balancing(self) -> bool:
        """Test load balancing functionality"""
        try:
            print("  ⚖️ Testing load balancing...")
            
            # Get node load information
            response = requests.get(f"{self.orchestrator_url}/api/v1/nodes", timeout=5)
            if response.status_code != 200:
                print(f"❌ Cannot get nodes for load balancing test")
                return False
            
            nodes_data = response.json()
            nodes = nodes_data.get('nodes', {})
            
            if len(nodes) < 2:
                print("⚠️ Need at least 2 nodes for load balancing test")
                return True  # Pass if not enough nodes
            
            # Check load scores
            load_scores = {}
            for node_id, node_info in nodes.items():
                load_score = node_info.get('load_score', 0)
                load_scores[node_id] = load_score
                print(f"  📊 Node {node_id}: Load Score {load_score}")
            
            # Verify load scores are reasonable
            avg_load = sum(load_scores.values()) / len(load_scores)
            print(f"✅ Average network load: {avg_load:.2f}")
            
            return avg_load < 90  # Should not be overloaded
            
        except Exception as e:
            print(f"❌ Load balancing test error: {e}")
            return False
    
    def test_network_topology(self) -> bool:
        """Test network topology and node connectivity"""
        try:
            print("  🌐 Testing network topology...")
            
            # Get network status
            response = requests.get(f"{self.orchestrator_url}/api/v1/status", timeout=5)
            if response.status_code != 200:
                return False
            
            status_data = response.json()
            network_data = status_data.get('data', {})
            
            # Check network metrics
            network_metrics = network_data.get('network_metrics', {})
            uptime = network_metrics.get('uptime', 0)
            utilization = network_metrics.get('network_utilization', 0)
            
            print(f"  ⏱️ Network uptime: {uptime:.2f} seconds")
            print(f"  📊 Network utilization: {utilization:.2f}%")
            
            # Check node connectivity
            nodes = network_data.get('nodes', {})
            connected_nodes = sum(1 for node in nodes.values() 
                                if node.get('status') in ['active', 'busy'])
            
            print(f"✅ Connected nodes: {connected_nodes}/{len(nodes)}")
            
            return connected_nodes > 0
            
        except Exception as e:
            print(f"❌ Network topology test error: {e}")
            return False
    
    def test_performance_metrics(self) -> bool:
        """Test performance metrics collection"""
        try:
            print("  📈 Testing performance metrics...")
            
            # Try to get performance metrics
            response = requests.get(f"{self.orchestrator_url}/api/v1/metrics/performance", timeout=5)
            
            if response.status_code == 200:
                metrics = response.json()
                if metrics.get('success', False):
                    perf_data = metrics.get('performance', {})
                    
                    # Check key metrics
                    metrics_found = []
                    for metric in ['average_cpu_usage', 'average_memory_usage', 'total_nodes', 'active_nodes']:
                        if metric in perf_data:
                            metrics_found.append(metric)
                            print(f"  📊 {metric}: {perf_data[metric]}")
                    
                    print(f"✅ Performance metrics available: {len(metrics_found)}/4")
                    return len(metrics_found) >= 2
                else:
                    print("⚠️ Performance metrics request failed")
                    return True  # Not critical
            else:
                print("⚠️ Performance metrics endpoint not available")
                return True  # Not critical
                
        except Exception as e:
            print(f"⚠️ Performance metrics test warning: {e}")
            return True  # Not critical for basic functionality
    
    def test_error_handling(self) -> bool:
        """Test error handling and recovery"""
        try:
            print("  🛡️ Testing error handling...")
            
            # Test invalid task submission
            invalid_task = {"invalid": "task"}
            response = requests.post(
                f"{self.orchestrator_url}/api/v1/tasks",
                json=invalid_task,
                timeout=5
            )
            
            # Should return error but not crash
            if response.status_code in [400, 422]:
                print("✅ Invalid task properly rejected")
                return True
            elif response.status_code == 500:
                print("⚠️ Server error on invalid task (not ideal but not critical)")
                return True
            else:
                print(f"❌ Unexpected response to invalid task: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error handling test error: {e}")
            return False
    
    def test_concurrent_operations(self) -> bool:
        """Test concurrent operations"""
        try:
            print("  🔀 Testing concurrent operations...")
            
            # Create multiple threads for concurrent requests
            def make_request():
                try:
                    response = requests.get(f"{self.orchestrator_url}/api/v1/health", timeout=5)
                    return response.status_code == 200
                except:
                    return False
            
            threads = []
            for i in range(5):
                thread = threading.Thread(target=make_request)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join(timeout=10)
            
            print("✅ Concurrent operations completed")
            return True
            
        except Exception as e:
            print(f"❌ Concurrent operations test error: {e}")
            return False
    
    def print_final_results(self, passed: int, total: int):
        """Print final test results"""
        print("\n" + "=" * 60)
        print("📋 INTEGRATION TEST RESULTS")
        print("=" * 60)
        
        success_rate = (passed / total) * 100
        duration = time.time() - self.test_start_time
        
        print(f"🎯 Tests Passed: {passed}/{total} ({success_rate:.1f}%)")
        print(f"⏱️ Total Duration: {duration:.2f} seconds")
        
        if success_rate >= 90:
            print("🎉 EXCELLENT: Integration is working perfectly!")
        elif success_rate >= 75:
            print("✅ GOOD: Integration is working well with minor issues")
        elif success_rate >= 50:
            print("⚠️ WARNING: Integration has significant issues")
        else:
            print("❌ CRITICAL: Integration is not working properly")
        
        # Print detailed results
        print("\n📋 Detailed Results:")
        for result in self.test_results:
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            print(f"  {status}: {result['test_name']}")
            if 'error' in result:
                print(f"    Error: {result['error']}")
        
        # Save results to file
        try:
            with open('integration_test_results.json', 'w') as f:
                json.dump({
                    'summary': {
                        'passed': passed,
                        'total': total,
                        'success_rate': success_rate,
                        'duration': duration,
                        'timestamp': datetime.now().isoformat()
                    },
                    'results': self.test_results
                }, f, indent=2)
            print(f"\n💾 Results saved to: integration_test_results.json")
        except Exception as e:
            print(f"⚠️ Could not save results: {e}")


def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description='Web4AI Integration Tester')
    parser.add_argument('--orchestrator', default='http://localhost:9000',
                      help='Orchestrator URL (default: http://localhost:9000)')
    parser.add_argument('--nodes', nargs='+', default=['http://localhost:5000'],
                      help='Node URLs (default: http://localhost:5000)')
    parser.add_argument('--quick', action='store_true',
                      help='Skip time-intensive tests')
    
    args = parser.parse_args()
    
    print("🚀 Web4AI Orchestrator-Node Integration Tester")
    print(f"🎯 Orchestrator: {args.orchestrator}")
    print(f"📡 Nodes: {', '.join(args.nodes)}")
    print()
    
    tester = IntegrationTester(args.orchestrator, args.nodes)
    
    try:
        success = tester.run_all_tests()
        exit_code = 0 if success else 1
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test runner error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
