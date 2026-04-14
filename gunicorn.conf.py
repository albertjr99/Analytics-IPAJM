# Gunicorn configuration — optimised for Render free tier (512 MB RAM)
# Start command: gunicorn -c gunicorn.conf.py app:server

workers = 1          # 1 worker avoids loading parquet data N times in memory
preload_app = True   # load app before forking — enables OS copy-on-write
bind = "0.0.0.0:10000"
timeout = 120
