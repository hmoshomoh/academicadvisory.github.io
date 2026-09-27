release: python manage.py migrate --noinput && python manage.py bootstrap_roles
web: gunicorn config.wsgi --log-file -
