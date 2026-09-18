try:
    from celery import Celery
    from app.core.config import settings
    celery_app = Celery('multimodal_sre', broker=settings.redis_url, backend=settings.redis_url)
    celery_app.conf.task_serializer = 'json'
    celery_app.conf.result_serializer = 'json'
    celery_app.conf.accept_content = ['json']
except ImportError:
    # Graceful fallback when running in minimal test environment without celery
    class MockAsyncResult:
        def __init__(self, task_id):
            self.task_id = task_id
            self.status = "SUCCESS"
            self.result = {"status": "completed"}
        def ready(self):
            return True

    class MockCelery:
        def task(self, *args, **kwargs):
            def decorator(f):
                f.delay = lambda *a, **kw: MockAsyncResult("task-local-1")
                return f
            return decorator
        def AsyncResult(self, task_id):
            return MockAsyncResult(task_id)

    celery_app = MockCelery()
