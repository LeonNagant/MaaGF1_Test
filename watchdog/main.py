"""
MaaFramework Watchdog - Main Entry Point
Independent log-based watchdog for monitoring MaaFw agent execution
"""
import os
import sys
import time
import signal
import argparse
from datetime import datetime

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Now import our modules
from config import load_watchdog_config, get_watchdog_config
from log_monitor import LogMonitor


class WatchdogService:
    """Main watchdog service"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or self._get_default_config_path()
        self.monitor: LogMonitor = None
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _get_default_config_path(self) -> str:
        """Get default config file path"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, 'watchdog.conf')
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\nReceived signal {signum}, shutting down...")
        self.shutdown()
    
    def initialize(self) -> bool:
        """Initialize watchdog service"""
        print("Initializing MaaFramework Watchdog...")
        print(f"Config file: {self.config_path}")
        
        # Load configuration
        if not load_watchdog_config(self.config_path):
            print("Failed to load configuration")
            return False
        
        config = get_watchdog_config()
        
        # Validate configuration
        if not config.rules:
            print("No watchdog rules configured")
            return False
        
        if not config.is_notification_configured():
            print("Warning: No notification platforms configured")
        
        # Create log monitor
        self.monitor = LogMonitor(config)
        
        print("Watchdog service initialized successfully")
        return True
    
    def start(self) -> bool:
        """Start watchdog service"""
        if not self.monitor:
            print("Watchdog not initialized")
            return False
        
        if self.running:
            print("Watchdog is already running")
            return False
        
        print("Starting watchdog service...")
        
        if not self.monitor.start_monitoring():
            print("Failed to start log monitoring")
            return False
        
        self.running = True
        print("Watchdog service started successfully")
        print(f"Monitoring started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Print status
        status = self.monitor.get_status()
        print(f"Status: {status}")
        
        return True
    
    def shutdown(self):
        """Shutdown watchdog service"""
        if not self.running:
            return
        
        print("Shutting down watchdog service...")
        
        if self.monitor:
            self.monitor.stop_monitoring()
        
        self.running = False
        print("Watchdog service stopped")
    
    def run(self):
        """Run watchdog service (blocking)"""
        if not self.start():
            return False
        
        try:
            # Main service loop
            while self.running:
                time.sleep(1)
                
                # Optional: Print periodic status
                # status = self.monitor.get_status()
                # print(f"[{datetime.now().strftime('%H:%M:%S')}] Active rules: {status['active_rules']}")
        
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received")
        
        finally:
            self.shutdown()
        
        return True
    
    def print_status(self):
        """Print current status"""
        if not self.monitor:
            print("Watchdog not initialized")
            return
        
        status = self.monitor.get_status()
        config = get_watchdog_config()
        
        print("=== MaaFramework Watchdog Status ===")
        print(f"Running: {status['running']}")
        print(f"Config file: {self.config_path}")
        print(f"Log source: {status['log_source']}")
        print(f"Total rules: {status['total_rules']}")
        print(f"Active rules: {status['active_rules']}")
        
        if status['active_rule_names']:
            print("Active rule names:")
            for rule_name in status['active_rule_names']:
                rule = config.get_rule(rule_name)
                if rule:
                    elapsed = (datetime.now() - rule.last_start_time).total_seconds() * 1000 if rule.last_start_time else 0
                    print(f"  - {rule_name}: {elapsed:.1f}ms elapsed")
        
        print(f"Notification available: {status['notification_available']}")
        if status['notification_available']:
            print(f"Available notifiers: {config.get_available_notifiers()}")
        
        print("=== Rule Configuration ===")
        for rule_name, rule in config.rules.items():
            print(f"  - {rule}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='MaaFramework Watchdog Service')
    parser.add_argument('--config', '-c', type=str, help='Path to configuration file')
    parser.add_argument('--status', action='store_true', help='Show status and exit')
    parser.add_argument('--daemon', '-d', action='store_true', help='Run as daemon (background)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Create service instance
    service = WatchdogService(args.config)
    
    # Initialize
    if not service.initialize():
        print("Failed to initialize watchdog service")
        sys.exit(1)
    
    # Handle status request
    if args.status:
        service.print_status()
        sys.exit(0)
    
    # Run service
    print("Starting MaaFramework Watchdog Service...")
    print("Press Ctrl+C to stop")
    
    success = service.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()