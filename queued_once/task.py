import hashlib

from celery import Task
from celery.utils import uuid
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.cache import get_cache
from django.utils.functional import cached_property
try:
    from django_redis.cache import RedisCache
except ImportError:
    RedisCache = None

log = get_task_logger(__name__)


class QueuedOnceTask(Task):
    abstract = True
    once_key_arg = None

    _LOCK_EXPIRE = 60 * 60 * 24  # 24 hours

    @cached_property
    def cache(self):
        backend = getattr(
            settings, 'CELERY_QUEUES_ONCE_CACHE_BACKEND', 'default')
        return get_cache(backend)

    def _key_from_args(self, args=None, kwargs=None):
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}

        if self.once_key_arg is None:
            sorted_kwargs = [(key, kwargs[key]) for key in sorted(kwargs)]
            key_args = (args, sorted_kwargs)
        elif isinstance(self.once_key_arg, int):
            if len(args) <= self.once_key_arg:
                raise ValueError(
                    'Task requires at least {} positional argument(s) due to '
                    'once_key_arg={}'
                    .format(self.once_key_arg + 1, self.once_key_arg))
            key_args = args[self.once_key_arg]
        else:
            if self.once_key_arg not in kwargs:
                raise ValueError(
                    'Task requires keyword argument {0!r} due to once_key_arg'
                    .format(self.once_key_arg))
            key_args = kwargs[self.once_key_arg]

        unhashed = unicode((self.__module__, self.__name__, key_args))
        hashed = hashlib.md5(unhashed.encode('utf-8'))
        return 'queuedtasks:{}'.format(hashed.hexdigest())

    def _get_lock(self, key):
        task_id = self.cache.get(key)
        return task_id

    def _take_lock(self, task_id, key):

        # Determine if we're using Redis as our cache
        is_redis = RedisCache is not None and isinstance(self.cache, RedisCache)

        # If we're using Redis, utilize SETNX
        set_kwargs = {'nx': True} if is_redis else {}

        # Set the lock in the cache
        self.cache.set(key, task_id, self._LOCK_EXPIRE, **set_kwargs)

    def _clear_lock(self, key):
        self.cache.delete(key)

    @staticmethod
    def _propagates_exceptions():
        return getattr(settings, 'CELERY_EAGER_PROPAGATES_EXCEPTIONS', False)

    def apply_async(self, args=None, kwargs=None, **other):
        if self._propagates_exceptions():
            log.warning(
                'Cannot take a lock and reliably clear it when '
                'CELERY_EAGER_PROPAGATES_EXCEPTIONS is True.')
            return super(QueuedOnceTask, self).apply_async(
                args, kwargs, **other)

        key = self._key_from_args(args, kwargs)

        # See if this task is already queued
        task_id = self._get_lock(key)
        if task_id:
            log.debug(
                'Got a duplicate task for one that was previously queued.',
                extra={'data': {
                    'task_id': task_id,
                    'name': self.__name__,
                    'args': args,
                    'kwargs': kwargs
                }}
            )
            return self.AsyncResult(task_id)

        # Generate or get the task_id and use it.
        task_id = other.setdefault('task_id', uuid())
        self._take_lock(task_id, key)

        # Actually apply the task
        return super(QueuedOnceTask, self).apply_async(args, kwargs, **other)

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        if not self._propagates_exceptions():
            self._clear_lock(self._key_from_args(args, kwargs))

        return super(QueuedOnceTask, self).after_return(
            status, retval, task_id, args, kwargs, einfo)
