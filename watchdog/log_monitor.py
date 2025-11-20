"""
Log monitoring system for MaaFramework watchdog
"""
import re
import time
import threading
import subprocess
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, TextIO

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from config import WatchdogConfig, WatchdogRule
from notifier import WatchdogNotifier


class LogMonitor:
    """Log monitor for watching MaaFramework execution"""
    
    def __init__(self, config: WatchdogConfig):
        self.config = config
        self.notifier = WatchdogNotifier(config)
        
        # Monitoring state
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Log patterns for node detection
        self.node_patterns = {
            'start': re.compile(r'\[.*?\]\[.*?\]\[.*?\] \[node_name=(.*?)\].*start', re.IGNORECASE),
            'complete': re.compile(r'\[.*?\]\[.*?\] \[node_name=(.*?)\].*complete', re.IGNORECASE),
            'general': re.compile(r'\[.*?\] \[node_name=(.*?)\]', re.IGNORECASE)
        }
        
        # File monitoring
        self.log_file: Optional[TextIO] = None
        self.log_file_position = 0
    
    def start_monitoring(self) -> bool:
        """Start log monitoring"""
        if self.is_running:
            print("Log monitor is already running")
            return False
        
        if not self._prepare_log_source():
            print("Failed to prepare log source")
            return False
        
        self.stop_event.clear()
        self.is_running = True
        
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="WatchdogLogMonitor"
        )
        self.monitor_thread.start()
        
        print("Watchdog log monitor started")
        return True
    
    def stop_monitoring(self) -> bool:
        """Stop log monitoring"""
        if not self.is_running:
            return False
        
        self.stop_event.set()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
            if self.monitor_thread.is_alive():
                print("Warning: Monitor thread did not stop gracefully")
        
        self._cleanup_log_source()
        self.is_running = False
        
        print("Watchdog log monitor stopped")
        return True
    
    def _prepare_log_source(self) -> bool:
        """Prepare log source for monitoring"""
        if self.config.log_file_path:
            # File-based monitoring
            try:
                if os.path.exists(self.config.log_file_path):
                    self.log_file = open(self.config.log_file_path, 'r', encoding='utf-8')
                    # Move to end of file to only read new content
                    self.log_file.seek(0, os.SEEK_END)
                    self.log_file_position = self.log_file.tell()
                    print(f"Monitoring log file: {self.config.log_file_path}")
                    return True
                else:
                    print(f"Log file does not exist: {self.config.log_file_path}")
                    return False
            except Exception as e:
                print(f"Failed to open log file: {e}")
                return False
        
        elif self.config.enable_stdout_capture:
            # stdout capture monitoring (for future implementation)
            print("Stdout capture monitoring not yet implemented")
            return False
        
        else:
            print("No log source configured")
            return False
    
    def _cleanup_log_source(self):
        """Cleanup log source"""
        if self.log_file:
            try:
                self.log_file.close()
            except:
                pass
            self.log_file = None
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        print("Starting watchdog monitor loop...")
        
        while not self.stop_event.wait(self.config.monitor_interval):
            try:
                new_lines = self._read_new_log_lines()
                
                if new_lines:
                    for line in new_lines:
                        self._process_log_line(line.strip())
                
                # Check for timeouts
                self._check_timeouts()
                
            except Exception as e:
                print(f"Monitor loop error: {e}")
                import traceback
                traceback.print_exc()
        
        print("Monitor loop ended")
    
    def _read_new_log_lines(self) -> List[str]:
        """Read new lines from log source"""
        if not self.log_file:
            return []
        
        try:
            # Check if file has new content
            current_position = self.log_file.tell()
            self.log_file.seek(0, os.SEEK_END)
            end_position = self.log_file.tell()
            
            if end_position <= current_position:
                # No new content
                return []
            
            # Read new content
            self.log_file.seek(current_position)
            new_content = self.log_file.read()
            
            if new_content:
                lines = new_content.split('\n')
                # Last line might be incomplete, put it back
                if not new_content.endswith('\n') and len(lines) > 1:
                    incomplete_line = lines[-1]
                    lines = lines[:-1]
                    self.log_file.seek(self.log_file.tell() - len(incomplete_line))
                
                return [line for line in lines if line.strip()]
            
        except Exception as e:
            print(f"Error reading log file: {e}")
        
        return []
    
    def _process_log_line(self, line: str):
        """Process a single log line"""
        if not line:
            return
        
        # Try to extract node name from various patterns
        node_name = None
        
        for pattern_name, pattern in self.node_patterns.items():
            match = pattern.search(line)
            if match:
                node_name = match.group(1)
                break
        
        if not node_name:
            return
        
        print(f"[DEBUG] Detected node: {node_name}")
        
        # Check if this node triggers any watchdog rules
        self._check_node_event(node_name, line)
    
    def _check_node_event(self, node_name: str, log_line: str):
        """Check if node event triggers any watchdog rules"""
        current_time = datetime.now()
        
        for rule_name, rule in self.config.rules.items():
            
            # For same start_node and end_node rules (like yours)
            if rule.start_node == rule.end_node and node_name == rule.start_node:
                if rule.is_active:
                    # Reset the timer - we heard from the node again
                    print(f"[WATCHDOG] Rule '{rule_name}' timer reset by node '{node_name}'")
                    rule.last_start_time = current_time
                else:
                    # Start the watchdog timer
                    print(f"[WATCHDOG] Rule '{rule_name}' timer started by node '{node_name}'")
                    rule.is_active = True
                    rule.last_start_time = current_time
            
            # For different start_node and end_node rules (traditional watchdog)
            elif rule.start_node != rule.end_node:
                
                # Check if this node starts a watchdog rule
                if node_name == rule.start_node and not rule.is_active:
                    print(f"[WATCHDOG] Rule '{rule_name}' activated by node '{node_name}'")
                    rule.is_active = True
                    rule.last_start_time = current_time
                    
                    # Send activation notification only for different start/end nodes
                    self.notifier.send_rule_activated(rule_name, rule)
                
                # Check if this node completes a watchdog rule
                elif node_name == rule.end_node and rule.is_active:
                    elapsed_ms = (current_time - rule.last_start_time).total_seconds() * 1000
                    print(f"[WATCHDOG] Rule '{rule_name}' completed by node '{node_name}' in {elapsed_ms:.1f}ms")
                    
                    # Send completion notification only for different start/end nodes
                    self.notifier.send_rule_completed(rule_name, rule, elapsed_ms)
                    
                    # Reset rule state
                    rule.is_active = False
                    rule.last_start_time = None
    
    def _check_timeouts(self):
        """Check for timeout conditions"""
        current_time = datetime.now()
        
        for rule_name, rule in self.config.rules.items():
            if not rule.is_active or rule.last_start_time is None:
                continue
            
            elapsed_ms = (current_time - rule.last_start_time).total_seconds() * 1000
            
            if elapsed_ms > rule.timeout_ms:
                print(f"[WATCHDOG] TIMEOUT: Rule '{rule_name}' exceeded {rule.timeout_ms}ms (elapsed: {elapsed_ms:.1f}ms)")
                
                # Send timeout alert (this is the only notification for same start/end node rules)
                self.notifier.send_timeout_alert(rule_name, rule, elapsed_ms)
                
                # Reset rule state
                rule.is_active = False
                rule.last_start_time = None
    
    def get_status(self) -> Dict:
        """Get monitoring status"""
        active_rules = [name for name, rule in self.config.rules.items() if rule.is_active]
        
        return {
            'running': self.is_running,
            'total_rules': len(self.config.rules),
            'active_rules': len(active_rules),
            'active_rule_names': active_rules,
            'log_source': self.config.log_file_path or 'stdout capture',
            'notification_available': self.config.is_notification_configured()
        }