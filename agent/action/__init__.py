"""
Action package initialization
Provides unified access to all action module functionalities
"""

# Import all submodules first to ensure they're loaded
from . import include
from . import input
from . import watchdog
from . import borderless

# Import global variables and configuration from include
from .include import (
    Task_Counter,
    Enable_MaaLog_Debug,
    Enable_MaaLog_Info
)

# Import log module after include to ensure globals are available
from . import log

# Import commonly used functions and classes for convenient access
from .log import MaaLog_Debug, MaaLog_Info

from .input import (
    win32_mouse_left_down, 
    win32_mouse_left_up, 
    find_game_window, 
    convert_maa_coordinates
)

# Import watchdog functions
from .watchdog import get_global_watchdog

# Import borderless functions
from .borderless import get_global_optimizer

# Define what gets exported when using "from action import *"
__all__ = [
    # Submodules
    'include',
    'log', 
    'input',
    'watchdog',
    'borderless',
    
    # Logging functions
    'MaaLog_Debug',
    'MaaLog_Info',
    
    # Input functions
    'win32_mouse_left_down',
    'win32_mouse_left_up', 
    'find_game_window',
    'convert_maa_coordinates',
    
    # Watchdog functions
    'get_global_watchdog',
    
    # Borderless functions
    'get_global_optimizer',
    
    # Global variables
    'Task_Counter',
    'Enable_MaaLog_Debug',
    'Enable_MaaLog_Info'
]

# Package metadata
__version__ = '1.0.0'
__author__ = 'MaaGF1 Team'
__description__ = 'Action module for MaaFramework agent'