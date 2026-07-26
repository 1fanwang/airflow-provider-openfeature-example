"""FAB auth manager config for the hosted, publicly read-only demo.

Anonymous visitors get the Viewer role: browse DAGs, runs, and task instances, but cannot trigger,
edit, or delete. A maintainer still logs in as admin (password set at init).
"""

from flask_appbuilder.const import AUTH_DB

AUTH_TYPE = AUTH_DB
AUTH_ROLE_PUBLIC = "Viewer"
