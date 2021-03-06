import os
from hypothesis import settings

settings.register_profile("ci", settings(max_examples=1000))
settings.register_profile("default", settings(max_examples=100))
settings.load_profile(os.getenv(u"HYPOTHESIS_PROFILE", "default"))

LIST_CYCLE_MIN_LENGTH = 1
LIST_CYCLE_MAX_LENGTH = 100
