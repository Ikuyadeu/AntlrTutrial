import unittest
from pyantlr.change_detector import ChangeDetector

# Longest Commmon SubSequence(not SubString)
class TestChangeDetector(unittest.TestCase):
    CC = ChangeDetector("", "")

    def test_if(self):
        code = """if X >= 0:"""

        """
        1:<INVALID>:if
        2:NAME:X
        3:<INVALID>:>=
        4:NUMBER:0
        5:<INVALID>::
        5:NEWLINE:NEWLINE
        5:ENDMARKER:ENDMARKER
        5:NEWLINE:<missing NEWLINE>
        """
        self.CC.set_code(code, code)
        self.assertEqual(self.CC.getTokenCount(code), 5)

    def test_for(self):
        code = """for x in range(5):
                        pass """

        """
        1:<INVALID>:for
        2:NAME:x
        3:<INVALID>:in
        4:NAME:range
        5:OPEN_PAREN:(
        6:NUMBER:5
        7:CLOSE_PAREN:)
        8:<INVALID>::
        8:NEWLINE:NEWLINE
        8:INDENT:INDENT
        9:<INVALID>:pass
        9:NEWLINE:NEWLINE
        9:DEDENT:DEDENT
        """
        self.CC.set_code(code, code)
        self.assertEqual(self.CC.getTokenCount(code), 9)

    def test_string_change(self):
        code_a = """
        print(\"helloworld!helloworld!\")"""
        code_b = """print(\"hello world!hello_world!\")"""
        self.CC.set_code(code_a, code_b)
        self.CC.set_diff(self.CC.LCS_FLAG)
        self.assertFalse(self.CC.isSameLayout())
        self.assertTrue(self.CC.isStringChange())

    def atest_dict_is_same(self):
        # 置いとく
        code_a = \
        """
snippet = {'yaql': {'expression': '$.data.var1.len()',
                    'data': {
                    'var1': {'list_join': ['', ['1', '2']]}
                    }
            }}
"""

        code_b = \
"""snippet = {'yaql': {'expression': '$.data.var1.len()',
                        'data': {'var1': {'list_join': ['', ['1', '2']]}}}}"""
        self.CC.set_code(code_a, code_b)
        self.assertFalse(self.CC.isLayoutChange())
        self.assertGreater(len(self.CC.makeNotLCS()), 3)
        

    def test_foo_to_bar(self):
        code_a = "foo = 0"
        code_b = "bar += 1"
        self.CC.set_code(code_a, code_b)
        self.CC.set_diff(self.CC.LCS_FLAG)
        self.assertTrue(self.CC.isNameChange())
        self.assertTrue(self.CC.isNumberChange())
        self.assertTrue(self.CC.isOperatorChange())
        self.assertEqual(len(self.CC.makeNotLCS()), 6)

    def test_add_func(self):
        code_a = "if not a:"
        code_b = "if a.isEmpty():"
        self.CC.set_code(code_a, code_b)
        self.assertGreater(len(self.CC.makeNotLCS()), 3)

    def test_add_and(self):
        code_a = "if a > 1:"
        code_b = "if a > 1 and x:"
        self.CC.set_code(code_a, code_b)
        self.CC.set_code(code_a, code_b)
        self.assertLess(len(self.CC.makeNotLCS()), 3)
        self.assertEqual(len(self.CC.makeNotDup()), 2)

    def test_add_and2(self):
        code_a = "if a > 1:"
        code_b = "if x and a > 1:"
        self.CC.set_code(code_a, code_b)
        self.assertLess(len(self.CC.makeNotLCS()), 3)
        self.assertEqual(len(self.CC.makeNotDup()), 2)

    def test_int_to_float(self):
        code_a = "if a > 1:"
        code_b = "if a > 1.5:"
        self.CC.set_code(code_a, code_b)
        self.CC.set_diff(self.CC.LCS_FLAG)
        self.assertTrue(self.CC.isNumberChange())

        code_a = "if a > -1:"
        code_b = "if a > -1.5:"
        self.CC.set_code(code_a, code_b)
        self.CC.set_diff(self.CC.LCS_FLAG)
        self.assertTrue(self.CC.isNumberChange())

    def test_big_delete(self):
        code_a = """if a > 1:
                        pass
                        if a > 5:
                            pass
                """

        code_b = """if a > 5:
                        pass
                """
        self.CC.set_code(code_a, code_b)
        self.assertEqual(len(self.CC.makeNotDup()), 6)        
        self.assertGreater(len(self.CC.makeNotLCS()), 3)
        self.assertEqual(len(self.CC.makeLD()), 6)

    def test_LD(self):
        code_a = "if a > b:"
        code_b = "if a > a:"
        self.CC.set_code(code_a, code_b)
        # self.assertEqual(len(self.CC.makeLCS()), 2)
        self.assertEqual(len(self.CC.makeLD()), 1)

    def test_swich_value(self):
        code_a = "if a > b:"
        code_b = "if b > a:"
        self.CC.set_code(code_a, code_b)
        self.CC.set_diff(self.CC.LCS_FLAG)
        self.assertTrue(self.CC.isNameChange())
        self.CC.set_diff(self.CC.DIFF_FLAG)
        self.assertFalse(self.CC.isNameChange())
        code_a =\
"""if provider in SUPPORTED_ENCRYPTION_PROVIDERS:
            provider = SUPPORTED_ENCRYPTION_PROVIDERS[provider]
        # TODO(lyarwood): Change this warning to an error in Pike if the
        # provider is not found in SUPPORTED_ENCRYPTION_PROVIDERS
        elif provider not in SUPPORTED_ENCRYPTION_PROVIDERS.values():
            LOG.warning(_LW("Use of the unsupported encryptor class "
                            "%(provider) will be blocked with the Pike "
                            "release of Nova."), {'provider': provider})"""
if __name__ == '__main__':
    unittest.main()