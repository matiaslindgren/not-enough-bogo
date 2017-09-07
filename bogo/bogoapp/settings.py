from bogoapp import local_settings

LOGO = getattr(local_settings, "LOGO", None)

SQL_DRIVER_LIB = local_settings.SQL_DRIVER_LIB
DATABASE_PATH = local_settings.DATABASE_PATH
SQL_SCHEMA_PATH = local_settings.SQL_SCHEMA_PATH

ODBC_DNS = f"Driver={SQL_DRIVER_LIB};Database={DATABASE_PATH}"

TEMPLATE_PATH="templates"

RANDOM_SEED=1
MINIMUM_SEQUENCE_STOP = 5
MAXIMUM_SEQUENCE_STOP = 15

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
TIMESPEC = "milliseconds"
