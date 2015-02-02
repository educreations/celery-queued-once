# Celery Queued Once

A Celery base task that deduplicates tasks that have identical parameters. Uses the Django cache for the locking backend, but works best with [django_redis](https://github.com/niwibe/django-redis).

## Copyright

Copyright © 2015, Educreations, Inc under the MIT software license. See LICENSE for more information.
