import celery


def make_celery(app):
    selleri = celery.Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL']
    )
    selleri.conf.update(app.config)

    TaskBase = selleri.Task

    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    selleri.Task = ContextTask

    return selleri
