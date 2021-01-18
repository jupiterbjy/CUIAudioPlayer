import logging
import inspect


LOGGER = logging.getLogger("UI_DEBUG")
if not LOGGER.handlers:
    _handler = logging.StreamHandler()
    _handler.setLevel("DEBUG")
    _handler.setFormatter(logging.Formatter("[--%(levelname)s--] %(message)s"))
    LOGGER.addHandler(_handler)
    LOGGER.setLevel("DEBUG")


def get_caller_stack_name(depth=1):
    """
    Gets the name of caller.
    :param depth: determine which scope to inspect, for nested usage.
    """
    return inspect.stack()[depth][3]


def log_caller():
    return f"<{get_caller_stack_name()}>"


class CallerLoggedLogger:
    """
    Proxy object for logger.
    Provides same interface to original logger.
    Attributes are added and decorated in lazy manner.
    # format:
         <caller> msg
    """

    def __init__(self, identifier=("<", ">")):
        self.ident_left, self.ident_right = identifier

    def __getattr__(self, item):
        try:
            target = getattr(LOGGER, item)
        except AttributeError:
            raise

        setattr(self, item, self.decorate_logging(target))
        return getattr(self, item)

    def decorate_logging(self, logging_function, ):

        def inner(msg, *args, **kwargs):
            caller = get_caller_stack_name(depth=2)
            logging_function(f"{self.ident_left}{caller}{self.ident_right} {msg}", *args, **kwargs)

        return inner


logger = CallerLoggedLogger()

# def logging_decorator(func):
#     async def inner()

if __name__ == '__main__':
    def test():
        """
        >>> a = CallerLoggedLogger()
        >>> a.debug('this is debug')  # prints on stderr, so no output to stdout.
        >>> a.warning('this is warning')  # and so on.
        >>> "debug" in dir(a)
        True
        >>> "warning" in dir(a)
        True
        >>> "critical" in dir(a)
        False
        >>> def tester():
        ...     a.warning("<-- this guy called me!")
        ...
        >>> tester()  # testing if warning is called out properly.
        """

    import doctest
    doctest.testmod(verbose=True)
