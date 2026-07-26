"""Webserver config for the hosted, publicly read-only demo.

Anonymous visitors get the Viewer role, so they can browse the UI, the DAGs, and the runs, but cannot
trigger, edit, pause, or delete anything. A maintainer still logs in as admin (set ADMIN_PASSWORD).
"""

from flask_appbuilder.const import AUTH_DB

AUTH_TYPE = AUTH_DB

# Unauthenticated visitors are read-only.
AUTH_ROLE_PUBLIC = "Viewer"
