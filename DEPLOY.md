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
2. Upload the code (passenger_wsgi.py at the app root, same as now).
3. In the cPanel Python App terminal:
   ```
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```
4. Restart the app (cPanel "Restart" button, or `touch tmp/restart.txt`
   if your setup uses that convention).

That's it — no settings.py edits, no gunicorn to think about.

## Local development

`.env` locally just needs `DEBUG=True` and `DB_ENGINE` left unset (it
defaults to SQLite). Everything else in `.env.example` is optional for
local work.
