import os
from signal import SIGTERM
from time import monotonic
from typing import Optional

from celery.worker.autoscale import Autoscaler

AUTOSCALE_KEEPALIVE = float(os.environ.get('AUTOSCALE_KEEPALIVE', 30))


class ShutdownWhenNoTasksAutoscaler(Autoscaler):

    def __init__(self,
                 pool,
                 max_concurrency,
                 min_concurrency=0,
                 worker=None,
                 keepalive=AUTOSCALE_KEEPALIVE,
                 mutex=None):
        super().__init__(pool, max_concurrency, min_concurrency, worker, keepalive, mutex)
        from text_extraction_system.config import get_settings
        self.cool_down_period_sec = get_settings().celery_shutdown_when_no_tasks_longer_than_sec
        self.no_tasks_start: Optional[float] = None
        print(f'Configuring celery to shutdown when there were no tasks for more than '
              f'f{self.cool_down_period_sec} seconds.')

    def _maybe_scale(self, req=None):
        res = super()._maybe_scale(req)

        if self.qty:
            # if there are tasks then reset "no tasks" time counter
            self.no_tasks_start = None
        elif not self.no_tasks_start:
            # if there are no tasks and the "no tasks" counter is not started - then start it
            self.no_tasks_start = monotonic()
        elif monotonic() - self.no_tasks_start > self.cool_down_period_sec:
            # if there are no tasks and the counter is started and the time out passed - then shutdown
            print(f'Shutting down because there were no tasks for more than {self.cool_down_period_sec} seconds')
            os.kill(os.getpid(), SIGTERM)

        return res
