from celery import Celery

from config import Config


def make_celery(config_class=Config):
    celery = Celery(
        "leegality",
        broker=config_class.CELERY_BROKER_URL,
        backend=config_class.CELERY_RESULT_BACKEND,
        include=["extraction"],
    )
    celery.conf.update(
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_soft_time_limit=60,
        task_time_limit=120,
        task_track_started=True,
    )
    if config_class.CELERY_TASK_ALWAYS_EAGER:
        celery.conf.task_always_eager = True
        celery.conf.task_eager_propagates = True
    return celery


celery = make_celery()


def init_celery(celery_app: Celery, flask_app) -> None:
    celery_app.conf.update(
        broker_url=flask_app.config["CELERY_BROKER_URL"],
        result_backend=flask_app.config["CELERY_RESULT_BACKEND"],
    )
    if flask_app.config.get("CELERY_TASK_ALWAYS_EAGER"):
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True

    class ContextTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask
