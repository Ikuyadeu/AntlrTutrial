import sys
from collections import Counter
from antlr4 import TerminalNode, InputStream, CommonTokenStream
from antlr4.error.ErrorListener import ConsoleErrorListener
from difflib import ndiff, SequenceMatcher, Differ, ndiff
from subprocess import Popen, PIPE
import json


class Tokenizer():
    IGNORE_CONTENTS = ["ENDMARKER","DEDENT"]
    IDENTIFIER_TAG = ""

    def __init__(self, language: str):
        self.LANGUAGE = language
        if self.LANGUAGE == "Python":
            from .grammers.Python.Python3Parser import Python3Parser as Parser
            from .grammers.Python.Python3Lexer import Python3Lexer as Lexer
            self.IDENTIFIER_TAG = "NAME"
            self.STRING_TAG = "STRING"  
            self.NUMBER_TAG = "NUMBER"
            self.VOCABULARY = Parser.symbolicNames
        elif self.LANGUAGE == "Java":
            from .grammers.Java.JavaParser import JavaParser as Parser
            from .grammers.Java.JavaLexer import JavaLexer as Lexer
            self.IDENTIFIER_TAG = "IDENTIFIER"
            self.STRING_TAG = "STRING_LITERAL"
            self.NUMBER_TAG = "DECIMAL_LITERAL"
            self.VOCABULARY = Parser.symbolicNames
        elif self.LANGUAGE == "JavaScript":
            from .grammers.JavaScript.JavaScriptParser import JavaScriptParser as Parser
            from .grammers.JavaScript.JavaScriptLexer import JavaScriptLexer as Lexer
            self.VOCABULARY = Parser.symbolicNames
            self.IDENTIFIER_TAG = "Identifier"
            self.STRING_TAG = "StringLiteral"
            self.NUMBER_TAG = "DecimalLiteral"
        elif self.LANGUAGE == "CPP":
            from .grammers.CPP.CPP14Parser import CPP14Parser as Parser
            from .grammers.CPP.CPP14Lexer import CPP14Lexer as Lexer
            self.VOCABULARY = Parser.symbolicNames
            self.IDENTIFIER_TAG = "Identifier"
            self.STRING_TAG = "Stringliteral"
            self.NUMBER_TAG = "Integerliteral"
        elif self.LANGUAGE == "PHP":
            from .grammers.PHP.PhpParser import PhpParser as Parser
            from .grammers.PHP.PhpLexer import PhpLexer as Lexer
            self.VOCABULARY = Parser.symbolicNames
            self.IDENTIFIER_TAG = "VarName"
            self.STRING_TAG = "StringPart"
            self.NUMBER_TAG = "Decimal"
        else:
            print("Unknown Language, so solve as Python")
            from .grammers.Python.Python3Parser import Python3Parser as Parser
            from .grammers.Python.Python3Lexer import Python3Lexer as Lexer
            self.VOCABULARY = Parser.symbolicNames

        self.Parser = Parser
        self.Lexer = Lexer

    def getTokens(self, code):
        if self.LANGUAGE == "Python":
            return self.makeTokensPython(self.getTree(code), [])
        return self.makeTokens(self.getTree(code), [])

    def getPureTokens(self, code):
        try:
            return [x[0] for x in self.getTokens(code) if not (x[0].startswith("<") and x[0].endswith(">"))]
        except:
            return []

    def getTree(self, code: str):
        # code = code_trip(code)
        parser = self.Parser(CommonTokenStream(self.Lexer(InputStream(code))))
        parser.removeErrorListeners()
        if self.LANGUAGE == "Python":
            tree = parser.single_input()
        elif self.LANGUAGE == "Java":
            tree = parser.compilationUnit()
        elif self.LANGUAGE == "JavaScript":
            tree = parser.sourceElement()
        elif self.LANGUAGE == "CPP":
            tree = parser.translationunit()
        elif self.LANGUAGE == "PHP":
            tree = parser.htmlDocument()
        else:
            tree = parser.single_input()

        return tree

    def makeTokens(self, tree, tokens: list):
        if isinstance(tree, TerminalNode):
            symbollic_name = self.VOCABULARY[tree.symbol.type]
            if symbollic_name not in self.IGNORE_CONTENTS:
                if len(tokens) > 0:
                    previous_token = tokens[-1]
                    before_index = previous_token[3] + len(previous_token[0])
                else:
                    before_index = 0
                start = tree.getPayload().start
                space = start - before_index
                string = tree.getText()
                if not string.startswith("<missing"):
                    tokens.append((string, symbollic_name, space, start))
        for i in range(tree.getChildCount()):
            tree2 = tree.getChild(i)
            self.makeTokens(tree2, tokens)
        return tokens


    def makeTokensPython(self, tree, tokens: list):
        if isinstance(tree, TerminalNode):
            symbollic_name = self.VOCABULARY[tree.symbol.type]
            if symbollic_name not in self.IGNORE_CONTENTS:
                line = tree.parentCtx.start.line
                if len(tokens) > 0:
                    previous_token = tokens[-1]
                    before_index = previous_token[3] + len(previous_token[0])

                    if line < previous_token[4]:
                        line = previous_token[4]
                    elif line > previous_token[4]:
                        tokens.append(("\n" * (line - previous_token[4]), "new_line", 0, previous_token[3], previous_token[4]))
                else:
                    before_index = 0
                start = tree.getPayload().start
                space = start - before_index
                string = tree.getText()
                if not string.startswith("<missing"):
                    tokens.append((string, symbollic_name, space, start, line))
        for i in range(tree.getChildCount()):
            tree2 = tree.getChild(i)
            self.makeTokensPython(tree2, tokens)
        return tokens

    def make_change_set(self, source, target):

        change_set = {}
        change_set = {
            "a": self.getPureTokens(source),
            "b": self.getPureTokens(target)
        }

        if len(change_set["a"]) == 0 or\
            len(change_set["b"]) == 0 or\
                change_set["a"] == change_set["b"]:
            return -1

        opcodes = SequenceMatcher(None, change_set["a"], change_set["b"]).get_opcodes()
        diffs = []

        for tag, a_i1, a_i2, b_i1, b_i2 in opcodes:
            symbol = opt_tag2symbol(tag)
            if symbol == "*":
                change_a = devide_token_sequence(change_set["a"][a_i1:a_i2])
                change_b = devide_token_sequence(change_set["b"][b_i1:b_i2])
                if len(change_a) <= 1 and len(change_a) <= 1:
                    sequence = [" ".join([symbol] + change_a[0] + ["-->"] + change_b[0])]
                else:
                    a_out =  [" ".join(["-"] + x) for x in change_a]
                    b_out =  [" ".join(["+"] + x) for x in change_b]
                    sequence = a_out + b_out
            elif symbol == "-":
                out = change_set["a"][a_i1:a_i2]
                sequence = [" ".join([symbol] + x) for x in devide_token_sequence(out)]
            elif symbol == "+":
                out = change_set["b"][b_i1:b_i2]
                sequence = [" ".join([symbol] + x) for x in devide_token_sequence(out)]
            elif symbol == "=":
                out = devide_token_sequence(change_set["b"][b_i1:b_i2])
                sequence = [" ".join([symbol] + x) for x in out]
                diffs.extend(sequence)
            else:
                continue
            diffs.extend(sequence)            
        return diffs

    def make_change_set_line(self, source, target):
        differ = Differ().compare(source, target)
        differ = ndiff(source.splitlines(keepends=True),
                       target.splitlines(keepends=True))
        previous_symbol = " "
        previous_tokens = []
        out = []
        for diff in differ:
            symbol = diff[0]
            if len(diff) < 3 or symbol == "?":
                continue
            if symbol == " ":
                continue
            elif symbol == "-":
                token = self.getPureTokens(diff[2:])
                if token == []:
                    continue
                if previous_symbol == "-":
                    out.append([("-", previous_tokens)])
                elif previous_symbol == "+":
                    changed_tokens = self.get_lines_diff(previous_tokens, token)
                    token = []
                    if changed_tokens != []:
                        out.append(changed_tokens)
            elif symbol == "+":
                token = self.getPureTokens(diff[2:])
                if token == []:
                    continue
                if previous_symbol == "+":
                    out.append([("+", previous_tokens)])
                if previous_symbol == "-":
                    changed_tokens = self.get_lines_diff(previous_tokens, token)
                    token = []
                    if changed_tokens != []:
                        out.append(changed_tokens)
            previous_symbol = symbol
            previous_tokens = token
        if previous_symbol in ["+", "-"]:
            out.append([{"tag": previous_symbol, "tokens": previous_tokens}])
        return out
    
    def get_lines_diff(self, previous_tokens, token):
        changed_tokens = []
        matcher = SequenceMatcher(None,
        previous_tokens, token)
        for tag, a_i1, a_i2, b_i1, b_i2 in matcher.get_opcodes():
            symbol2 = opt_tag2symbol(tag)
            if symbol2 == "*":
                changed_tokens.append({"tag": symbol2, "tokens": [previous_tokens[b_i1:b_i2], token[a_i1:a_i2]]})
            elif symbol2 == "-":
                changed_tokens.append({"tag": symbol2, "tokens": previous_tokens[a_i1:a_i2]})
            elif symbol2 == "+":
                changed_tokens.append({"tag": symbol2, "tokens": token[b_i1:b_i2]})
            elif symbol2 == "=":
                changed_tokens.append({"tag": symbol2, "tokens":  token[b_i1:b_i2]})
            else:
                continue
        return changed_tokens

    def get_abstract_tree_diff(self, source, target):
        tokens_a = clean_symbol(self.getTokens(source))
        tokens_b = clean_symbol(self.getTokens(target))

        abstract_index = 0
        abstracted_identifiers = {}
        for i, token_a in [x for x in enumerate(tokens_a)
                        if x[1][1] in [self.IDENTIFIER_TAG, self.STRING_TAG, self.NUMBER_TAG]]:
            if token_a[0] in abstracted_identifiers:
                tokens_a[i] = (f"${{{abstracted_identifiers[token_a[0]]}:{token_a[1]}}}", "ABSTRACT_SNIPPET", token_a[2], token_a[3])
                continue

            for j, token_b in [x for x in enumerate(tokens_b)
                            if x[1][1] in [self.IDENTIFIER_TAG, self.STRING_TAG, self.NUMBER_TAG]]:
                if token_b[0] in abstracted_identifiers:
                    tokens_b[j] = (f"${{{abstracted_identifiers[token_b[0]]}:{token_b[1]}}}", "ABSTRACT_SNIPPET", token_b[2], token_b[3])
                    continue
                # if identifiers looks function
                elif token_a[0] == token_b[0] and i + 1 < len(tokens_a) and tokens_a[i+1][0] != "(":
                    tokens_a[i] = (f"${{{abstract_index}:{token_a[1]}}}", "ABSTRACT_SNIPPET", token_a[2], token_a[3])
                    tokens_b[j] = (f"${{{abstract_index}:{token_b[1]}}}", "ABSTRACT_SNIPPET", token_b[2], token_b[3])
                    abstracted_identifiers[token_a[0]] = abstract_index
                    abstract_index += 1
        non_abstracted_identifiers = {"condition": list(set([x[0] for x in tokens_a
                                                    if x[1] == self.IDENTIFIER_TAG])),
                                      "consequent": list(set([x[0] for x in tokens_b
                                                     if x[1] == self.IDENTIFIER_TAG]))}
        real_condition = tokens2Realcode(tokens_a)
        real_consequent = tokens2Realcode(tokens_b)
        if isIdentifiersReplace(real_condition, real_consequent, non_abstracted_identifiers):
            return {"condition": non_abstracted_identifiers["condition"][0],
                    "consequent": non_abstracted_identifiers["consequent"][0],
                    "abstracted": {}}

        return {"condition": real_condition,
                "consequent": real_consequent,
                "abstracted": {v: k for k, v in abstracted_identifiers.items()}}

