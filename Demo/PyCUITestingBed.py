import py_cui
from pprint import pprint

"""
A playground to see Attributes of widgets which document is not complete about. 
"""


class TestSubject:
    def __init__(self, root_):
        self.root = root_

        self.widgets = [
            self.root.add_button("test", 0, 0, command=self.passer),
            self.root.add_block_label("test", 0, 1),
            self.root.add_label("test", 0, 2),
            self.root.add_scroll_menu("test", 1, 0),
            self.root.add_slider("test", 1, 1)
        ]

        output = {type(x): [att for att in dir(x) if not att.startswith("_")] for x in self.widgets}
        pprint(output)

    def passer(self):
        pass


if __name__ == '__main__':
    root = py_cui.PyCUI(5, 5)
    ref = TestSubject(root)

    # root.start()
    # Forgot to use type hint, it would trigger pycharm to reveal all available attributes.
