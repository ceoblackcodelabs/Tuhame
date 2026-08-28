# Deploying to production (cPanel / Passenger)

## What changed and why

- **`.env` now controls everything that differs between local and
  production** — database engine, debug mode, allowed hosts, email.
  `Tuhame/settings.py` itself no longer needs to be hand-edited or have
  blocks commented/uncommented before an upload. That manual step was the
  main suspect for the "works locally, breaks in production" 500s.
- **Gunicorn removed.** On cPanel/Passenger, Passenger starts and manages
  the Python process itself via `passenger_wsgi.py` — running gunicorn
  *as well* was redundant and a likely source of the occasional/odd
  behaviour. `passenger_wsgi.py` is now the only entry point.
- **MySQL driver added.** `mysqlclient` was never in `requirements.txt`,
  so if production was ever actually running on MySQL without it manually
  installed some other way, every DB call would fail. Added `PyMySQL`
  instead (pure Python — installs cleanly on shared hosting where
  `mysqlclient`'s C build usually can't compile).
- **Media files now actually serve in production.** The old urls.py used
  Django's `static()` helper for `/media/`, which silently does nothing
  when `DEBUG=False`. That's why profile pictures/property photos
  uploaded fine but never displayed on the live site.

## Every time you upload to production

1. Make sure production's `.env` (not committed — see `.env.example`)
   has:
   ```
   DEBUG=False
   DB_ENGINE=mysql
   DB_NAME=...
   DB_USER=...
   DB_PASSWORD=...
   DB_HOST=localhost
   ALLOWED_HOSTS=yourdomain.co.ke,www.yourdomain.co.ke
   CSRF_TRUSTED_ORIGINS=https://yourdomain.co.ke,https://www.yourdomain.co.ke
   ```
2. Set the email vars (used for signup verification + password reset —
   see `Tuhame/emails.py`):
   ```
   EMAIL_HOST_USER=...
   EMAIL_HOST_PASSWORD=...
   DEFAULT_FROM_EMAIL=2Hame <no-reply@yourdomain.co.ke>
   SITE_NAME=2Hame
   ```
3. Set the M-Pesa Daraja vars (used only for subscription payments — see
   `subscriptions/mpesa.py`). SITE_URL above is reused to build the
   callback URL, so there's no separate MPESA_CALLBACK_URL to set:
   ```
   CONSUMER_KEY=...
   CONSUMER_SECRET=...
   PASSKEY=...
   BUSINESS_SHORT_CODE=...
   TILL_NUMBER=...
   MPESA_ENVIRONMENT=production
   ```
4. Install `ffmpeg` on the server if it isn't already there — it's what
   compresses hero videos on upload (see `Tuhame/video_utils.py`). If it's
   missing, uploads still work, just uncompressed (a warning is logged,
   nothing breaks). On a cPanel box without root, check with your host
   whether `ffmpeg` can be added, or ask them to install it — there's no
   pure-Python fallback for this.
   ```
   which ffmpeg   # confirms it's on PATH
   ```
5. Upload the code (passenger_wsgi.py at the app root, same as now).
6. In the cPanel Python App terminal:
   ```
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```
7. Restart the app (cPanel "Restart" button, or `touch tmp/restart.txt`
   if your setup uses that convention).

That's it — no settings.py edits, no gunicorn to think about.

## Local development

`.env` locally just needs `DEBUG=True` and `DB_ENGINE` left unset (it
defaults to SQLite). Everything else in `.env.example` is optional for
local work.

## Concurrency ("load balancing") on shared hosting

There's no nginx/HAProxy layer in front of the app on cPanel — Passenger
itself is what spreads requests across multiple worker processes. That's
the lever you actually have here, not a separate load balancer:

- cPanel's "Setup Python App" screen (or its generated `.htaccess`) sets
  `PassengerMinInstances` / a max pool size for the app. Increasing the
  min instances is what lets the app handle more than one request at a
  time under load, instead of queuing behind a single process.
- **Set `REDIS_URL` once you run more than one instance.** Without it,
  caching (`CACHES` in `settings.py`) falls back to an in-memory cache
  that's local to each process — so with 2+ instances, a session or
  cached value written by one worker won't be visible to a request
  handled by another, which shows up as intermittent/flaky-looking
  behavior. A shared Redis (many cPanel hosts offer one, or use a
  managed Redis add-on) fixes that.
- The DB pooling (`CONN_MAX_AGE`, `CONN_HEALTH_CHECKS`) already in
  `settings.py` means each worker reuses its DB connection instead of
  reconnecting every request — that scales fine with more instances.

If you outgrow shared hosting, moving to a VPS with nginx in front of a
few Gunicorn/Passenger workers is the natural next step, and this
project's settings (SITE_URL, ALLOWED_HOSTS, static/media handling)
already work in that setup without further changes.

source /home/ofjrdbsn/virtualenv/2Hame/3.12/bin/activate && cd /home/ofjrdbsn/2Hame