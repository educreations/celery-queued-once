from celery import current_app
from celery.task import current, task
from django.conf import settings
from django.core.cache import get_cache
from django.test import SimpleTestCase
from django.test.utils import override_settings

from queued_once import QueuedOnceTask


@task(base=QueuedOnceTask)
def lock_taken(*args, **kwargs):
    test_case = kwargs.get('test_case')
    lock = current._get_lock(current._key_from_args(args, kwargs))
    test_case.assertIsNotNone(lock)
    test_case.assertEqual(current.request.id, lock)


@task(base=QueuedOnceTask)
def recursive_task(*args, **kwargs):
    test_case = kwargs.get('test_case')
    test_case.assertEqual(0, recursive_task.count)
    recursive_task.count += 1
    result = recursive_task.delay(*args, **kwargs)
    test_case.assertEqual(result.id, current.request.id)
    test_case.assertEqual(1, recursive_task.count)


@task(base=QueuedOnceTask, once_key_arg='mykey')
def recursive_task_with_key(*args, **kwargs):
    test_case = kwargs.get('test_case')
    depth = kwargs.get('depth', 0)
    test_case.assertEqual(0, depth)
    kwargs['depth'] = depth + 1
    result = recursive_task_with_key.delay(*args, **kwargs)
    test_case.assertEqual(result.id, current.request.id)


@task(base=QueuedOnceTask)
def retry_task(*args, **kwargs):
    test_case = kwargs.get('test_case')
    retry_task.count += 1

    prev_count = retry_task.count
    retry_task.delay(*args, **kwargs)
    test_case.assertEqual(prev_count, retry_task.count)

    if retry_task.count < 3:
        return retry_task.retry(*args, **kwargs)
    test_case.assertEqual(current.request.retries, retry_task.count - 1)
    retry_task.delay(*args, **kwargs)
    test_case.assertEqual(3, retry_task.count)


class CustomException(Exception):
    pass


@task(base=QueuedOnceTask)
def exception_task(*args, **kwargs):
    raise CustomException('Custom')


@task(base=QueuedOnceTask)
def recursive_exception_task(*args, **kwargs):
    test_case = kwargs.get('test_case')
    recursive_exception_task.count += 1
    result = recursive_exception_task.delay(*args, **kwargs)
    test_case.assertEqual(result.id, current.request.id)
    test_case.assertEqual(1, recursive_exception_task.count)

    raise CustomException('Custom')


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=False)
class QueuedOnceTaskTest(SimpleTestCase):

    def setUp(self):
        backend = getattr(
            settings, 'CELERY_QUEUES_ONCE_CACHE_BACKEND', 'default')
        self.cache = get_cache(backend)
        try:
            self.cache.delete_pattern('queuedtasks:*')
        except AttributeError:
            self.cache.clear()
        current_app.config_from_object(settings)

    def assertLockNotTaken(self, task, *args, **kwargs):
        lock = task._get_lock(
            task._key_from_args(args, dict(test_case=self, **kwargs)))
        self.assertIsNone(lock)

    def assertIsUUID(self, value):
        self.assertEqual(36, len(value))

    def test_single_task(self):
        self.assertLockNotTaken(lock_taken)
        result = lock_taken.delay(test_case=self)
        result.get()
        self.assertIsUUID(result.id)
        self.assertLockNotTaken(lock_taken)

    def test_two_tasks(self):
        self.assertLockNotTaken(recursive_task)
        recursive_task.count = 0
        result = recursive_task.delay(test_case=self)
        result.get()
        self.assertIsUUID(result.id)
        self.assertLockNotTaken(recursive_task)

    def test_retry_task(self):
        self.assertLockNotTaken(retry_task)
        retry_task.count = 0
        result = retry_task.delay(test_case=self)
        result.get()
        self.assertIsUUID(result.id)
        self.assertLockNotTaken(retry_task)

    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
    def test_exception_task(self):
        self.assertLockNotTaken(exception_task)
        with self.assertRaises(CustomException):
            exception_task.delay(test_case=self)
        self.assertLockNotTaken(exception_task)

    def test_recursive_exception_task(self):
        self.assertLockNotTaken(recursive_exception_task)
        recursive_exception_task.count = 0
        result = recursive_exception_task.delay(test_case=self)
        with self.assertRaises(CustomException):
            result.get()
        self.assertLockNotTaken(recursive_exception_task)
        self.assertEqual(1, recursive_exception_task.count)

    def test_custom_key(self):
        self.assertLockNotTaken(recursive_task_with_key, mykey=42)
        recursive_task_with_key.delay(test_case=self, mykey=42).get()
        self.assertLockNotTaken(recursive_task_with_key, mykey=42)
