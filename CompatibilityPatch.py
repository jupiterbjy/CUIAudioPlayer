from typing import Union, Iterable
from collections import OrderedDict
import GetModuleReference


# Target 3.7 to 3.8, only listing what I'm using.
# will run these in order, so adding suffix as sorting key.


def a_suffix_prefix_patch():
    try:
        getattr(str, "endswith")

    except AttributeError:
        # < Python 3.8

        def mock_suffix(self: str, suffix: Union[str, Iterable]):
            if isinstance(suffix, str):
                suffix = [suffix]

            for suffix_candidate in suffix:
                # Python's `in` is faster than manual search.
                # We first check if sub-string is in string.
                if suffix_candidate in self:

                    # if it contains, then check again with last char off.
                    # If it still finds string, it's not suffix.
                    if suffix_candidate not in self[:-1]:
                        return True
                        # If it can't find string, then it's suffix.

            return False

        def mock_prefix(self: str, prefix: Union[str, Iterable]):
            if isinstance(prefix, str):
                prefix = [prefix]

            for prefix_candidate in prefix:

                if prefix_candidate in self:
                    if prefix_candidate not in self[1:]:
                        return True

            return False

        str.endswith = mock_suffix
        str.startswith = mock_prefix


def b_remove_suffix_prefix_patch():
    """Only applies for str. No bytes."""
    try:
        getattr(str, "removesuffix")
    except AttributeError:
        # < Python 3.9

        def mock_remove_suffix(self: str, suffix: str):
            if self.endswith(suffix):
                return self[:-len(suffix)]

        def mock_remove_prefix(self: str, prefix: str):
            if self.startswith(prefix):
                return self[len(prefix):]

        str.removesuffix = mock_remove_suffix
        str.removeprefix = mock_remove_prefix


def fetch_and_run_patches():
    function_dict = GetModuleReference.list_function(__name__, return_dict=True)

    for _, patch in OrderedDict(sorted(function_dict.items())):
        patch()
