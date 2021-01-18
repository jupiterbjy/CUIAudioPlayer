from wcwidth import wcswidth, wcwidth
from sys import stdout
from typing import Generator


def pad_actual_length(source: str) -> str:
    """Pad Zero-Width SPace aka ZWSP to match the actual length to visual length."""
    def inner_gen(source_: str) -> Generator[str, None, None]:
        for ch in source_:
            yield "\u200b" + ch if wcwidth(ch) == 2 else ch

    return "".join(inner_gen(source))


print("Raw")
string = "【ENG】【日本語】しぐれうい"
print("Actual width:", wcswidth(string))
print("len:", len(string))
stdout.write("Output: " + string + "\n")

print("\nCompensated with \\u200b")
compensated = pad_actual_length(string)
print("Actual width:", wcswidth(compensated))
print("len:", len(compensated))
stdout.write("Output: " + compensated + "\n")
