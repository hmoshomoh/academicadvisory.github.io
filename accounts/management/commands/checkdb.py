"""Diagnose database connection settings.

Exists because a failed connection reports what libpq saw, not where Django got
it from — so the usual question ("is my .env being read?") has no obvious answer.
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

import config.settings as settings_module


class Command(BaseCommand):
    help = "Show which database settings are in use and try to connect."

    def handle(self, *args, **options):
        env_path = Path(settings.BASE_DIR) / ".env"
        supports_env = hasattr(settings_module, "_load_env_file")

        self.stdout.write("Checking your database setup")
        self.stdout.write("-" * 50)

        if not supports_env:
            self.stdout.write(self.style.ERROR(
                "This copy of the code is out of date and cannot read a .env file.\n"
                "Run:  git pull"
            ))
        elif env_path.exists():
            self.stdout.write(self.style.SUCCESS(".env file   : found"))
        else:
            self.stdout.write(".env file   : not found (that is fine on Mac and Linux)")
            self.stdout.write("              looked in: {}".format(env_path))

        config = settings.DATABASES["default"]
        self.stdout.write("database    : {}".format(config.get("NAME") or "(not set)"))
        self.stdout.write("user        : {}".format(config.get("USER") or "(not set)"))
        self.stdout.write("host        : {}".format(config.get("HOST") or "localhost"))
        self.stdout.write("port        : {}".format(config.get("PORT") or "5432"))
        self.stdout.write("password    : {}".format(
            "set" if config.get("PASSWORD") else "NOT SET"
        ))
        self.stdout.write("-" * 50)

        try:
            connection.ensure_connection()
        except Exception as error:
            self.stdout.write(self.style.ERROR("Could not connect."))
            self.stdout.write("")
            self.stdout.write(str(error).strip())
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(self._hint(str(error), config)))
            return

        self.stdout.write(self.style.SUCCESS("Connected successfully."))
        self.stdout.write("You can run:  python manage.py migrate")

    @staticmethod
    def _hint(error, config):
        error = error.lower()
        if "no password supplied" in error:
            return (
                "What this means: the application connected without a password, so it\n"
                "never saw your DATABASE_URL.\n"
                "Fix: run 'git pull' to get the version that reads .env files, then check\n"
                "the file is named exactly .env and sits next to manage.py (not .env.txt)."
            )
        if "password authentication failed" in error:
            return (
                "What this means: a password was sent but PostgreSQL rejected it.\n"
                "Fix: check the password in your .env is the one you chose when you\n"
                "installed PostgreSQL, and that the user is 'postgres'."
            )
        if "does not exist" in error and config.get("NAME", "") in error:
            return (
                "What this means: the database has not been created yet.\n"
                "Fix (Windows): createdb -U postgres acad_app\n"
                "Fix (Mac/Linux): createdb acad_app"
            )
        if "role" in error and "does not exist" in error:
            return (
                "What this means: PostgreSQL has no user by that name.\n"
                "Fix: on Windows the only user is 'postgres'. Set DATABASE_URL in your\n"
                ".env to use postgres as the user."
            )
        if "could not connect" in error or "refused" in error:
            return (
                "What this means: PostgreSQL is not running, or not on this port.\n"
                "Fix: start PostgreSQL, then check with: pg_isready"
            )
        return "Check Step 7 of README.md for the database setup instructions."
