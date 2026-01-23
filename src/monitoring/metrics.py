from prometheus_client import Gauge, Counter

# Resource Metrics
CPU_USAGE = Gauge("job_intel_cpu_percent", "Current system CPU usage percentage")

MEMORY_USAGE = Gauge(
    "job_intel_memory_percent", "Current system memory usage percentage"
)

DISK_FREE = Gauge(
    "job_intel_disk_free_percent", "Current system disk free space percentage"
)

# Application Metrics
THROTTLE_EVENTS = Counter(
    "job_intel_throttle_events_total",
    "Total number of times the system has entered throttled state",
)

JOB_SCRAPED_TOTAL = Counter(
    "job_intel_jobs_scraped_total", "Total number of jobs scraped", ["source", "status"]
)

JOB_PROCESSING_SECONDS = Gauge(
    "job_intel_processing_seconds", "Time spent processing jobs", ["source"]
)
