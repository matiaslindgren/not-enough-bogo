try:
    from bogoapp import local_settings
except ImportError:
    pass # probably running ci tests

LOGO = getattr(local_settings, "LOGO", None)

SQL_DRIVER_LIB = getattr(local_settings, "SQL_DRIVER_LIB", None)
DATABASE_PATH = getattr(local_settings, "DATABASE_PATH", None)
SQL_SCHEMA_PATH = getattr(local_settings, "SQL_SCHEMA_PATH", None)

ODBC_DNS = f"Driver={SQL_DRIVER_LIB};Database={DATABASE_PATH}"

TEMPLATE_PATH="templates"

RANDOM_SEED=1
MINIMUM_SEQUENCE_STOP = 5
MAXIMUM_SEQUENCE_STOP = 15

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
TIMESPEC = "milliseconds"
