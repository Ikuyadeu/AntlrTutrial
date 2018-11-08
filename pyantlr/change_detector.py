import sys
from collections import Counter
from antlr4 import TerminalNode, InputStream, CommonTokenStream
from pyantlr.Python2Lexer import Python2Lexer
from pyantlr.Python2Parser import Python2Parser

class ChangeDetector:
    IGNORE_CONTENTS = ["NEWLINE", "INDENT", "DEDENT", "ENDMARKER"]
    VOCABULARY = Python2Parser.symbolicNames

    OPERATOR = ['<','>','==','>=','<=','<>','!=','in','not','is','and', 'or'] + \
            ['|', '^', '&', '<<', '>>', '+', '-', '*', '/', '%', '//', '~'] + \
            ['=', '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>=', '**=', '//=']

    CONTENT = 0
    SYMBOL = 1

    LCS_FLAG = 0
    DIFF_FLAG = 1
    LD_FLAG = 2

    def __init__(self, code_a: str, code_b: str):
        self.code_a = code_a
        self.code_b = code_b
        self.tokens_a =  self.makeTokens(self.getTree(code_a), [])
        self.tokens_b =  self.makeTokens(self.getTree(code_b), [])

    def getTokens(self, code):
        return self.makeTokens(self.getTree(code), [])

    def set_code(self, code_a: str, code_b: str):
        self.code_a = code_a
        self.code_b = code_b
        self.tokens_a =  self.makeTokens(self.getTree(code_a), [])
        self.tokens_b =  self.makeTokens(self.getTree(code_b), [])

    def set_diff(self, flag: int):
        if flag == self.LCS_FLAG:
            self.diff = self.makeNotLCS()
        elif flag == self.DIFF_FLAG:
            self.diff = self.makeNotDup()
        elif flag == self.LD_FLAG:
            self.diff = self.makeLD()
        else:
            self.diff = self.makeNotDup()

    def isLayoutChange(self):
        return len(self.makeNotLCS()) == 0 and len(self.makeNotDup()) == 0

    def isSameLayout(self):
        return all([a[self.CONTENT] == b[self.CONTENT] and
                    a[self.SYMBOL] == b[self.SYMBOL]
                    for a, b in zip(self.tokens_a, self.tokens_b)])

    def isStringChange(self):
        return any([token[self.SYMBOL] == "STRING" for token in self.diff])

    def isNameChange(self):
        return any([token[self.SYMBOL] == "NAME" for token in self.diff])

    def isNumberChange(self):
        return any([token[self.SYMBOL] == "NUMBER" for token in self.diff])

    def isOperatorChange(self):
        return any([token[self.CONTENT] in self.OPERATOR for token in self.diff])

    def getTokenCount(self, code: str):
        tree = self.getTree(code)
        tokens = self.makeTokens(tree, [])
        return len(tokens)

    def getTree(self, code: str):
        code = code.strip()
        lexer = Python2Lexer(InputStream(code))
        stream = CommonTokenStream(lexer)
        parser = Python2Parser(stream)
        tree = parser.single_input()
        # print(tree.toStringTree(None, parser))
        return tree

    def makeTokens(self, tree, tokens: list):
        if isinstance(tree, TerminalNode):
            symbollic_name = self.VOCABULARY[tree.symbol.type]
            if symbollic_name not in self.IGNORE_CONTENTS:
                token = (tree.getText(), symbollic_name)
                tokens.append(token)
        for i in range(tree.getChildCount()):
            tree2 = tree.getChild(i)
            self.makeTokens(tree2, tokens)
        return tokens

    def makeNotLCS(self):
        """
        Not Longest Commmon SubSequence(not SubString)
        """
        lcl_result = Counter(self.makeLCS())
        sub_lcl_a = list((Counter(self.tokens_a) - lcl_result).elements())
        sub_lcl_b = list((Counter(self.tokens_b) - lcl_result).elements())
        return sub_lcl_a + sub_lcl_b

    def makeLCS(self):
        """
        Longest Commmon SubSequence(not SubString)
        """
        lengths = [[0 for j in range(len(self.tokens_b)+1)] for i in range(len(self.tokens_a)+1)]
        # row 0 and column 0 are initialized to 0 already
        for i, x in enumerate(self.tokens_a):
            for j, y in enumerate(self.tokens_b):
                if x == y:
                    lengths[i+1][j+1] = lengths[i][j] + 1
                else:
                    lengths[i+1][j+1] = max(lengths[i+1][j], lengths[i][j+1])
        # read the substring out from the matrix
        result = []
        x, y = len(self.tokens_a), len(self.tokens_b)
        while x != 0 and y != 0:
            if lengths[x][y] == lengths[x-1][y]:
                x -= 1
            elif lengths[x][y] == lengths[x][y-1]:
                y -= 1
            else:
                assert self.tokens_a[x-1] == self.tokens_b[y-1]
                result.append(self.tokens_a[x-1])
                x -= 1
                y -= 1
        return result

    def makeLD(self):
        """
        Levenshtein Distance
        """
        s = self.tokens_a
        t = self.tokens_b
        rows = len(s)+1
        cols = len(t)+1
        dist = [[0 for x in range(cols)] for x in range(rows)]
        dist2 = [[[] for x in range(cols)] for x in range(rows)]
        # source prefixes can be transformed into empty strings 
        # by deletions:
        for i in range(1, rows):
            dist[i][0] = i
            # dist2[i][0].append(s[i - 1])
            dist2[i][0] = dist2[i-1][0] + [s[i-1]]
        # target prefixes can be created from an empty source string
        # by inserting the characters
        for i in range(1, cols):
            dist[0][i] = i
            # dist2[0][i] = dist2[0][i-1] + [t[i-1]]
            dist2[0][i].append(t[i - 1])
        col0 = 0
        row0 = 0
        for col in range(1, cols):
            col0 = col
            for row in range(1, rows):
                row0 = row
                deletion = dist[row-1][col] + 1
                insertion = dist[row][col-1] + 1
                substitution = dist[row-1][col-1] + int(s[row-1] != t[col-1])
                values = [substitution, insertion,deletion]
                dist[row][col] = min(values)
                if dist[row][col] == substitution:
                    if s[row-1] != t[col-1]:
                        # print([s[row-1], t[col-1]])
                        dist2[row][col] = dist2[row-1][col-1] + [t[col-1]]
                    else:
                        dist2[row][col] = dist2[row-1][col-1]
                elif dist[row][col] == insertion:
                    dist2[row][col] = dist2[row][col-1] + [t[col-1]]
                elif dist[row][col] == deletion:
                    dist2[row][col] = dist2[row-1][col] + [s[row-1]]

        return dist2[row0][col0]

    def makeNotDup(self):
        c_a = Counter(self.tokens_a)
        c_b = Counter(self.tokens_b)
        return list((c_a - c_b).elements()) + list((c_b - c_a).elements())


def main():
    code_a = "if not a:"
    code_b = "if a.isEmpty():"
    CC = ChangeDetector(code_a, code_b)
    CC.getTokenCount(code_a)

if __name__ == '__main__':
    main()