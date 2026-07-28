"""
Gunicorn production config.

Run with:  gunicorn -c gunicorn.conf.py Tuhame.wsgi:application

Everything here is overridable via environment variables so you can tune
it per-server without editing code (e.g. on a small droplet vs a bigger
box). The defaults are sane for a small-to-medium VPS.
"""
import multiprocessing
import os

# ── Bind ──
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")

# ── Workers & threads ──
# Threaded workers so each worker process can handle several requests
# concurrently while one is waiting on I/O (DB query, image processing,
# an external API call) instead of one request blocking the whole worker.
# Formula: (2 x CPU cores) + 1 is the standard Gunicorn recommendation -
# balances throughput against per-worker memory usage.
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
threads = int(os.environ.get("GUNICORN_THREADS", 4))
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "gthread")

# ── Load balancing across workers ──
# Loading the app once before forking workers (instead of once per worker)
# cuts memory usage and start-up time significantly, and lets the OS load
# balance incoming connections across workers more evenly since they all
# start from the same warmed-up state.
preload_app = True

# Recycle each worker after N requests (with jitter so they don't all
# recycle at once) - guards against slow memory growth over a long
# uptime instead of ever needing a manual restart.
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", 1000))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", 100))

# ── Timeouts ──
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 30))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", 30))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", 5))

# Use shared memory for the heartbeat/temp files if available - avoids
# slow disk I/O on some hosts for something that happens constantly.
_shm = "/dev/shm"
if os.path.isdir(_shm) and os.access(_shm, os.W_OK):
    worker_tmp_dir = _shm

# ── Logging ──
accesslog = os.environ.get("GUNICORN_ACCESS_LOG", "-")  # stdout
errorlog = os.environ.get("GUNICORN_ERROR_LOG", "-")    # stderr
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
