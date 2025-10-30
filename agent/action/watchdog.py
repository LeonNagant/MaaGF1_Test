from .include import *
import threading
import time
from datetime import datetime, timedelta

# Load config.py
import sys
import os
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from utils import (get_telegram_config, is_telegram_configured, 
                   get_wechat_config, is_wechat_configured,
                   get_default_ext_notify, get_available_notifiers)

# Import notifiers and logging functions from log module
from .log import TelegramNotifier, WeChatWorkNotifier, MaaLog_Debug, MaaLog_Info

class Watchdog:
    """
    Watchdog monitoring system for agent health checking
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._is_running = False
        self._timeout_ms = 0
        self._last_feed_time = None
        self._start_info = ""
        self._telegram_notifier = None
        self._wechat_notifier = None
        
        # For logging
        self.action_name = "Watchdog"
    
    def _get_telegram_notifier(self):
        """Get Telegram notifier"""
        if self._telegram_notifier is None:
            bot_token, chat_id = get_telegram_config()
            if bot_token and chat_id:
                self._telegram_notifier = TelegramNotifier(bot_token, chat_id)
        return self._telegram_notifier
    
    def _get_wechat_notifier(self):
        """Get Enterprise WeChat notifier"""
        if self._wechat_notifier is None:
            webhook_key = get_wechat_config()
            if webhook_key:
                self._wechat_notifier = WeChatWorkNotifier(webhook_key)
        return self._wechat_notifier
    
    def _send_notification(self, message):
        """
        Send notification using available platforms with fallback
        """
        # Get default platform and available platforms
        default_platform = get_default_ext_notify()
        available_platforms = get_available_notifiers()
        
        MaaLog_Debug(f"Watchdog notification - default platform: {default_platform}, available platforms: {available_platforms}")
        
        if not available_platforms:
            MaaLog_Debug("Watchdog notification failed: no available notification platforms")
            return False
        
        # Build try order
        try_order = []
        if default_platform and default_platform in available_platforms:
            try_order.append(default_platform)
        
        # Add other available platforms as alternatives
        for platform in available_platforms:
            if platform not in try_order:
                try_order.append(platform)
        
        MaaLog_Debug(f"Watchdog notification try order: {try_order}")
        
        # Try sending in order
        for platform in try_order:
            try:
                if platform == 'telegram':
                    notifier = self._get_telegram_notifier()
                    if notifier:
                        MaaLog_Debug(f"Trying to send watchdog message via Telegram")
                        if notifier.send_message(message):
                            MaaLog_Debug(f"Watchdog notification success: sent via Telegram")
                            return True
                        else:
                            MaaLog_Debug(f"Telegram sending failed, trying next platform")
                elif platform == 'wechat':
                    notifier = self._get_wechat_notifier()
                    if notifier:
                        MaaLog_Debug(f"Trying to send watchdog message via Enterprise WeChat")
                        if notifier.send_message(message):
                            MaaLog_Debug(f"Watchdog notification success: sent via Enterprise WeChat")
                            return True
                        else:
                            MaaLog_Debug(f"Enterprise WeChat sending failed, trying next platform")
            except Exception as e:
                MaaLog_Debug(f"{platform} sending exception: {e}, trying next platform")
                continue
        
        MaaLog_Debug("Watchdog notification failed: all platforms unable to send message")
        return False
    
    def start(self, timeout_ms, string_info=""):
        """
        Start watchdog with specified timeout and info
        """
        with self._lock:
            if self._is_running:
                MaaLog_Debug("Watchdog is already running")
                return False
            
            self._timeout_ms = timeout_ms
            self._start_info = string_info
            self._last_feed_time = datetime.now()
            self._is_running = True
            
            start_message = f"[WATCHDOG] Started\nTimeout: {timeout_ms}ms\nInfo: {string_info}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            MaaLog_Info(f"Watchdog started - timeout: {timeout_ms}ms, info: {string_info}")
            
            # Send notification
            self._send_notification(start_message)
            
            return True
    
    def stop(self, string_info=""):
        """
        Stop watchdog with specified info
        """
        with self._lock:
            if not self._is_running:
                MaaLog_Debug("Watchdog is not running")
                return False
            
            self._is_running = False
            
            stop_message = f"[WATCHDOG] Stopped\nInfo: {string_info}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            MaaLog_Info(f"Watchdog stopped - info: {string_info}")
            
            # Send notification
            self._send_notification(stop_message)
            
            return True
    
    def feed(self):
        """
        Feed the watchdog (reset timeout)
        """
        with self._lock:
            if not self._is_running:
                MaaLog_Debug("Cannot feed watchdog: not running")
                return False
            
            self._last_feed_time = datetime.now()
            MaaLog_Debug(f"Watchdog fed at {self._last_feed_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            return True
    
    def poll(self):
        """
        Check if watchdog has timed out
        Returns True if timeout occurred, False if still healthy
        """
        with self._lock:
            if not self._is_running:
                return False
            
            if self._last_feed_time is None:
                return True
            
            elapsed_ms = (datetime.now() - self._last_feed_time).total_seconds() * 1000
            is_timeout = elapsed_ms > self._timeout_ms
            
            MaaLog_Debug(f"Watchdog poll - elapsed: {elapsed_ms:.1f}ms, timeout: {self._timeout_ms}ms, is_timeout: {is_timeout}")
            
            return is_timeout
    
    def notify(self):
        """
        Send timeout notification
        """
        with self._lock:
            if not self._is_running:
                return False
            
            elapsed_ms = (datetime.now() - self._last_feed_time).total_seconds() * 1000 if self._last_feed_time else float('inf')
            
            timeout_message = f"[WATCHDOG] Watchdog Timeout Alert!\nStart Info: {self._start_info}\nTimeout Threshold: {self._timeout_ms}ms\nElapsed Time: {elapsed_ms:.1f}ms\nLast Feed: {self._last_feed_time.strftime('%Y-%m-%d %H:%M:%S') if self._last_feed_time else 'Never'}\nAlert Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            MaaLog_Info(f"Watchdog timeout alert - elapsed: {elapsed_ms:.1f}ms, threshold: {self._timeout_ms}ms")
            
            # Send notification
            return self._send_notification(timeout_message)
    
    @property
    def is_running(self):
        """Check if watchdog is running"""
        with self._lock:
            return self._is_running

# Global watchdog instance
_global_watchdog = Watchdog()

def get_global_watchdog():
    """Get global watchdog instance"""
    return _global_watchdog

@AgentServer.custom_action("watchdog_start")
class WatchdogStartAction(CustomAction):
    """
    Start watchdog action
    """
    
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        try:
            param = argv.custom_action_param
            MaaLog_Debug(f"WatchdogStartAction param: {param} (type: {type(param)})")
            
            # Parse parameters
            if isinstance(param, str):
                try:
                    param = json.loads(param)
                except json.JSONDecodeError:
                    MaaLog_Debug("Failed to parse param as JSON, treating as string")
                    return CustomAction.RunResult(success=False)
            
            if not isinstance(param, dict):
                MaaLog_Debug("Invalid param format, expected dict")
                return CustomAction.RunResult(success=False)
            
            timeout_ms = param.get('timeout_ms', 30000)  # Default 30 seconds
            string_info = param.get('info', '')
            
            watchdog = get_global_watchdog()
            success = watchdog.start(timeout_ms, string_info)
            
            return CustomAction.RunResult(success=success)
            
        except Exception as e:
            MaaLog_Debug(f"WatchdogStartAction exception: {e}")
            import traceback
            MaaLog_Debug(f"Exception stack: {traceback.format_exc()}")
            return CustomAction.RunResult(success=False)

@AgentServer.custom_action("watchdog_stop")
class WatchdogStopAction(CustomAction):
    """
    Stop watchdog action
    """
    
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        try:
            param = argv.custom_action_param
            MaaLog_Debug(f"WatchdogStopAction param: {param} (type: {type(param)})")
            
            # Parse parameters
            if isinstance(param, str):
                try:
                    param = json.loads(param)
                except json.JSONDecodeError:
                    # If not JSON, treat as simple string info
                    string_info = param
                else:
                    string_info = param.get('info', '') if isinstance(param, dict) else ''
            elif isinstance(param, dict):
                string_info = param.get('info', '')
            else:
                string_info = ''
            
            watchdog = get_global_watchdog()
            success = watchdog.stop(string_info)
            
            return CustomAction.RunResult(success=success)
            
        except Exception as e:
            MaaLog_Debug(f"WatchdogStopAction exception: {e}")
            import traceback
            MaaLog_Debug(f"Exception stack: {traceback.format_exc()}")
            return CustomAction.RunResult(success=False)

@AgentServer.custom_action("watchdog_feed")
class WatchdogFeedAction(CustomAction):
    """
    Feed watchdog action
    """
    
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        try:
            watchdog = get_global_watchdog()
            success = watchdog.feed()
            
            return CustomAction.RunResult(success=success)
            
        except Exception as e:
            MaaLog_Debug(f"WatchdogFeedAction exception: {e}")
            import traceback
            MaaLog_Debug(f"Exception stack: {traceback.format_exc()}")
            return CustomAction.RunResult(success=False)