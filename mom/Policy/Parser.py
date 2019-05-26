# Memory Overcommitment Manager
# Copyright (C) 2010 Anthony Liguori and Adam Litke, IBM Corporation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
import logging
from functools import total_ordering

import re
from .spark import GenericScanner, GenericParser

class PolicyError(Exception): pass

@total_ordering
class Token(object):
    def __init__(self, kind, value=None, line=None):
        self.kind = kind
        self.line = line
        if value == None:
            self.value = kind
        else:
            self.value = value

    def __eq__(self, rhs):
        return self.kind == rhs

    def __ne__(self, rhs):
        return not self == rhs

    def __lt__(self, rhs):
        return self.kind < rhs

    def __repr__(self):
        return '[%s %s]' % (self.kind, self.value)

class NumericToken(Token):
    def __init__(self, type, value, line=None):
        self.type = type
        Token.__init__(self, 'number', value, line)

class Scanner(GenericScanner):
    def __init__(self, operators=''):
        self.operators = operators
        GenericScanner.__init__(self)

    def get_re(self, name):
        if name == 'user_op':
            def escape(op):
                nop = ''
                for ch in op:
                    if ch in '+*.':
                        nop += '\\'
                    nop += ch
                return nop
            return ' %s ' % '|'.join(map(escape, self.operators))
        else:
            raise AttributeError(name)

    def tokenize(self, input):
        self.rv = []
        GenericScanner.tokenize(self, input)
        return self.rv

    def t_whitespace(self, s, line):
        r' \s+ '
        return s.count("\n")

    def t_pound_comment(self, s, line):
        r' \#.*?\n '
        pass

    def t_symbol(self, s, line):
        r' [A-Za-z_][A-Za-z0-9_\-\.]* '
        self.rv.append(Token('symbol', s, line))

    def t_string(self, s, line):
        r' "([^"\\]|\\.)*" '
        self.rv.append(Token('string', s, line))

    def t_single_quote_string(self, s, line):
        r" '([^'\\]|\\.)*' "
        self.rv.append(Token('string', s, line))

    def t_float(self, s, line):
        r' -?(0|([1-9][0-9]*))*(\.[0-9]+)([Ee][+-]?[0-9]+)? '
        self.rv.append(NumericToken('float', s, line))

    def t_integer(self, s, line):
        r' -?(0(?![0-9Xx])|[1-9][0-9]*)(?![0-9eE]) '
        self.rv.append(NumericToken('integer', s, line))

    def t_integer_with_exponent(self, s, line):
        r' -?(0(?![0-9Xx])|[1-9][0-9]*)[Ee][+-]?[0-9]+ '
        # Python only recognizes scientific notation on float types
        self.rv.append(NumericToken('float', s, line))

    def t_hex(self, s, line):
        r' 0[Xx][0-9A-Fa-f]+ '
        self.rv.append(NumericToken('hex', s, line))

    def t_octal(self, s, line):
        r' 0[0-9]+ '
        self.rv.append(NumericToken('octal', s, line))

    def t_builtin_op(self, s, line):
        r' [\(\){}\[\]] '
        self.rv.append(Token(s, line=line))

    def t_user_op(self, s, line):
        self.rv.append(Token('operator', s, line))

class Parser(GenericParser):
    def __init__(self, start='value'):
        GenericParser.__init__(self, start)

    def mklist(self, args):
        if len(args) == 2:
            return []
        return args[1]

    def p_value_list(self, args):
        '''
          value_list ::= value
          value_list ::= value_list value
        '''
        if len(args) == 1:
            return [args[0]]
        return args[0] + [args[1]]

    def p_list(self, args):
        '''
          list ::= ( )
          list ::= ( value_list )
        '''
        return self.mklist(args)

    def p_bracket_list(self, args):
        '''
          bracket_list ::= [ ]
          bracket_list ::= [ value_list ]
        '''
        return self.mklist(args)

    def p_curly_list(self, args):
        '''
          curly_list ::= { }
          curly_list ::= { value_list }
        '''
        return [Token('symbol', 'eval')] + self.mklist(args)

    def p_value(self, args):
        '''
          value ::= operator
          value ::= number
          value ::= operator
          value ::= symbol
          value ::= string
          value ::= single_quote_string
          value ::= list
          value ::= curly_list
          value ::= bracket_list
         '''
        return args[0]

class ExternalFunctions(object):
    '''
    This class defines a set of Python functions that will be callable from
    within a policy definition.  Each function must be defined as a static
    method.
    '''
    @staticmethod
    def abs(x):
        return __builtins__['abs'](x)

    @staticmethod
    def debug(*values):
        'value ...'
        logging.getLogger("mom.Evaluator").debug("debug: %s", values)
        return values[-1]

