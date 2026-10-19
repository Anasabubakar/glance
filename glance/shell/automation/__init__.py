"""
Glance automations: fast, exact, no-AI handling of everyday tasks.

    from automation import handle, Ctx
    result = handle(Ctx(manager), "tile this window left and open the calculator")

`handle` returns a Result when it understood and did the whole request, otherwise None
(then the request goes to the AI). Importing this package registers every rule.
"""

from . import (apps, filesys, infoqa, routines, shortcuts, system, web, windows)  # noqa: F401
from .ctx import Ctx, FakeCtx  # noqa: F401
from .registry import Result, handle, rules, understands  # noqa: F401
