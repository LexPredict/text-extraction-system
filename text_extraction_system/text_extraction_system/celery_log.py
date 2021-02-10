import datetime
from logging import LogRecord, Formatter
from traceback import TracebackException, StackSummary
from typing import Dict, Tuple, List

import json_log_formatter
import pytz
from celery._state import get_current_task

LOG_STACK_TRACE = 'log_stack_trace'


def set_log_extra(log_extra: Dict[str, str] = None):
    task = get_current_task()
    setattr(task, 'log_extra', log_extra)


class HumanReadableTraceBackException(TracebackException):
    _RECURSIVE_CUTOFF = 3

    @classmethod
    def format_stack(cls, stack: StackSummary):
        """Format the stack ready for printing.

        This method is a copy of StackSummary.format() with some readability improvements:
        1. "File: " replaced with "   " just for shortening.
        2. Removed line of code output - in out project we usually throw exceptions with quite verbose error
        messages and the line of code usually appears to be the "raise XXX(the same error message here)"
        and it confuses the reader because it usually contains the same text as the error message but with
        some formatting argument names instead of their values.
        """
        result = []
        last_file = None
        last_line = None
        last_name = None
        count = 0
        for frame in stack:
            if (last_file is None or last_file != frame.filename or
                    last_line is None or last_line != frame.lineno or
                    last_name is None or last_name != frame.name):
                if count > cls._RECURSIVE_CUTOFF:
                    count -= cls._RECURSIVE_CUTOFF
                    result.append(
                        f'  [Previous line repeated {count} more '
                        f'time{"s" if count > 1 else ""}]\n'
                    )
                last_file = frame.filename
                last_line = frame.lineno
                last_name = frame.name
                count = 0
            count += 1
            if count > cls._RECURSIVE_CUTOFF:
                continue
            row = list()
            row.append('  File "{}", line {}, in {}\n'.format(
                frame.filename, frame.lineno, frame.name))
            result.append(''.join(row))
        if count > cls._RECURSIVE_CUTOFF:
            count -= cls._RECURSIVE_CUTOFF
            result.append(
                f'  [Previous line repeated {count} more '
                f'time{"s" if count > 1 else ""}]\n'
            )
        return result

    def human_readable_format(self, suppress_context_for_message: bool = True) -> str:
        message_lines, stack_lines = self.human_readable_format_msg_stack_lines()
        total = list()
        if message_lines:
            total.extend(message_lines)
        if stack_lines:
            total.append('\nStack trace:')
            total.extend(stack_lines)
        return '\n'.join(total)

    def human_readable_format_msg_stack_lines(self,
                                              suppress_context_for_message: bool = True) -> Tuple[List[str], List[str]]:

        error_message = list()
        error_stack = list()

        ex = self  # type: HumanReadableTraceBackException
        prefix = ''

        while True:
            msg = ''.join([line for line in ex.format_exception_only()])
            if hasattr(ex, 'detailed_error'):
                msg += f'\nDetailed error: {ex.detailed_error}'
            msg = msg.strip('\n')
            msg_multiline = '\n' in msg

            # Additional empty line before the next error message if it is multiline
            if prefix:
                if msg_multiline:
                    error_message.append(prefix)
                    error_message.append(msg)
                else:
                    error_message.append(prefix + msg)
            else:
                error_message.append(msg)

            if ex.__cause__ is not None:
                ex = ex.__cause__
                prefix = 'caused by: '
            elif not suppress_context_for_message and ex.__context__ is not None and not ex.__suppress_context__:
                ex = ex.__context__
                prefix = 'raised during processing: '
            else:
                break
            # Additional empty line after the prev error message if it was multi-line
            if msg_multiline:
                error_message.append('')

        ex = self  # type: HumanReadableTraceBackException

        while True:
            error_stack.extend([l.strip('\n') for l in self.format_stack(ex.stack)])
            if ex.__cause__ is not None:
                ex = ex.__cause__
            elif ex.__context__ is not None and not ex.__suppress_context__:
                ex = ex.__context__
            else:
                break
        return error_message, error_stack


class TextFormatter(Formatter):

    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt, datefmt, style)

    def formatException(self, ei):
        exc_type, exception, exc_traceback = ei
        return HumanReadableTraceBackException \
            .from_exception(exception) \
            .human_readable_format()


class JSONFormatter(json_log_formatter.JSONFormatter):
    def mutate_json_record(self, json_record):
        return json_record

    def json_record(self, message: str, extra: Dict, record: LogRecord):

        stack = None
        if not (extra and LOG_STACK_TRACE in extra) and record.exc_info:
            exc_type, exception, exc_traceback = record.exc_info
            exc_message, exc_stack = HumanReadableTraceBackException \
                .from_exception(exception) \
                .human_readable_format_msg_stack_lines()
            message_lines = list()
            if message:
                message_lines.append(message)
            if exc_message:
                message_lines.extend(exc_message)
            message = '\n'.join(message_lines)
            stack = '\n'.join(exc_stack)

        res = {
            '@timestamp': datetime.datetime.utcfromtimestamp(record.created).replace(
                tzinfo=pytz.utc).astimezone().isoformat(),
            'logger': record.name,
            'level': record.levelname,
            'message': message
        }

        task = get_current_task()
        if task and task.request:
            res.update({
                'log_task_id': task.request.id,
                'log_task_name': task.name
            })
            log_extra = getattr(task, 'log_extra', None)
            if log_extra:
                res.update(log_extra)

        if record.levelname in {'ERROR', 'DEBUG', 'WARN'}:
            res.update({
                'process_name': record.processName,
                'process_id': record.process,
                'thread_name': record.threadName,
                'thread_id': record.thread,
                'file_name': record.filename,
                'func_name': record.funcName,
                'line_no': record.lineno,
                'pathname': record.pathname
            })

        if extra:
            for k, v in extra.items():
                if k.startswith('log_'):
                    res[k[len('log_'):]] = v if v is None or isinstance(v, (str, bool, int)) else str(v)

        if stack and LOG_STACK_TRACE not in res:
            res[LOG_STACK_TRACE] = stack

        return res