class GenericEvaluator(object):
    operator_map = {}

    def __init__(self):
        pass

    def get_operators(self):
        """
        Return the list of defined operators. It must return more specific
        operators first or parsing errors will appear.

        eg. << must appear before <
        """
        return sorted(self.operator_map.keys(),
                      key = lambda x:len(x),
                      reverse = True)

    def parse_doc(self, doc):
        scanner = Scanner(['...'])
        tokens = scanner.tokenize(doc)
        parser = Parser(start='value_list')
        return parser.parse(tokens)

    # TODO: split up doc parsing...
    # use elipse syntax to indicate repetition in a
    # list.  IOW:
    # (number ...)
    # is a list of zero or more numbers
    # ((symbol value) ...)
    # is a list of zero or more tuples of symbol value
    # (symbol number ...)
    # is a list containing a symbol and zero or more numbers
    def _dispatch(self, fn, args, line):
        doc = fn.__doc__
        if doc == None:
            args = list(map(self.eval, args))
        else:
            types = self.parse_doc(doc)

            # check if we can check arity - it is not possible when variable
            # number of arguments is expected so instead check for the
            # minimal number of required arguments
            if len(types) != len(args) and (types[-1].value != '...'
                                            or types[-1].kind != 'operator'):
                raise PolicyError("arity mismatch in doc parsing of '%s'"
                                  " on line %d" % (fn.__name__, line))
            elif types[-1].value == '...' and len(types) > len(args) + 1:
                raise PolicyError("not enough arguments for '%s'"
                                  " on line %d" % (fn.__name__, line))

            i = 0
            while types and i < len(args):
                # if we are repeating (...) element types, leave type intact
                if types[0].value != '...' or types[0].kind != 'operator':
                    type = types.pop(0)
                # also get the type when it is the first ... or operator
                elif i == 0:
                    type = types[0]

                if type.value == 'code':
                    i += 1
                    continue
                elif type.value == 'symbol':
                    if not isinstance(args[i], Token) or args[i].kind != 'symbol':
                        raise PolicyError('malformed expression'
                                          ' on line %d' % line)
                    args[i] = args[i].value
                else:
                    args[i] = self.eval(args[i])

                # next argument
                i += 1

        return fn(*args)

    def eval(self, code):
        if isinstance(code, Token):
            if code.kind == 'number':
                return self.eval_number(code)
            elif code.kind == 'string':
                return code.value[1:-1]
            elif code.kind == 'symbol':
                if code.value == "nil":
                    return None
                else:
                    return self.eval_symbol(code.value, code.line)
            else:
                raise PolicyError('Unexpected token type "%s" on line %d' %
                                  (code.kind, code.line))

        node = code[0]
        if not isinstance(node, Token):
            print(code)
            raise PolicyError('Expected simple token as arg 1')

        if node.kind == 'symbol':
            name = node.value
        elif node.kind == 'operator':
            name = self.operator_map[node.value]
        else:
            raise PolicyError('Unexpected token type in arg 1 "%s"'
                              ' on line %d' % (node.kind, node.line))

        func = self.stack.get(name, line=node.line, allow_undefined=True)
        if func is not None:
            args = list(map(self.eval, code[1:]))
            return func(*args)
        elif hasattr(self, 'c_%s' % name):
            return self._dispatch(getattr(self, 'c_%s' % name), code[1:], line=node.line)
        elif hasattr(self, "default"):
            return self.default(name, code[1:], line=node.line)
        else:
            raise PolicyError('Unknown function "%s" with no default handler'
                              ' on line %d' % (name, node.line))

class VariableStack(object):
    def __init__(self):
        self.stack = []

    def enter_scope(self):
        self.stack = [{}] + self.stack

    def leave_scope(self):
        self.stack = self.stack[1:]

    def get(self, name, allow_undefined=False, line=None):
        # Split the name on '.' to handle object references
        parts = name.split('.')
        obj = parts[0]
        for scope in self.stack:
            if obj in scope:
                if len(parts) > 1:
                    if hasattr(scope[obj], parts[1]):
                        return getattr(scope[obj], parts[1])
                else:
                    return scope[obj]
        if allow_undefined:
            return None
        raise PolicyError("undefined symbol %s on line %d" % (name, line))

    def set(self, name, value, alloc=False):
        if alloc:
            self.stack[0].setdefault(name, value)
            return self.stack[0][name]

        for scope in self.stack:
            if name in scope:
                scope[name] = value
                return value

        raise PolicyError("undefined symbol %s" % name)