def tokens2Realcode(tokens):
    return "".join([" " * x[2] + x[0] for x in tokens])


def isIdentifiersReplace(condition, consequent, identifiers):
    condition_set = set(identifiers["condition"])
    consequent_set = set(identifiers["consequent"])
    origin_condition = list(condition_set - consequent_set)
    origin_consequent = list(consequent_set - condition_set)
    return len(origin_condition) == len(origin_consequent) == 1 and\
           condition.replace(origin_condition[0], origin_consequent[0]) == consequent


def opt_tag2symbol(opt_tag):
    if opt_tag == "replace":
        return "*"
    elif opt_tag == "delete":
        return "-"
    elif opt_tag == "insert":
        return "+"
    elif opt_tag == "equal":
        return "="
    else:
        return "?"


def devide_token_sequence(sequence):
    if " " not in sequence:
        return [sequence]
    new_sequence = []
    indexes = [i for i, x in enumerate(sequence) if x in [" ", "\n", "\t"]]
    previous_index = 0
    for index in indexes:
        new_sequence.append(sequence[previous_index+1:index])
        previous_index = index
    if previous_index + 1 != len(sequence):
        new_sequence.append(sequence[previous_index+1:])
    return new_sequence


def IS_CHARACTER_JUNK(ch, ws=" \t\n"):
    return ch in ws


