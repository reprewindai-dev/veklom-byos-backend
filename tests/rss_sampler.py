import psutil
import time
import statistics
import sys

def sample_memory(duration_seconds=30, interval_seconds=0.5):
    print(f"Sampling process memory for {duration_seconds}s at {interval_seconds}s interval...")
    p = psutil.Process()
    samples = []
    t_end = time.time() + duration_seconds
    while time.time() < t_end:
        samples.append(p.memory_info().rss)
        time.sleep(interval_seconds)
        
    p95 = sorted(samples)[int(0.95 * len(samples)) - 1]
    p95_mb = p95 / (1024 * 1024)
    print(f"RSS Memory Statistics:")
    print(f"  Max: {max(samples)/(1024*1024):.2f} MB")
    print(f"  Min: {min(samples)/(1024*1024):.2f} MB")
    print(f"  p95: {p95_mb:.2f} MB")
    
    # Assert limit is < 600 MB
    limit_mb = 600.0
    if p95_mb > limit_mb:
        print(f"❌ MEMORY GATE BREACHED: p95 RSS {p95_mb:.2f} MB > {limit_mb} MB")
        sys.exit(1)
        
    print("✓ Memory stability checks passed.")

if __name__ == "__main__":
    sample_memory()
