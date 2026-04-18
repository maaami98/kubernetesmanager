#!/usr/bin/env python3
"""
km - Interactive Kubectl Manager
A simple kubectl wrapper with shortcuts for common operations
"""

import os
import sys
import yaml
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style


class KubeConfig:
    def __init__(self):
        self.config_path = Path.home() / ".kube" / "config"
        self.config = None
        self.load_config()

    def load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Error: kubeconfig not found at {self.config_path}")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"Error parsing kubeconfig: {e}")
            sys.exit(1)

    def get_clusters(self) -> List[str]:
        if self.config and 'clusters' in self.config:
            return [c['name'] for c in self.config['clusters']]
        return []

    def get_contexts(self) -> List[str]:
        if self.config and 'contexts' in self.config:
            return [c['name'] for c in self.config['contexts']]
        return []

    def get_current_context(self) -> Optional[str]:
        return self.config.get('current-context') if self.config else None

    def get_namespaces(self) -> List[str]:
        try:
            result = subprocess.run(
                ['kubectl', 'get', 'ns', '-o', 'jsonpath={.items[*].metadata.name}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip().split()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return []

    def set_context(self, context: str) -> bool:
        """Switch to a context"""
        try:
            result = subprocess.run(
                ['kubectl', 'config', 'use-context', context],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False


class KubectlCompleter(Completer):
    def __init__(self, commands: List[str], namespaces: List[str], pods: List[str], contexts: List[str] = None, 
                 deployments: List[str] = None, services: List[str] = None, 
                 current_namespace: str = None, current_resource_type: str = None, 
                 clusters: List[str] = None, current_cluster: str = None):
        self.commands = commands
        self.namespaces = namespaces or []
        self.pods = pods or []
        self.contexts = contexts or []
        self.deployments = deployments or []
        self.services = services or []
        self.clusters = clusters or []
        self.current_namespace = current_namespace
        self.current_resource_type = current_resource_type
        self.current_cluster = current_cluster
        self.current_command = ""
        self.command_args = []

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor(WORD=True)
        text_before_cursor = document.text[:document.cursor_position]
        
        # Split the current input to understand context
        parts = text_before_cursor.strip().split()
        current_part_index = len(parts) - 1 if parts else 0
        
        # If we're at the beginning or after a space, suggest commands
        if current_part_index == 0 or (text_before_cursor.endswith(' ') and not word_before_cursor):
            for cmd in self.commands:
                if cmd.startswith(word_before_cursor):
                    yield Completion(cmd, -len(word_before_cursor))
            return
        
        # If first word is 'cd', suggest based on current level
        if len(parts) >= 1 and parts[0].lower() == 'cd':
            if current_part_index == 1:  # cd <target>
                if not self.current_cluster:
                    # At root level, suggest clusters
                    for cluster in self.clusters:
                        if cluster.startswith(word_before_cursor):
                            yield Completion(cluster, -len(word_before_cursor))
                elif not self.current_namespace:
                    # In cluster, suggest namespaces
                    for ns in self.namespaces:
                        if ns.startswith(word_before_cursor):
                            yield Completion(ns, -len(word_before_cursor))
                elif not self.current_resource_type:
                    # In namespace, suggest resource types
                    resource_types = ['deployments', 'services', 'pods', 'routes']
                    for rt in resource_types:
                        if rt.startswith(word_before_cursor):
                            yield Completion(rt, -len(word_before_cursor))
                else:
                    # In resource type, suggest resource names
                    if self.current_resource_type == 'deployments':
                        resources = self.deployments
                    elif self.current_resource_type == 'services':
                        resources = self.services
                    elif self.current_resource_type == 'pods':
                        resources = self.pods
                    elif self.current_resource_type == 'routes':
                        # Routes için dinamik al, ama şimdilik boş
                        resources = []
                    else:
                        resources = []
                    
                    for res in resources:
                        if res.startswith(word_before_cursor):
                            yield Completion(res, -len(word_before_cursor))
            return
        
        # If first word is 'set' and second is 'namespace', suggest namespaces
        if len(parts) >= 2 and parts[0].lower() == 'set' and parts[1].lower() == 'namespace':
            if current_part_index == 2:  # set namespace <namespace>
                for ns in self.namespaces:
                    if ns.startswith(word_before_cursor):
                        yield Completion(ns, -len(word_before_cursor))
            return
        
        # If first word is 'set' and second is 'context', suggest contexts
        if len(parts) >= 2 and parts[0].lower() == 'set' and parts[1].lower() == 'context':
            if current_part_index == 2:  # set context <context>
                for ctx in self.contexts:
                    if ctx.startswith(word_before_cursor):
                        yield Completion(ctx, -len(word_before_cursor))
            return
        
        # If first word is 'exec', suggest pods
        if len(parts) >= 1 and parts[0].lower() == 'exec':
            if current_part_index == 1:  # exec <pod>
                for pod in self.pods:
                    if pod.startswith(word_before_cursor):
                        yield Completion(pod, -len(word_before_cursor))
            return
        
        # If first word is 'logs', suggest pods
        if len(parts) >= 1 and parts[0].lower() == 'logs':
            if current_part_index == 1:  # logs <pod>
                for pod in self.pods:
                    if pod.startswith(word_before_cursor):
                        yield Completion(pod, -len(word_before_cursor))
            return
        
        # If first word is 'describe' and second is 'pod', suggest pods
        if len(parts) >= 2 and parts[0].lower() == 'describe' and parts[1].lower() == 'pod':
            if current_part_index == 2:  # describe pod <pod>
                for pod in self.pods:
                    if pod.startswith(word_before_cursor):
                        yield Completion(pod, -len(word_before_cursor))
            return
        
        # If first word is 'delete' and second is 'pod', suggest pods
        if len(parts) >= 2 and parts[0].lower() == 'delete' and parts[1].lower() == 'pod':
            if current_part_index == 2:  # delete pod <pod>
                for pod in self.pods:
                    if pod.startswith(word_before_cursor):
                        yield Completion(pod, -len(word_before_cursor))
            return
        
        # If first word is 'cat', suggest files based on current level
        if len(parts) >= 1 and parts[0].lower() == 'cat':
            if current_part_index == 1:  # cat <file>
                files = ['yaml']
                if self.current_resource_type == 'pods':
                    files.extend(['log', 'events'])
                for f in files:
                    if f.startswith(word_before_cursor):
                        yield Completion(f, -len(word_before_cursor))
            return
        
        # If first word is 'more', suggest files based on current level
        if len(parts) >= 1 and parts[0].lower() == 'more':
            if current_part_index == 1:  # more <file>
                files = ['yaml']
                if self.current_resource_type == 'pods':
                    files.extend(['log', 'events'])
                for f in files:
                    if f.startswith(word_before_cursor):
                        yield Completion(f, -len(word_before_cursor))
            return
        
        # For other commands starting with 's', suggest them
        if word_before_cursor and word_before_cursor[0].lower() == 's':
            for cmd in self.commands:
                if cmd.startswith(word_before_cursor):
                    yield Completion(cmd, -len(word_before_cursor))


class KubectlManager:
    def __init__(self):
        self.kube_config = KubeConfig()
        self.current_context = self.kube_config.get_current_context()
        self.cached_clusters = self.kube_config.get_clusters()
        self.current_cluster = self._extract_cluster_from_context(self.current_context)
        self.current_namespace = None
        self.current_resource_type = None  # deployments, services, pods, routes
        self.current_resource_name = None  # specific resource name
        self.running = True
        self.ctrl_c_count = 0  # Track consecutive Ctrl+C presses
        self.cached_namespaces = []  # Cache namespaces for completion
        self.cached_pods = []  # Cache pods for completion
        self.cached_contexts = []  # Cache contexts for completion
        self.cached_deployments = []  # Cache deployments for completion
        self.cached_services = []  # Cache services for completion
        
        # Built-in commands
        self.commands = [
            'show clusters', 'show contexts', 'show namespaces', 'show pods', 
            'show deployments', 'show services', 'show nodes', 'show events',
            'describe pod', 'logs', 'exec', 'delete pod', 'apply', 'delete',
            'set namespace', 'cd', 'ls', 'pwd', 'tree', 'clear', 'cat', 'more', 'help', 'exit', 'quit', 'status'
        ]
        
        # Initialize caches
        self._update_namespace_cache()
        self._update_pod_cache()
        self._update_context_cache()
        self._update_deployment_cache()
        self._update_service_cache()

    def _update_namespace_cache(self):
        """Update cached namespaces"""
        try:
            self.cached_namespaces = self.kube_config.get_namespaces()
        except:
            self.cached_namespaces = []

    def _update_context_cache(self):
        """Update cached contexts"""
        try:
            self.cached_contexts = self.kube_config.get_contexts()
        except:
            self.cached_contexts = []

    def _extract_cluster_from_context(self, context_name: str) -> str:
        """Extract cluster name from context name."""
        if not context_name:
            return None
        try:
            for ctx in self.kube_config.config.get('contexts', []):
                if ctx.get('name') == context_name:
                    cluster = ctx.get('context', {}).get('cluster')
                    return cluster
        except:
            pass
        return None

    def _set_cluster_context(self, cluster_name: str) -> bool:
        """Switch to a cluster by finding its context."""
        try:
            for ctx in self.kube_config.config.get('contexts', []):
                if ctx.get('context', {}).get('cluster') == cluster_name:
                    context_name = ctx.get('name')
                    if self.kube_config.set_context(context_name):
                        self.current_context = context_name
                        self.current_cluster = cluster_name
                        return True
        except:
            pass
        return False

    def _navigate_path(self, path_parts: list) -> str:
        """Navigate using path like /cluster/namespace or /cluster/namespace/resource_type/resource_name."""
        try:
            # Start from root
            self.current_cluster = None
            self.current_namespace = None
            self.current_resource_type = None
            self.current_resource_name = None
            
            for i, part in enumerate(path_parts):
                if i == 0:
                    # First part is cluster
                    if part not in self.cached_clusters:
                        return f"Error: Cluster '{part}' not found. Available: {', '.join(self.cached_clusters)}"
                    if not self._set_cluster_context(part):
                        return f"Error: Could not switch to cluster '{part}'"
                    self.current_cluster = part
                    self._update_namespace_cache()
                elif i == 1:
                    # Second part is namespace
                    namespaces = self.kube_config.get_namespaces()
                    if part not in namespaces:
                        return f"Error: Namespace '{part}' not found in cluster {self.current_cluster}"
                    self.current_namespace = part
                    self._update_pod_cache()
                    self._update_deployment_cache()
                    self._update_service_cache()
                elif i == 2:
                    # Third part is resource_type
                    valid_types = ['deployments', 'services', 'pods', 'routes']
                    if part not in valid_types:
                        return f"Error: Invalid resource type '{part}'. Valid: {', '.join(valid_types)}"
                    self.current_resource_type = part
                elif i == 3:
                    # Fourth part is resource_name
                    if self.current_resource_type == 'deployments':
                        resources = self.cached_deployments
                    elif self.current_resource_type == 'services':
                        resources = self.cached_services
                    elif self.current_resource_type == 'pods':
                        resources = self.cached_pods
                    elif self.current_resource_type == 'routes':
                        try:
                            result = subprocess.run(
                                ['oc', 'get', 'routes', '-n', self.current_namespace, 
                                 '-o', 'jsonpath={.items[*].metadata.name}'],
                                capture_output=True, text=True, timeout=5
                            )
                            resources = result.stdout.strip().split() if result.returncode == 0 else []
                        except:
                            resources = []
                    else:
                        resources = []
                    
                    if part not in resources:
                        return f"Error: Resource '{part}' not found in {self.current_resource_type}"
                    self.current_resource_name = part
                else:
                    return f"Error: Path too deep. Maximum: /cluster/namespace/resource_type/resource_name"
            
            path_str = '/'.join([self.current_cluster or '', self.current_namespace or '', 
                                self.current_resource_type or '', self.current_resource_name or ''])
            path_str = '/' + path_str.strip('/')
            return f"✓ Switched to {path_str}"
        except Exception as e:
            return f"Error navigating path: {e}"

    def _update_pod_cache(self):
        """Update cached pods for current namespace"""
        try:
            args = ['get', 'pods', '-o', 'jsonpath={.items[*].metadata.name}']
            if self.current_namespace:
                args.extend(['-n', self.current_namespace])
            else:
                args.append('-A')
            
            result = subprocess.run(
                ['kubectl'] + args,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.cached_pods = result.stdout.strip().split()
            else:
                self.cached_pods = []
        except:
            self.cached_pods = []

    def _update_deployment_cache(self):
        """Update cached deployments for current namespace"""
        try:
            args = ['get', 'deployments', '-o', 'jsonpath={.items[*].metadata.name}']
            if self.current_namespace:
                args.extend(['-n', self.current_namespace])
            
            result = subprocess.run(
                ['kubectl'] + args,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.cached_deployments = result.stdout.strip().split()
            else:
                self.cached_deployments = []
        except:
            self.cached_deployments = []

    def _update_service_cache(self):
        """Update cached services for current namespace"""
        try:
            args = ['get', 'svc', '-o', 'jsonpath={.items[*].metadata.name}']
            if self.current_namespace:
                args.extend(['-n', self.current_namespace])
            
            result = subprocess.run(
                ['kubectl'] + args,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.cached_services = result.stdout.strip().split()
            else:
                self.cached_services = []
        except:
            self.cached_services = []

    def _show_namespace_contents(self) -> str:
        """Show resource types in current namespace"""
        if not self.current_namespace:
            return "Not in a namespace. Use 'cd <namespace>' first."
        
        output = f"\n📁 Resource Types in /{self.current_cluster}/{self.current_namespace}/:\n"
        output += "\n📦 deployments/\n"
        output += "🌐 services/\n"
        output += "🐳 pods/\n"
        output += "🛣️  routes/\n"
        
        output += "\n💡 Use 'cd <resource_type>' to enter a resource type"
        return output

    def _show_resource_type_contents(self, resource_type: str) -> str:
        """Show resources in a specific resource type"""
        if not self.current_namespace:
            return "Not in a namespace."
        
        output = f"\n📁 {resource_type.capitalize()} in {self.current_context}/{self.current_namespace}/{resource_type}/:\n"
        
        if resource_type == 'deployments':
            resources = self.cached_deployments
            icon = "📦"
        elif resource_type == 'services':
            resources = self.cached_services
            icon = "🌐"
        elif resource_type == 'pods':
            resources = self.cached_pods
            icon = "🐳"
        elif resource_type == 'routes':
            # Routes için oc get routes kullan (OpenShift)
            try:
                result = subprocess.run(
                    ['oc', 'get', 'routes', '-n', self.current_namespace, 
                     '-o', 'jsonpath={.items[*].metadata.name}'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    resources = result.stdout.strip().split()
                else:
                    resources = []
            except:
                resources = []
            icon = "🛣️"
        else:
            return f"Unknown resource type: {resource_type}"
        
        for res in sorted(resources):
            output += f"  {icon} {res}/\n"
        
        if not resources:
            output += "  (empty)\n"
        
        output += "\n💡 Use 'cd <resource_name>' to enter a resource"
        return output

    def _show_resource_contents(self, resource_type: str, resource_name: str) -> str:
        """Show files in a specific resource"""
        output = f"\n📁 Files in {self.current_context}/{self.current_namespace}/{resource_type}/{resource_name}/:\n"
        output += "  📄 yaml\n"
        
        if resource_type == 'pods':
            output += "  📄 log\n"
            output += "  📄 events\n"
        
        output += "\n💡 Use 'cat <file>' to view file contents"
        return output

    def _cat_file(self, filename: str) -> str:
        """Display file contents (currently only yaml supported)"""
        if not (self.current_resource_name and self.current_resource_type and self.current_namespace):
            return "Error: Not in a resource directory. Use 'cd' to navigate to a resource first."
        
        if filename.lower() == 'yaml':
            # Get YAML for current resource
            try:
                if self.current_resource_type == 'routes':
                    # Routes için oc kullan
                    cmd = ['oc', 'get', self.current_resource_type[:-1], self.current_resource_name, 
                           '-n', self.current_namespace, '-o', 'yaml']
                else:
                    cmd = ['kubectl', 'get', self.current_resource_type[:-1], self.current_resource_name, 
                           '-n', self.current_namespace, '-o', 'yaml']
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return result.stdout
                else:
                    return f"Error getting YAML: {result.stderr}"
            except subprocess.TimeoutExpired:
                return "Error: Command timed out"
            except FileNotFoundError:
                return f"Error: {'oc' if self.current_resource_type == 'routes' else 'kubectl'} not found"
        
        elif filename.lower() == 'log' and self.current_resource_type == 'pods':
            # Get pod logs with timestamps
            try:
                cmd = ['kubectl', 'logs', self.current_resource_name, '-n', self.current_namespace, '--timestamps']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                if result.returncode == 0:
                    return result.stdout
                else:
                    return f"Error getting logs: {result.stderr}"
            except subprocess.TimeoutExpired:
                return "Error: Command timed out"
            except FileNotFoundError:
                return "Error: kubectl not found"
        
        elif filename.lower() == 'events' and self.current_resource_type == 'pods':
            # Get pod events
            try:
                cmd = ['kubectl', 'get', 'events', '-n', self.current_namespace, 
                       '--field-selector', f'involvedObject.name={self.current_resource_name}', 
                       '-o', 'yaml']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return result.stdout
                else:
                    return f"Error getting events: {result.stderr}"
            except subprocess.TimeoutExpired:
                return "Error: Command timed out"
            except FileNotFoundError:
                return "Error: kubectl not found"
        
        else:
            return f"Error: File '{filename}' not found or not supported for {self.current_resource_type}."

    def _more_file(self, filename: str) -> str:
        """Display file contents with more pager"""
        if not (self.current_resource_name and self.current_resource_type and self.current_namespace):
            return "Error: Not in a resource directory. Use 'cd' to navigate to a resource first."
        
        # Get content
        content = self._get_file_content(filename)
        if content.startswith("Error"):
            return content
        
        # Run more command with stdin instead of temporary file
        try:
            print(f"\n--- Running more for {filename} ---")
            print("Commands: /search, arrow keys, space/page down, b/page up, q/quit")
            subprocess.run(['more'], input=content, text=True)
            return f"📄 More completed for: {filename}"
        except FileNotFoundError:
            return f"📄 Content:\n\n{content}\n\n(Note: 'more' command not found)"
        except Exception as e:
            return f"📄 Content:\n\n{content}\n\n(Error running more: {e})"

    def _get_file_content(self, filename: str) -> str:
        """Get file content without displaying (helper for more)"""
        if not (self.current_resource_name and self.current_resource_type and self.current_namespace):
            return "Error: Not in a resource directory."
        
        if filename.lower() == 'yaml':
            try:
                if self.current_resource_type == 'routes':
                    cmd = ['oc', 'get', self.current_resource_type[:-1], self.current_resource_name, 
                           '-n', self.current_namespace, '-o', 'yaml']
                else:
                    cmd = ['kubectl', 'get', self.current_resource_type[:-1], self.current_resource_name, 
                           '-n', self.current_namespace, '-o', 'yaml']
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return result.stdout
                else:
                    return f"Error getting YAML: {result.stderr}"
            except subprocess.TimeoutExpired:
                return "Error: Command timed out"
            except FileNotFoundError:
                return f"Error: {'oc' if self.current_resource_type == 'routes' else 'kubectl'} not found"
        
        elif filename.lower() == 'log' and self.current_resource_type == 'pods':
            try:
                cmd = ['kubectl', 'logs', self.current_resource_name, '-n', self.current_namespace, '--timestamps']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                if result.returncode == 0:
                    return result.stdout
                else:
                    return f"Error getting logs: {result.stderr}"
            except subprocess.TimeoutExpired:
                return "Error: Command timed out"
            except FileNotFoundError:
                return "Error: kubectl not found"
        
        elif filename.lower() == 'events' and self.current_resource_type == 'pods':
            try:
                cmd = ['kubectl', 'get', 'events', '-n', self.current_namespace, 
                       '--field-selector', f'involvedObject.name={self.current_resource_name}', 
                       '-o', 'yaml']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return result.stdout
                else:
                    return f"Error getting events: {result.stderr}"
            except subprocess.TimeoutExpired:
                return "Error: Command timed out"
            except FileNotFoundError:
                return "Error: kubectl not found"
        
        else:
            return f"Error: File '{filename}' not found or not supported."

    def _run_piped_command(self, command: str, input_text: str) -> str:
        """Run a command with piped input"""
        try:
            # Simple implementation for grep
            if command.startswith('grep '):
                pattern = command[5:].strip()
                lines = input_text.split('\n')
                matching_lines = [line for line in lines if pattern in line]
                return '\n'.join(matching_lines)
            else:
                return f"Error: Pipe command '{command}' not supported. Only 'grep' is supported for now."
        except Exception as e:
            return f"Error in piped command: {e}"

    def _show_tree(self) -> str:
        """Show tree structure of cluster/namespace hierarchy"""
        output = f"\n🌳 Cluster Structure: {self.current_context}\n"
        output += "└── 📁 Namespaces:\n"
        
        for i, ns in enumerate(sorted(self.cached_namespaces)):
            is_last = i == len(self.cached_namespaces) - 1
            prefix = "    └── " if is_last else "    ├── "
            marker = "✓ " if ns == self.current_namespace else ""
            
            output += f"{prefix}{marker}{ns}/\n"
            
            # If this is current namespace, show its contents
            if ns == self.current_namespace:
                try:
                    # Get deployments
                    result = subprocess.run(
                        ['kubectl', 'get', 'deployments', '-n', ns, 
                         '-o', 'jsonpath={.items[*].metadata.name}'],
                        capture_output=True, text=True, timeout=3
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        deployments = result.stdout.strip().split()
                        for j, deploy in enumerate(sorted(deployments)):
                            sub_prefix = "    │   └── " if not is_last else "        └── "
                            output += f"{sub_prefix}📦 {deploy}\n"
                except:
                    pass
                
                try:
                    # Get services
                    result = subprocess.run(
                        ['kubectl', 'get', 'svc', '-n', ns, 
                         '-o', 'jsonpath={.items[*].metadata.name}'],
                        capture_output=True, text=True, timeout=3
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        services = result.stdout.strip().split()
                        for j, svc in enumerate(sorted(services)):
                            sub_prefix = "    │   └── " if not is_last else "        └── "
                            output += f"{sub_prefix}🌐 {svc}\n"
                except:
                    pass
        
        return output

    def run_kubectl(self, args: List[str]) -> str:
        """Run kubectl command and return output"""
        cmd = ['kubectl'] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout if result.returncode == 0 else result.stderr
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except FileNotFoundError:
            return "Error: kubectl not found"

    def show_clusters(self) -> str:
        """Show available clusters"""
        clusters = self.kube_config.get_clusters()
        if not clusters:
            return "No clusters found"
        
        output = "\n📦 Clusters (root):\n"
        for cluster in sorted(clusters):
            marker = "✓" if cluster == self.current_cluster else " "
            output += f"  [{marker}] {cluster}/\n"
        output += "\n💡 Use 'cd <cluster>' to enter a cluster or 'cd /cluster/namespace' to navigate"
        return output

    def show_contexts(self) -> str:
        """Show available contexts"""
        contexts = self.kube_config.get_contexts()
        current = self.current_context
        
        if not contexts:
            return "No contexts found"
        
        output = "\n🔀 Available Contexts:\n"
        for ctx in contexts:
            marker = "✓" if ctx == current else " "
            output += f"  [{marker}] {ctx}\n"
        return output

    def show_namespaces(self) -> str:
        """Show available namespaces in folder-like structure"""
        namespaces = self.cached_namespaces
        if not namespaces:
            return "No namespaces found"
        
        output = f"\n📁 Namespaces in {self.current_context}:\n"
        for ns in sorted(namespaces):
            marker = "✓" if ns == self.current_namespace else "  "
            output += f"  {marker} {ns}/\n"
        output += "\n💡 Use 'cd <namespace>' to enter a namespace"
        return output

    def show_pods(self) -> str:
        """Show pods"""
        args = ['get', 'pods', '-o', 'wide']
        if self.current_namespace:
            args.extend(['-n', self.current_namespace])
        else:
            args.append('-A')
        
        return self.run_kubectl(args)

    def show_deployments(self) -> str:
        """Show deployments"""
        args = ['get', 'deployments', '-o', 'wide']
        if self.current_namespace:
            args.extend(['-n', self.current_namespace])
        else:
            args.append('-A')
        
        return self.run_kubectl(args)

    def show_services(self) -> str:
        """Show services"""
        args = ['get', 'svc', '-o', 'wide']
        if self.current_namespace:
            args.extend(['-n', self.current_namespace])
        else:
            args.append('-A')
        
        return self.run_kubectl(args)

    def show_nodes(self) -> str:
        """Show nodes"""
        return self.run_kubectl(['get', 'nodes', '-o', 'wide'])

    def show_events(self) -> str:
        """Show events"""
        args = ['get', 'events', '--sort-by=.metadata.creationTimestamp']
        if self.current_namespace:
            args.extend(['-n', self.current_namespace])
        else:
            args.append('-A')
        
        return self.run_kubectl(args)

    def describe_pod(self, pod_name: str) -> str:
        """Describe a pod"""
        args = ['describe', 'pod', pod_name]
        if self.current_namespace:
            args.extend(['-n', self.current_namespace])
        
        return self.run_kubectl(args)

    def get_logs(self, pod_name: str, follow: bool = False, tail: int = None) -> str:
        """Get pod logs with timestamps"""
        args = ['logs', pod_name, '--timestamps']
        if self.current_namespace:
            args.extend(['-n', self.current_namespace])
        if follow:
            args.append('-f')
        if tail:
            args.extend(['--tail', str(tail)])
        
        return self.run_kubectl(args)

    def exec_pod(self, pod_name: str, *cmd_args) -> str:
        """Exec into a pod"""
        if not cmd_args:
            cmd_args = ['bash']
        
        args = ['exec', '-it', pod_name]
        if self.current_namespace:
            args.extend(['-n', self.current_namespace])
        args.extend(['--', *cmd_args])
        
        try:
            subprocess.run(['kubectl'] + args)
            return ""
        except FileNotFoundError:
            return "Error: kubectl not found"

    def delete_pod(self, pod_name: str) -> str:
        """Delete a pod"""
        args = ['delete', 'pod', pod_name]
        if self.current_namespace:
            args.extend(['-n', self.current_namespace])
        
        return self.run_kubectl(args)

    def apply_manifest(self, filepath: str) -> str:
        """Apply a manifest"""
        if not os.path.exists(filepath):
            return f"Error: File '{filepath}' not found"
        
        return self.run_kubectl(['apply', '-f', filepath])

    def delete_manifest(self, filepath: str) -> str:
        """Delete a manifest"""
        if not os.path.exists(filepath):
            return f"Error: File '{filepath}' not found"
        
        return self.run_kubectl(['delete', '-f', filepath])

    def set_namespace(self, namespace: str) -> str:
        """Set current namespace"""
        namespaces = self.kube_config.get_namespaces()
        if namespace not in namespaces:
            return f"Error: Namespace '{namespace}' not found\nAvailable: {', '.join(namespaces)}"
        
        self.current_namespace = namespace
        return f"✓ Namespace set to: {namespace}"

    def set_context_cmd(self, context: str) -> str:
        """Set current context"""
        contexts = self.kube_config.get_contexts()
        if context not in contexts:
            return f"Error: Context '{context}' not found\nAvailable: {', '.join(contexts)}"
        
        if self.kube_config.set_context(context):
            self.current_context = context
            return f"✓ Context switched to: {context}"
        else:
            return "Error: Failed to switch context"

    def get_status(self) -> str:
        """Get cluster status"""
        output = "\n=== Cluster Status ===\n"
        output += f"Current Context: {self.current_context}\n"
        output += f"Current Namespace: {self.current_namespace or 'All namespaces'}\n"
        output += "\nNodes:\n"
        output += self.show_nodes()
        return output

    def show_help(self) -> str:
        """Show help"""
        help_text = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    km - Interactive Kubernetes Shell                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

📋 KOMUTLAR:
  cd <path>              - klasöre geç (cd .. = bir üst seviyeye)
  cd                     - root'a geç (tüm clusterları gör)
  ls / ls *              - mevcut seviyedeki öğeleri listele
  pwd                    - mevcut yolu göster
  tree                   - tüm klasör yapısını göster
  clear                  - ekranı temizle
  cat <file>             - dosya içeriğini göster (yaml)
  more <file>            - dosya içeriğini göster (yaml)
  
  Klasör Yapısı: /cluster/namespace/resource_type/resource_name/
    • /                 - root, tüm clusterları göster
    • /cluster-name/    - cluster seviyesi
    • /cluster/ns/      - namespace seviyesi
    • /cluster/ns/pods/ - resource type seviyesi
    • /cluster/ns/pods/pod-name/ - pod seviyesi
    • Örnek: cd /dev/kube-system/pods/my-pod
  
  show deployments       - deployment'ları göster
  show services          - service'leri göster
  show pods              - pod'ları göster
  show nodes             - node'ları göster
  show events            - event'ları göster
  show clusters          - cluster'ları listele
  show contexts          - context'leri listele
  show namespaces        - namespace'leri listele
  
  describe pod <name>    - pod detaylarını göster
  logs <pod>             - pod loglarını göster
  exec <pod> [cmd]       - pod'da komut çalıştır
  delete pod <name>      - pod'u sil
  
  apply <file>           - manifest uygula
  delete <file>          - manifest sil
  
  status                 - cluster durumunu göster
  help                   - bu yardımı göster
  exit/quit              - çık

💡 İPUÇLARI:
  • Klasör yapısı: cluster/namespace/resource_type/resource_name/
  • TAB ile otomatik tamamlama
  • Ctrl+C iki kez basarak çık
  • cd <namespace> ile namespace'e gir
  • cd <resource_type> ile resource tipine gir
  • cd <resource_name> ile resource'a gir
  • ls ile mevcut seviyeyi gör
  • cat yaml ile resource YAML'ını gör
  • cat yaml | grep <pattern> ile arama yap
  • Pod'lar için: cat log (logs), cat events (events)
  • more <file> ile interaktif pager (/, ok tuşları, q ile çık)
  • İçerikler doğrudan ekranda gösterilir, geçici dosya yazılmaz
"""
        return help_text

    def process_command(self, user_input: str) -> Optional[str]:
        """Process user command"""
        # Handle pipes
        if '|' in user_input:
            commands = [cmd.strip() for cmd in user_input.split('|')]
            if len(commands) == 2:
                left_output = self.process_command(commands[0])
                if left_output:
                    # Simple pipe: run right command with left output as input
                    return self._run_piped_command(commands[1], left_output)
                else:
                    return None
            else:
                return "Error: Only simple pipes (cmd1 | cmd2) are supported"
        
        parts = user_input.strip().split(maxsplit=1)
        if not parts:
            return None
        
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if user_input.lower().startswith('show clusters'):
            return self.show_clusters()
        elif user_input.lower().startswith('show contexts'):
            self._update_context_cache()  # Refresh context cache
            return self.show_contexts()
        elif user_input.lower().startswith('show namespaces'):
            self._update_namespace_cache()  # Refresh namespace cache
            return self.show_namespaces()
        elif user_input.lower().startswith('show pods'):
            return self.show_pods()
        elif user_input.lower().startswith('show deployments'):
            return self.show_deployments()
        elif user_input.lower().startswith('show services'):
            return self.show_services()
        elif user_input.lower().startswith('show nodes'):
            return self.show_nodes()
        elif user_input.lower().startswith('show events'):
            return self.show_events()
        elif user_input.lower().startswith('describe pod'):
            pod_name = user_input[12:].strip()
            if pod_name:
                return self.describe_pod(pod_name)
            else:
                return "Error: pod name required"
        elif user_input.lower().startswith('logs'):
            pod_name = user_input[4:].strip().split()[0] if user_input[4:].strip() else ""
            if pod_name:
                return self.get_logs(pod_name)
            else:
                return "Error: pod name required"
        elif user_input.lower().startswith('exec'):
            parts = user_input[4:].strip().split(maxsplit=1)
            if parts:
                pod_name = parts[0]
                cmd_args = parts[1].split() if len(parts) > 1 else ['bash']
                return self.exec_pod(pod_name, *cmd_args)
            else:
                return "Error: pod name required"
        elif user_input.lower().startswith('delete pod'):
            pod_name = user_input[10:].strip()
            if pod_name:
                return self.delete_pod(pod_name)
            else:
                return "Error: pod name required"
        elif user_input.lower().startswith('set namespace'):
            ns_name = user_input[13:].strip()
            if ns_name:
                return self.set_namespace(ns_name)
            else:
                return "Error: namespace name required"
        elif user_input.lower().startswith('set context'):
            ctx_name = user_input[11:].strip()
            if ctx_name:
                return self.set_context_cmd(ctx_name)
            else:
                return "Error: context name required"
        elif user_input.lower().startswith('apply'):
            filepath = user_input[5:].strip()
            if filepath:
                return self.apply_manifest(filepath)
            else:
                return "Error: file path required"
        elif user_input.lower().startswith('delete'):
            filepath = user_input[6:].strip()
            if filepath:
                return self.delete_manifest(filepath)
            else:
                return "Error: file path required"
        elif user_input.lower() == 'cd':
            # cd without arguments goes to root
            self.current_cluster = None
            self.current_namespace = None
            self.current_resource_type = None
            self.current_resource_name = None
            self._update_pod_cache()
            return "✓ Switched to root (clusters)"
        elif user_input.lower().startswith('cd '):
            target = user_input[3:].strip()
            
            # Handle path-like navigation (e.g., /dev/namespace, /dev2/kube-system)
            if '/' in target:
                path_parts = [p for p in target.split('/') if p]
                return self._navigate_path(path_parts)
            
            if target == '..':
                # Go up one level
                if self.current_resource_name:
                    # From resource to resource_type
                    self.current_resource_name = None
                    return f"✓ Switched to {self.current_resource_type}"
                elif self.current_resource_type:
                    # From resource_type to namespace
                    self.current_resource_type = None
                    return f"✓ Switched to namespace {self.current_namespace}"
                elif self.current_namespace:
                    # From namespace to cluster
                    self.current_namespace = None
                    self._update_pod_cache()
                    return f"✓ Switched to cluster {self.current_cluster}"
                elif self.current_cluster:
                    # From cluster to root
                    self.current_cluster = None
                    return "✓ Switched to root (clusters)"
                else:
                    return "Already at root level"
            elif target:
                # Navigate down one level
                if not self.current_cluster:
                    # At root, cd to cluster
                    if target in self.cached_clusters:
                        if self._set_cluster_context(target):
                            self.current_cluster = target
                            self._update_namespace_cache()
                            self._update_pod_cache()
                            self._update_deployment_cache()
                            self._update_service_cache()
                            return f"✓ Switched to cluster {target}"
                        else:
                            return f"Error: Could not switch to cluster '{target}'"
                    else:
                        return f"Error: Cluster '{target}' not found. Available: {', '.join(self.cached_clusters)}"
                elif not self.current_namespace:
                    # In cluster, cd to namespace
                    result = self.set_namespace(target)
                    if "✓" in result:
                        self._update_pod_cache()
                        self._update_deployment_cache()
                        self._update_service_cache()
                    return result
                elif not self.current_resource_type:
                    # In namespace, cd to resource_type
                    valid_types = ['deployments', 'services', 'pods', 'routes']
                    if target in valid_types:
                        self.current_resource_type = target
                        return f"✓ Switched to {target}"
                    else:
                        return f"Error: Invalid resource type '{target}'. Valid: {', '.join(valid_types)}"
                elif not self.current_resource_name:
                    # In resource_type, cd to resource_name
                    if self.current_resource_type == 'deployments':
                        resources = self.cached_deployments
                    elif self.current_resource_type == 'services':
                        resources = self.cached_services
                    elif self.current_resource_type == 'pods':
                        resources = self.cached_pods
                    elif self.current_resource_type == 'routes':
                        try:
                            result = subprocess.run(
                                ['oc', 'get', 'routes', '-n', self.current_namespace, 
                                 '-o', 'jsonpath={.items[*].metadata.name}'],
                                capture_output=True, text=True, timeout=5
                            )
                            resources = result.stdout.strip().split() if result.returncode == 0 else []
                        except:
                            resources = []
                    else:
                        resources = []
                    
                    if target in resources:
                        self.current_resource_name = target
                        return f"✓ Switched to {target}"
                    else:
                        return f"Error: Resource '{target}' not found in {self.current_resource_type}"
                else:
                    return "Cannot navigate deeper"
            else:
                # cd with empty target
                self.current_cluster = None
                self.current_namespace = None
                self.current_resource_type = None
                self.current_resource_name = None
                self._update_pod_cache()
                return "✓ Switched to root (clusters)"
        elif user_input.lower() == 'ls' or user_input.lower() == 'ls *':
            if self.current_resource_name and self.current_resource_type:
                # Show files in resource
                return self._show_resource_contents(self.current_resource_type, self.current_resource_name)
            elif self.current_resource_type:
                # Show resources in resource type
                return self._show_resource_type_contents(self.current_resource_type)
            elif self.current_namespace:
                # Show resource types in namespace
                return self._show_namespace_contents()
            elif self.current_cluster:
                # Show namespaces in cluster
                self._update_namespace_cache()  # Refresh namespace cache
                return self.show_namespaces()
            else:
                # Show clusters at root
                return self.show_clusters()
        elif user_input.lower() == 'pwd':
            path = ""
            if self.current_cluster:
                path += f"/{self.current_cluster}"
            if self.current_namespace:
                path += f"/{self.current_namespace}"
            if self.current_resource_type:
                path += f"/{self.current_resource_type}"
            if self.current_resource_name:
                path += f"/{self.current_resource_name}"
            return path if path else "/"
        elif user_input.lower() == 'tree':
            return self._show_tree()
        elif user_input.lower() == 'clear':
            print("\033[2J\033[H", end="")  # Clear screen
            return ""
        elif user_input.lower().startswith('cat '):
            filename = user_input[4:].strip()
            return self._cat_file(filename)
        elif user_input.lower().startswith('more '):
            filename = user_input[5:].strip()
            return self._more_file(filename)
        else:
            return f"Unknown command: {user_input}\nType 'help' for available commands"

    def get_prompt(self) -> str:
        """Generate prompt based on current path: /cluster/namespace/resource_type/resource_name/"""
        if self.current_resource_name and self.current_resource_type and self.current_namespace and self.current_cluster:
            return f"/{self.current_cluster}/{self.current_namespace}/{self.current_resource_type}/{self.current_resource_name}> "
        elif self.current_resource_type and self.current_namespace and self.current_cluster:
            return f"/{self.current_cluster}/{self.current_namespace}/{self.current_resource_type}> "
        elif self.current_namespace and self.current_cluster:
            return f"/{self.current_cluster}/{self.current_namespace}> "
        elif self.current_cluster:
            return f"/{self.current_cluster}> "
        else:
            return "/> "

    def run_interactive(self):
        """Run interactive shell"""
        # Custom style for prompt
        style = Style.from_dict({
            'prompt': 'bold #00ff00',
        })
        
        print("╔════════════════════════════════════════════════════════════╗")
        print("║          km - Interactive Kubernetes Shell                  ║")
        print("║         Klasör yapısı: /cluster/namespace/resource/         ║")
        print("╚════════════════════════════════════════════════════════════╝\n")
        
        session = PromptSession(style=style)
        
        while self.running:
            try:
                prompt_text = self.get_prompt()
                
                # Create completer with current data
                completer = KubectlCompleter(self.commands, self.cached_namespaces, self.cached_pods, self.cached_contexts, 
                                           self.cached_deployments, self.cached_services, 
                                           self.current_namespace, self.current_resource_type,
                                           self.cached_clusters, self.current_cluster)
                
                user_input = session.prompt(
                    prompt_text,
                    completer=completer,
                )
                
                # Reset Ctrl+C counter on successful input
                self.ctrl_c_count = 0
                
                if not user_input.strip():
                    continue
                
                output = self.process_command(user_input)
                if output:
                    print(output)
                    if not user_input.lower() in ['exit', 'quit']:
                        print()
                
            except KeyboardInterrupt:
                self.ctrl_c_count += 1
                if self.ctrl_c_count >= 2:
                    print("\n👋 Goodbye!")
                    break
                else:
                    print("\nPress Ctrl+C again to exit")
                    continue
            except EOFError:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
                self.ctrl_c_count = 0  # Reset counter on error


def main():
    if len(sys.argv) > 1:
        # Non-interactive mode - for compatibility with older usage
        print("Usage: km (interactive mode)")
        print("Type 'help' after starting for available commands")
    else:
        # Interactive mode
        manager = KubectlManager()
        manager.run_interactive()


if __name__ == '__main__':
    sys.exit(main())
