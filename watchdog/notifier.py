"""
Notification system for watchdog alerts
"""
import requests
import json
from typing import Optional
from datetime import datetime


class TelegramNotifier:
    """Telegram notification handler"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    def send_message(self, message: str) -> bool:
        """Send message via Telegram"""
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(self.api_url, data=payload, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                print(f"Telegram API error: {response.status_code}, {response.text}")
                return False
                
        except Exception as e:
            print(f"Telegram send error: {e}")
            return False


class WeChatWorkNotifier:
    """WeChat Work notification handler"""
    
    def __init__(self, webhook_key: str):
        self.webhook_key = webhook_key
        self.webhook_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={webhook_key}"
    
    def send_message(self, message: str) -> bool:
        """Send message via WeChat Work"""
        try:
            payload = {
                "msgtype": "text",
                "text": {
                    "content": message
                }
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                self.webhook_url, 
                data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), 
                headers=headers, 
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    return True
                else:
                    print(f"WeChat Work API error: {result}")
                    return False
            else:
                print(f"WeChat Work HTTP error: {response.status_code}, {response.text}")
                return False
                
        except Exception as e:
            print(f"WeChat Work send error: {e}")
            return False


class WatchdogNotifier:
    """Unified notification manager for watchdog"""
    
    def __init__(self, config):
        self.config = config
        self._telegram_notifier = None
        self._wechat_notifier = None
    
    def _get_telegram_notifier(self) -> Optional[TelegramNotifier]:
        """Get Telegram notifier instance"""
        if self._telegram_notifier is None and self.config.bot_token and self.config.chat_id:
            self._telegram_notifier = TelegramNotifier(self.config.bot_token, self.config.chat_id)
        return self._telegram_notifier
    
    def _get_wechat_notifier(self) -> Optional[WeChatWorkNotifier]:
        """Get WeChat Work notifier instance"""
        if self._wechat_notifier is None and self.config.webhook_key:
            self._wechat_notifier = WeChatWorkNotifier(self.config.webhook_key)
        return self._wechat_notifier
    
    def send_notification(self, message: str) -> bool:
        """Send notification with fallback mechanism"""
        available_platforms = self.config.get_available_notifiers()
        
        if not available_platforms:
            print("Warning: No notification platforms available")
            return False
        
        # Determine try order
        try_order = []
        default_platform = self.config.default_ext_notify
        
        if default_platform and default_platform in available_platforms:
            try_order.append(default_platform)
        
        for platform in available_platforms:
            if platform not in try_order:
                try_order.append(platform)
        
        # Try sending notification
        for platform in try_order:
            try:
                if platform == 'telegram':
                    notifier = self._get_telegram_notifier()
                    if notifier and notifier.send_message(message):
                        print(f"Watchdog notification sent via Telegram")
                        return True
                elif platform == 'wechat':
                    notifier = self._get_wechat_notifier()
                    if notifier and notifier.send_message(message):
                        print(f"Watchdog notification sent via WeChat Work")
                        return True
            except Exception as e:
                print(f"Failed to send via {platform}: {e}")
                continue
        
        print("Failed to send watchdog notification via all platforms")
        return False
    
    def send_timeout_alert(self, rule_name: str, rule, elapsed_ms: float) -> bool:
        """Send timeout alert notification"""
        message = (
            f"🚨 WATCHDOG TIMEOUT ALERT\n\n"
            f"Rule: {rule_name}\n"
            f"Description: {rule.description or 'N/A'}\n"
            f"Start Node: {rule.start_node}\n"
            f"Expected End Node: {rule.end_node}\n"
            f"Timeout Threshold: {rule.timeout_ms}ms\n"
            f"Elapsed Time: {elapsed_ms:.1f}ms\n"
            f"Last Start: {rule.last_start_time.strftime('%Y-%m-%d %H:%M:%S') if rule.last_start_time else 'Unknown'}\n"
            f"Alert Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return self.send_notification(message)
    
    def send_rule_activated(self, rule_name: str, rule) -> bool:
        """Send rule activation notification"""
        message = (
            f"✅ WATCHDOG RULE ACTIVATED\n\n"
            f"Rule: {rule_name}\n"
            f"Description: {rule.description or 'N/A'}\n"
            f"Start Node: {rule.start_node}\n"
            f"Timeout: {rule.timeout_ms}ms\n"
            f"Activation Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return self.send_notification(message)
    
    def send_rule_completed(self, rule_name: str, rule, elapsed_ms: float) -> bool:
        """Send rule completion notification"""
        message = (
            f"✅ WATCHDOG RULE COMPLETED\n\n"
            f"Rule: {rule_name}\n"
            f"End Node: {rule.end_node}\n"
            f"Elapsed Time: {elapsed_ms:.1f}ms\n"
            f"Timeout Threshold: {rule.timeout_ms}ms\n"
            f"Completion Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return self.send_notification(message)