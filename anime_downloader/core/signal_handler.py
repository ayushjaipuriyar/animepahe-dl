"""
Signal handling utilities for graceful shutdown.
"""

import signal
import sys
import threading
from typing import Callable, Optional
from ..utils.logger import logger


class SignalHandler:
    """Handles system signals for graceful shutdown."""
    
    def __init__(self):
        self.shutdown_callbacks = []
        self.is_shutting_down = False
        self._original_handlers = {}
        self._lock = threading.Lock()
    
    def register_shutdown_callback(self, callback: Callable[[], None]):
        """Register a callback to be called on shutdown."""
        with self._lock:
            self.shutdown_callbacks.append(callback)
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        # Handle SIGINT (Ctrl+C) and SIGTERM
        for sig in [signal.SIGINT, signal.SIGTERM]:
            self._original_handlers[sig] = signal.signal(sig, self._signal_handler)
        
        # On Windows, also handle SIGBREAK (Ctrl+Break)
        if hasattr(signal, 'SIGBREAK'):
            self._original_handlers[signal.SIGBREAK] = signal.signal(
                signal.SIGBREAK, self._signal_handler
            )
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        with self._lock:
            if self.is_shutting_down:
                # Force exit if already shutting down
                logger.warning("Force shutdown requested")
                sys.exit(1)
            
            self.is_shutting_down = True
        
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name}, initiating graceful shutdown...")
        
        # Call shutdown callbacks
        for callback in self.shutdown_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in shutdown callback: {e}")
        
        logger.info("Graceful shutdown complete")
        sys.exit(0)
    
    def restore_signal_handlers(self):
        """Restore original signal handlers."""
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)
        self._original_handlers.clear()
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self.is_shutting_down


# Global signal handler instance
_signal_handler: Optional[SignalHandler] = None


def get_signal_handler() -> SignalHandler:
    """Get the global signal handler instance."""
    global _signal_handler
    if _signal_handler is None:
        _signal_handler = SignalHandler()
    return _signal_handler


def setup_signal_handling():
    """Setup global signal handling."""
    handler = get_signal_handler()
    handler.setup_signal_handlers()
    return handler


def register_shutdown_callback(callback: Callable[[], None]):
    """Register a shutdown callback."""
    get_signal_handler().register_shutdown_callback(callback)


def is_shutdown_requested() -> bool:
    """Check if shutdown has been requested."""
    return get_signal_handler().is_shutdown_requested()