def clean_diff(diffs):
    return [x for x in diffs if not x.startswith("?")]


def clean_symbol(tokens):
    return [("\n", "NEWLINE", x[2], x[3], x[4]) if x[1] == "NEWLINE" else\
            ("\t", "INDENT", x[2], x[3], x[4]) if x[1] == "INDENT" else x for x in tokens
            if x[0] != "<EOF>"]

def code_trip(code):
    splited_code = code.splitlines(keepends=True)
    max_space = min(len(x) - len(x.lstrip()) for x in splited_code)
    return "".join([x[max_space:] for x in splited_code])

def main():
    code = [[
"""for i in range(len(my_array)):
    element = my_array[i]
    for a in b:
        pass""",
"""for i, element in enumerate(my_array):"""],
["""

for (i in range(len(my_array))){
    element = my_array[i]}""",
"""

for (i, element in enumerate(my_array)){}"""],
[
""" 
def some_method(arg1=:default, arg2=nil, arg3=[])
  a = c
end
""",
"""
def some_method(arg1 = :default, arg2 = nil, arg3 = [])
  a = b
end
"""
],
[
"""
tf.scalar_summary('regularization_loss', regularization_loss,
name='regularization_loss')
""",
"""
tf.summary.scalar('regularization_loss', regularization_loss)
"""
],
[
"""
print("hello", 2)
""",
"""
printf("hello", hhh)
"""
],
[
"""
    bisect_tests(options.bisect, options, options.modules, options.parallel)
""",
"""bisect_tests(
    options.bisect, options, options.modules, options.parallel,
    options.start_at, options.start_after,
)
"""
],
[
"""
a.b.create!(path: \"aaa\")
""",

"""
a.b.create!(name: \"aaa\")
"""
]

]
    TN = Tokenizer("Python")
    # expect_out = [
    # {
    #     "condition": ["for ${1:i} in range(len(${2:my_array})):",
    #                    "\t${3:element} = ${2:array}[${1:element}]"],
    #     "consequent": ["for ${1:i}, ${3:element} in enumerate(${2:my_array}):"]
    # }
    # ]

    target = code[6]
    result = TN.get_abstract_tree_diff(target[0], target[1])
    condition = result["condition"]
    consequent = result["consequent"]
    # print(result)

    print(f"inputA:\n{target[0]}")
    print(condition)
    print(f"inputB:\n{target[1]}")
    print(consequent)




if __name__ == '__main__':
    main()
