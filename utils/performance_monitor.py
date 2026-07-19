"""
Performance Monitoring and Optimization Utilities for PDF Processing

This module provides tools to monitor and optimize PDF processing performance.
"""

import time
import psutil
import logging
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class PDFProcessingProfiler:
    """Performance profiler for PDF processing operations.

    The profiler can be used as a context manager for the whole profiling
    session (``with PDFProcessingProfiler() as profiler: ...``) and also
    provides a ``profile_phase`` context manager to measure individual
    stages of the PDF pipeline. A simple ``@profile`` decorator is also
    supplied for quick function-level instrumentation.
    """
    
    def __init__(self):
        self.start_time: Optional[float] = None
        self.metrics: Dict[str, Any] = {}
        self._process = psutil.Process()
        
    # ---------------------------------------------------------------------
    # Context manager support for the entire profiler instance
    # ---------------------------------------------------------------------
    def __enter__(self):
        """Enter profiling context – automatically starts profiling."""
        self.start_profiling()
        return self
    
    def __exit__(self, exc_type, exc, tb):
        """Exit profiling context – records final metrics and logs them."""
        self.stop_profiling()
        # Log summary (debug level – can be configured by the app)
        logger.debug("Profiling summary: %s", self.metrics)
        # Do not suppress exceptions
        return False
    
    # ---------------------------------------------------------------------
    # Core profiling methods
    # ---------------------------------------------------------------------
    def start_profiling(self) -> None:
        """Start performance profiling for the whole operation."""
        self.start_time = time.time()
        self.metrics = {
            "start_memory": self._process.memory_info().rss / 1024 / 1024,  # MB
            "start_cpu": psutil.cpu_percent(),
            "phases": {}
        }
        logger.info("🔍 Started performance profiling")
    
    def stop_profiling(self) -> None:
        """Finalize profiling – capture total elapsed time and resources."""
        if self.start_time is None:
            logger.warning("stop_profiling called without start_profiling")
            return
        total_time = time.time() - self.start_time
        self.metrics.update({
            "total_time_sec": total_time,
            "end_memory": self._process.memory_info().rss / 1024 / 1024,
            "end_cpu": psutil.cpu_percent()
        })
    
    # ---------------------------------------------------------------------
    # Phase-level profiling (context manager)
    # ---------------------------------------------------------------------
    @contextmanager
    def profile_phase(self, name: str):
        """Record timing and memory/CPU usage for a named phase."""
        start = time.time()
        start_mem = self._process.memory_info().rss / 1024 / 1024
        start_cpu = psutil.cpu_percent()
        yield  # execute the wrapped block
        end = time.time()
        end_mem = self._process.memory_info().rss / 1024 / 1024
        end_cpu = psutil.cpu_percent()
        self.metrics["phases"][name] = {
            "elapsed_sec": end - start,
            "memory_mb": end_mem - start_mem,
            "cpu_percent": end_cpu - start_cpu,
        }
        
    def log_phase(self, phase_name: str, additional_info: Optional[Dict[str, Any]] = None):
        """Log a processing phase with timing and resource usage."""
        if not self.start_time:
            logger.warning("Profiling not started")
            return
            
        current_time = time.time()
        current_memory = self._process.memory_info().rss / 1024 / 1024  # MB
        
        phase_data = {
            "elapsed_time": current_time - self.start_time,
            "memory_usage": current_memory,
            "memory_delta": current_memory - self.metrics["start_memory"]
        }
        
        if additional_info:
            phase_data.update(additional_info)
            
        self.metrics["phases"][phase_name] = phase_data
        
        logger.info(f"📊 Phase '{phase_name}': {phase_data['elapsed_time']:.1f}s, "
                    f"Memory: {current_memory:.1f}MB (+{phase_data['memory_delta']:.1f}MB)")
        
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of performance metrics."""
        if not self.start_time:
            return {}
            
        total_time = time.time() - self.start_time
        final_memory = self._process.memory_info().rss / 1024 / 1024
        
        return {
            "total_time": total_time,
            "memory_peak": final_memory,
            "memory_increase": final_memory - self.metrics["start_memory"],
            "phases": self.metrics["phases"],
            "efficiency_score": self._calculate_efficiency_score()
        }
        
    def _calculate_efficiency_score(self) -> float:
        """Calculate an efficiency score based on time and memory usage."""
        total_time = time.time() - self.start_time if self.start_time else 0
        memory_usage = self._process.memory_info().rss / 1024 / 1024
        
        # Normalize and combine metrics (0-100 scale)
        time_score = max(0, 100 - (total_time * 2))  # Penalty for long processing
        memory_score = max(0, 100 - (memory_usage / 10))  # Penalty for high memory usage
        
        return (time_score + memory_score) / 2

# ---------------------------------------------------------------------
# Convenience decorator using a shared profiler instance
# ---------------------------------------------------------------------
def profile(func):
    """Decorator that profiles a function using a temporary ``PDFProcessingProfiler``."""
    def wrapper(*args, **kwargs):
        with PDFProcessingProfiler() as prof:
            result = func(*args, **kwargs)
        logger.debug("Function %s profiling data: %s", func.__name__, prof.metrics)
        return result
    return wrapper

@contextmanager
def performance_monitor(operation_name: str):
    """Context manager for monitoring performance of operations."""
    profiler = PDFProcessingProfiler()
    profiler.start_profiling()
    
    try:
        yield profiler
    finally:
        summary = profiler.get_summary()
        logger.info(f"🏁 Operation '{operation_name}' completed in {summary.get('total_time', 0):.1f}s")
        logger.info(f"📈 Memory usage: {summary.get('memory_peak', 0):.1f}MB "
                    f"(+{summary.get('memory_increase', 0):.1f}MB)")
        logger.info(f"⭐ Efficiency score: {summary.get('efficiency_score', 0):.1f}/100")

def optimize_chunk_size(text_length: int, target_chunks: int = 50) -> int:
    """Calculate optimal chunk size based on text length and target number of chunks."""
    if text_length < 1000:
        return 500  # Small documents
    elif text_length < 10000:
        return 1000  # Medium documents
    else:
        # Large documents - calculate based on target chunks
        optimal_size = text_length // target_chunks
        return min(max(optimal_size, 800), 2000)  # Clamp between 800-2000

def estimate_processing_time(file_size_mb: float, num_pages: int) -> float:
    """Estimate processing time based on file size and page count."""
    base_time = 2.0  # Base processing time in seconds
    size_factor = file_size_mb * 0.5  # 0.5 seconds per MB
    page_factor = num_pages * 0.1  # 0.1 seconds per page
    embedding_factor = (num_pages * 2)  # Embedding generation time
    
    return base_time + size_factor + page_factor + embedding_factor

def check_system_resources() -> Dict[str, Any]:
    """Check available system resources."""
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "available_memory_gb": psutil.virtual_memory().available / 1024 / 1024 / 1024,
        "disk_space_gb": psutil.disk_usage('/').free / 1024 / 1024 / 1024,
        "recommendations": _get_performance_recommendations()
    }

def _get_performance_recommendations() -> List[str]:
    """Get performance recommendations based on current system state."""
    recommendations = []
    
    memory = psutil.virtual_memory()
    if memory.percent > 85:
        recommendations.append("High memory usage detected. Consider processing smaller PDFs or restarting the service.")
    
    cpu = psutil.cpu_percent(interval=1)
    if cpu > 90:
        recommendations.append("High CPU usage detected. Consider reducing parallel processing.")
    
    if len(recommendations) == 0:
        recommendations.append("System resources are optimal for PDF processing.")
    
    return recommendations
