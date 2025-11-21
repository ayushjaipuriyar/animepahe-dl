# Performance Benchmarks

This directory contains benchmark scripts to measure and optimize download performance.

## Available Benchmarks

### benchmark_download.py

Comprehensive benchmark suite testing:
- Thread count optimization
- Quality settings impact
- Concurrent download performance
- Download statistics tracking

**Usage:**
```bash
python benchmarks/benchmark_download.py
```

## Benchmark Results

### Thread Count Performance

Optimal thread count varies by:
- Network bandwidth
- CPU cores
- Disk I/O speed
- Server rate limits

**Typical Results:**
- 10 threads: Good for slow connections
- 50 threads: Balanced for most users
- 100 threads: Best for fast connections

### Quality Impact

Download time by quality:
- 360p: ~1x baseline
- 720p: ~2.5x baseline
- 1080p: ~4x baseline

### Concurrent Downloads

Downloading multiple episodes simultaneously:
- 1 episode: Baseline
- 2 episodes: ~1.8x faster total
- 3 episodes: ~2.5x faster total
- 4+ episodes: Diminishing returns

## Running Custom Benchmarks

### Test Specific Thread Count

```python
from anime_downloader.performance import benchmark

def download_test():
    # Your download code here
    pass

results = benchmark(download_test, iterations=10)
print(f"Average time: {results['avg_time']:.3f}s")
```

### Track Download Stats

```python
from anime_downloader.performance import DownloadStats

stats = DownloadStats()

# During download
stats.add_segment(bytes_downloaded=1024*1024, success=True)

# Get summary
summary = stats.summary()
print(f"Speed: {summary['download_speed_mbps']:.2f} MB/s")
```

### Measure Execution Time

```python
from anime_downloader.performance import Timer

with Timer("My Operation", auto_log=True) as timer:
    # Code to measure
    pass

print(f"Elapsed: {timer.elapsed:.3f}s")
```

## Optimization Tips

### Network Optimization

1. **Increase thread count** for faster connections:
   ```bash
   animepahe-dl -n "Anime" -t 100
   ```

2. **Use concurrent downloads**:
   ```bash
   animepahe-dl -n "Anime" -c 3
   ```

3. **Lower quality** for faster downloads:
   ```bash
   animepahe-dl -n "Anime" -q 720
   ```

### System Optimization

1. **Use SSD storage** for better I/O
2. **Close bandwidth-heavy applications**
3. **Use wired connection** instead of WiFi
4. **Disable VPN** if not needed

### Application Optimization

1. **Enable caching** to reduce API calls
2. **Use async downloader** for better concurrency
3. **Batch downloads** during off-peak hours
4. **Monitor system resources** (CPU, RAM, disk)

## Profiling

### CPU Profiling

```bash
python -m cProfile -o profile.stats -m anime_downloader.main -n "Anime"
python -m pstats profile.stats
```

### Memory Profiling

```bash
pip install memory_profiler
python -m memory_profiler anime_downloader/main.py
```

### Network Profiling

Monitor network usage:
```bash
# Linux
iftop

# macOS
nettop

# Windows
Resource Monitor
```

## Contributing Benchmarks

To add new benchmarks:

1. Create a new script in `benchmarks/`
2. Use the performance utilities from `anime_downloader.performance`
3. Document the benchmark purpose and usage
4. Include sample results
5. Submit a pull request

## Interpreting Results

### Good Performance Indicators

- Download speed > 5 MB/s
- Success rate > 95%
- CPU usage < 50%
- Memory usage stable

### Performance Issues

- Download speed < 1 MB/s: Check network
- Success rate < 90%: Check server/network
- High CPU usage: Reduce thread count
- High memory usage: Reduce concurrent downloads

## Automated Benchmarking

Run benchmarks in CI/CD:

```yaml
- name: Run Benchmarks
  run: |
    python benchmarks/benchmark_download.py
    # Compare with baseline
```

## Resources

- [Python Performance Tips](https://wiki.python.org/moin/PythonSpeed/PerformanceTips)
- [Profiling Python Code](https://docs.python.org/3/library/profile.html)
- [Async Programming Guide](https://docs.python.org/3/library/asyncio.html)
