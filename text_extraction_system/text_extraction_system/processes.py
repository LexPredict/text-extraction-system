import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from io import StringIO
from subprocess import CompletedProcess
from threading import Thread
from typing import List, Callable, TextIO, Optional, Any

import psutil

READ_LEN = 100


class ProcessKilledByTimeout(Exception):
    pass


class ProcessReturnedErrorCode(Exception):
    pass


class InjuredDocumentError(Exception):
    pass


def render_process_msg(completed_process: CompletedProcess) -> str:
    msg = f'Command line:\n' \
          f'{completed_process.args}'

    if completed_process.stdout:
        msg += f'\nProcess stdout:\n' \
               f'===========================\n' \
               f'{completed_process.stdout}\n' \
               f'===========================\n'
    if completed_process.stderr:
        msg += f'\nProcess stderr:\n' \
               f'===========================\n' \
               f'{completed_process.stderr}\n' \
               f'===========================\n'
    return msg


def raise_from_process(log: logging.Logger, completed_process: CompletedProcess, process_title: Callable[[], str]):
    error_title = process_title()
    error_message = render_process_msg(completed_process)
    if completed_process.returncode != 0:
        if 'java.io.IOException: Error: Expected operator' in error_message \
                or 'document is injured' in error_message:
            raise InjuredDocumentError('The document is injured and cannot be processed.')
        else:
            raise ProcessReturnedErrorCode(f'Process returned non-zero code:\n'
                                           f'{error_title}\n'
                                           f'{error_message}')
    elif log.isEnabledFor(logging.DEBUG):
        log.debug(f'Successfully executed sub-process:\n'
                  f'{error_title}\n'
                  f'{error_message}')


def io_pipe_lines(src: TextIO, dst: Callable[[str], None]):
    try:
        for buf in iter(src.readline, ''):
            dst(buf)
    except ValueError:
        pass


def exec(cmd: List[str],
         stdout: Callable[[str], None] = None,
         stderr: Callable[[str], None] = None,
         encoding: str = sys.getdefaultencoding(),
         timeout_sec: int = 60 * 60,
         task: Any = None) -> int:
    with subprocess.Popen(cmd,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          universal_newlines=True,
                          encoding=encoding,
                          preexec_fn=os.setpgrp) as ps:
        if task:
            task.store_spawned_process(ps.pid)
        if stdout:
            Thread(target=io_pipe_lines, args=(ps.stdout, stdout), daemon=True).start()

        if stderr:
            Thread(target=io_pipe_lines, args=(ps.stderr, stderr), daemon=True).start()

        try:
            return ps.wait(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            # ps.kill()
            os.killpg(os.getpgid(ps.pid), signal.SIGTERM)
            ps.wait(timeout=5)
            raise ProcessKilledByTimeout()


def start_process(cmd: List[str],
                  stdout: Callable[[str], None] = None,
                  stderr: Callable[[str], None] = None,
                  encoding: str = sys.getdefaultencoding(),
                  cwd: str = None) -> subprocess.Popen:
    ps = subprocess.Popen(cmd,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          universal_newlines=True,
                          encoding=encoding,
                          cwd=cwd)
    if stdout:
        Thread(target=io_pipe_lines, args=(ps.stdout, stdout), daemon=True).start()

    if stderr:
        Thread(target=io_pipe_lines, args=(ps.stderr, stderr), daemon=True).start()

    return ps


def read_output(cmd: List[str],
                stderr_callback: Callable[[str], None],
                encoding: str = sys.getdefaultencoding(),
                timeout_sec: int = 60 * 60,
                error_if_returner_not: Optional[int] = 0,
                task: Any = None) -> str:
    stdout = StringIO()
    stderr = StringIO()

    def err(line: str):
        stderr.write(line)
        stderr_callback(line)

    def out(line: str):
        stdout.write(line)

    try:
        error_code = exec(cmd, stdout=out, stderr=err,
                          encoding=encoding, timeout_sec=timeout_sec,
                          task=task)
    except ProcessKilledByTimeout:
        raise ProcessKilledByTimeout(f'Process has been killed by timeout.\n'
                                     f'Cmd: {cmd}\n'
                                     f'Timeout (sec): {timeout_sec}\n'
                                     f'Stderr:\n'
                                     f'{stderr.getvalue()}')

    if error_if_returner_not is not None and error_code != error_if_returner_not:
        raise ProcessReturnedErrorCode(f'Process returned wrong error code.\n'
                                       f'Cmd: {cmd}\n'
                                       f'Expected error code: {error_if_returner_not}\n'
                                       f'Actual error code: {error_code}\n'
                                       f'Stderr:\n'
                                       f'{stderr.getvalue()}')
    else:
        return stdout.getvalue()


async def async_read_pipe(pipe, dst: Callable[[str], None]):
    while True:
        buf = await pipe.read()
        if not buf:
            break
        dst(buf)


async def async_exec(program: str, args: List[str], stdout: Callable[[str], None] = None,
                     stderr: Callable[[str], None] = None):
    proc = await asyncio.create_subprocess_exec(program, *args,
                                                stdin=asyncio.subprocess.PIPE,
                                                stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.PIPE)

    io_tasks = list()
    if stderr:
        io_tasks.append(async_read_pipe(proc.stderr, stderr))
    if stdout:
        io_tasks.append(async_read_pipe(proc.stdout, stdout))

    if not io_tasks:
        return await proc.communicate()
    else:
        await asyncio.gather(*io_tasks)


async def async_wait_for_file(file_path, timeout_interval_sec: float = 30, check_interval_sec: float = 0.3):
    start = time.time()
    while True:
        if time.time() - start > timeout_interval_sec:
            raise TimeoutError(f'Timeout waiting for file creation: {file_path}')
        if not os.path.exists(file_path):
            await asyncio.sleep(check_interval_sec)
        else:
            break


def terminate_processes_by_ids(pids: List[int],
                               log_func: Optional[Callable[[str], None]] = None):
    count_terminated, count_skipped, count_failed = 0, 0, 0
    # terminate spawned processes
    for pid in pids:
        try:
            p = psutil.Process(pid)
            if p:
                p.terminate()
                count_terminated += 1
            else:
                count_skipped += 1
        except psutil.NoSuchProcess:
            count_skipped += 1
        except:
            count_failed += 1
    if log_func:
        log_func(f'terminate_processes(): {count_terminated} spawned processed are terminated, '
                 f'{count_skipped} skipped, {count_failed} failed to terminate')
