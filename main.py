import csv
import os
import re
import sys
import json
from antlr_util.tokenizer import Tokenizer
import logging
from pylint import epylint as lint
from collections import Counter

logging.basicConfig(filename='ANTLR_STYLE.log',level=logging.DEBUG)


OUT_JSON_NAME = "out/out"

def main():
    """
    The main
    """
    if len(sys.argv) > 1:
        target_code_path = sys.argv[1]
    else:
        print("""Usage: python %s target_code_path""" % sys.argv[0])
        sys.exit()

    TK = Tokenizer("Python")

    # 対象ファイルを読み込む
    with open(target_code_path, "r") as target_file:
        code_contents = target_file.read()
        splitted_contents = code_contents.splitlines()
        for line in splitted_contents:
            # 行単位でトークン化
            tokens = TK.getTokens(line)

            # 抽象構文木を生成
            tree = TK.getTree(line)
            # 構文木からトークンを生成
            tokens2 = TK.makeTokens(tree, [])
            print(tree)
            print(tokens)
            print(tokens2)
        

if __name__ == '__main__':
    main()