class Evaluator(GenericEvaluator):
    operator_map = {'+': 'add', '-': 'sub',
                    '*': 'mul', '/': 'div',
                    '<': 'lt', '>': 'gt',
                    '<=': 'lte', '>=': 'gte',
                    '<<': 'shl', '>>': 'shr',
                    '==': 'eq', '!=': 'neq',
                    'and': 'and', 'or': 'or', 'not': 'not',
                    'min': 'min', 'max': 'max', "null": "null",
                    "valid": "valid"}

    def __init__(self):
        GenericEvaluator.__init__(self)
        self.stack = VariableStack()
        self.funcs = {}
        self.stack.enter_scope()
        self.import_externs()

    def import_externs(self):
        for i in dir(ExternalFunctions):
            if not re.match("__", i):
                self.stack.set(i, getattr(ExternalFunctions, i), True)

    def eval_symbol(self, name, line):
        return self.stack.get(name, line=line)

    def eval_number(self, token):
        if token.type == 'float':
            return float(token.value)
        elif token.type in ('integer', 'hex', 'octal'):
            return int(token.value, 0)
        else:
            raise PolicyError("Unsupported numeric type for token"
                              " '%s' on line %d" % (token, token.line))

    def default(self, name, args, line):
        if name == 'eval':
            return map(self.eval, args)[-1]

        params, code = self.funcs[name]
        if len(params) != len(args):
            raise PolicyError('Function "%s" invoked with incorrect arity'
                              ' on line %d' % (name, line))

        scope = []
        for i in range(len(params)):
            scope.append([params[i], args[i]])

        return self.eval([Token('symbol', 'let'), scope, code])

    def c_def(self, name, params, code):
        'symbol code code'
        self.funcs[name] = (params, code)
        return name

    # defun is an alias to def, maintain def for backwards compatibility
    c_defun = c_def

    def c_set(self, name, value):
        'symbol value'
        return self.stack.set(name, value)

    # setq is an alias to set here, note that in lisp set evaluates it's first argument as well
    c_setq = c_set

    def c_defvar(self, name, value):
        'symbol value'
        return self.stack.set(name, value, True)

    def c_let(self, syms, *code):
        'code code ...'
        if type(syms) != list:
            raise PolicyError('Expecting list as arg 1 in let')

        self.stack.enter_scope()
        for sym in syms:
            if type(sym) != list or len(sym) != 2:
                raise PolicyError('Expecting list of tuples in arg1 of let')
            name, value = sym
            if name.kind != 'symbol':
                raise PolicyError('Expecting list of (symbol value) in let')
            self.stack.set(name.value, self.eval(value), True)
        for expr in code:
            result = self.eval(expr)
        self.stack.leave_scope()
        return result

    def c_with(self, iterable, iterator, code):
        'symbol symbol code'

        list = self.stack.get(iterable)
        result = []
        for item in list:
            self.stack.enter_scope()
            self.stack.set(iterator, item, True)
            result.append(self.eval(code))
            self.stack.leave_scope()
        return result

    def c_if(self, cond, yes, no):
        'value code code'

        if cond:
            return self.eval(yes)
        else:
            return self.eval(no)

    def c_add(self, x, y):
        'value value'
        return x + y

    def c_sub(self, x, y):
        'value value'
        return x - y

    def c_mul(self, x, y):
        'value value'
        return x * y

    def c_div(self, x, y):
        'value value'
        return x / y

    def c_lt(self, x, y):
        'value value'
        return x < y

    def c_gt(self, x, y):
        'value value'
        return x > y

    def c_lte(self, x, y):
        'value value'
        return x <= y

    def c_gte(self, x, y):
        'value value'
        return x >= y

    def c_eq(self, x, y):
        'value value'
        return x == y

    def c_neq(self, x, y):
        'value value'
        return x != y

    def c_shl(self, x, y):
        'value value'
        return x << y

    def c_shr(self, x, y):
        'value value'
        return x >> y

    def c_and(self, *args):
        'value ...'
        for arg in args:
            if not arg:
                return arg
        return args[-1]

    def c_or(self, *args):
        'value ...'
        for arg in args:
            if arg:
                return arg
        return args[-1]

    def c_not(self, x):
        'value'
        return not x

    def c_min(self, *args):
        'value ...'
        return min(args)

    def c_max(self, *args):
        'value ...'
        return max(args)

    def c_null(self, *args):
        '...'
        try:
            return all(v is None or len(v) == 0 for v in args)
        except TypeError:
            # some value is not null and not iterable
            return False

    def c_valid(self, *args):
        '...'
        try:
            return not any(v is None for v in args)
        except TypeError:
            return False

def get_code(e, string):
    try:
        scanner = Scanner(e.get_operators())
        tokens = scanner.tokenize(string)
        parser = Parser(start='value_list')
        return parser.parse(tokens)
    except SystemExit:
        raise PolicyError("parse error")

def eval(e, string):
    code = get_code(e, string)
    results = []
    for expr in code:
        results.append(e.eval(expr))
    return results

def repl(e):
    while True:
        print('>>>')
        try:
            string = input()
        except EOFError:
            break

        print(eval(e, string)[0])

if __name__ == '__main__':
    import sys

    e = Evaluator()

    if len(sys.argv) > 1:
        f = open(sys.argv[1], 'r')
        try:
            lines = f.read()
        finally:
            f.close()
        results = eval(e, lines)
        for result in results:
            print(result)
    else:
        repl(e)
