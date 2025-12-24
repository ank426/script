#!/usr/bin/python

import sys
import re

# Unicode ranges for common Kanji
kanji_pattern = re.compile(
    r'[\u3400-\u4DBF\u4E00-\u9FFF]'
)

def count_unique_kanji(filenames):
    unique = set()

    for filename in filenames:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    unique.update(kanji_pattern.findall(line))
        except FileNotFoundError:
            print(f"Warning: file not found: {filename}")
        except Exception as e:
            print(f"Error reading {filename}: {e}")

    return unique

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python count_kanji.py <file1> <file2> ...")
        sys.exit(1)

    filenames = sys.argv[1:]
    kanji_set = count_unique_kanji(filenames)

    print(f"Unique kanji count: {len(kanji_set)}")
    print("Kanji:")
    print("".join(sorted(kanji_set)))
