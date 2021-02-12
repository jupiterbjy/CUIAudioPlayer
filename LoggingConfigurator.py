import logging
import inspect


LOG_DETAILED_CALLER = True
# This will log where the function is from.

# TODO: either monkey-patch or use default settings of logging to use logging.getLogger on other sources.

LOGGER = logging.getLogger("UI_DEBUG")

if LOG_DETAILED_CALLER:
    import gc

if not LOGGER.handlers:
    _handler = logging.StreamHandler()
    _handler.setLevel("DEBUG")
    _handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    LOGGER.addHandler(_handler)
    LOGGER.setLevel("DEBUG")


def get_caller_stack_name(depth=1):
    """
    Gets the name of caller.
    :param depth: determine which scope to inspect, for nested usage.
    """
    return inspect.stack()[depth][3]


def get_caller_stack_and_association(depth=1):
    stack_frame = inspect.stack()[depth][0]
    f_code_ref = stack_frame.f_code

    def get_reference_filter():
        for obj in gc.get_referrers(f_code_ref):
            try:
                if obj.__code__ is f_code_ref:  # checking identity
                    return obj
            except AttributeError:
                continue

    actual_function_ref = get_reference_filter()
    try:
        return actual_function_ref.__qualname__
    except AttributeError:
        return "<Module>"

# https://stackoverflow.com/questions/52715425


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

        self.debug = self.debug
        self.info = self.info
        self.warning = self.warning
        self.error = self.error
        self.critical = self.critical
        # triggering __getattr__ so those methods are bound, and show up on inspection either.
        # not a good practice I suppose?
        # Found out there's %(funcName)% in logging parameter, lel.

        self.name_fetching_method = get_caller_stack_and_association if LOG_DETAILED_CALLER else get_caller_stack_name

    def __getattr__(self, item):
        try:
            target = getattr(LOGGER, item)
        except AttributeError:
            raise

        setattr(self, item, self.decorate_logging(target))
        return getattr(self, item)

    def decorate_logging(self, logging_function, ):

        def inner(msg, *args, **kwargs):
            caller = self.name_fetching_method(depth=2)
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
