# Memory Overcommitment Manager
# Copyright (C) 2010 Adam Litke, IBM Corporation
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
import pytest
from mom.Policy import Parser

@pytest.fixture
def evaluator():
    return Parser.Evaluator()

@pytest.fixture
def entity():
    class TestEntity(object):
        def __init__(self):
            self.a = 12
            self.b = 7
        def mod(self, a, b):
            self.a = a % b
            return self.a
    return TestEntity()

@pytest.fixture
def guest_list():
    """Fixture to create a list of guest objects"""
    class Guest:
        def __init__(self, num):
            self.num = num
        def name(self):
            return f"Guest-{self.num}"

    return [Guest(1), Guest(2), Guest(4)]

@pytest.fixture
def empty_guest():
    class Guest(object):
        def __init__(self, num):
            self._num = num

        @property
        def num(self):
            return self._num

    return Guest(None)

@pytest.fixture
def valid_guest():
    class Guest(object):
        def __init__(self, num):
            self._num = num

        @property
        def num(self):
            return self._num

    return Guest(0)

def verify_policy(evaluator, policy, expected):
    results = Parser.eval(evaluator, policy)
    assert results == expected

def test_comments(evaluator):
    pol = """
    # This is a full-line pound comment
    12 # A partial-line comment with (+ 23 43) keywords
    (+ 3 # An expression with embedded comments
    2)
    """
    results = Parser.eval(evaluator, pol)
    assert results == [ 12, 5 ]

def test_whitespace(evaluator):
    pol = """
    (+ 1
    2)  (- 10 2)
    """
    verify_policy(evaluator, pol, [ 3, 8 ])

def test_string(evaluator):
    pol = """
    "foo" "bar"

    # Operators on strings have the same effect as for Python
    (+ "Hello " "World!")
    (+ (* 3 "Hey ") "!")
    """
    verify_policy(evaluator, pol, [ "foo", "bar", "Hello World!", "Hey Hey Hey !" ])

def test_basic_math(evaluator):
    pol = """
    10
    0o0                  # Octal
    .3                  # The leading 0 on a float is not required
    (* 0 1)
    (+ 1 2)
    (/ 11 2)            # Integer division
    (/ 11 2.0)          # Floating point division
    (* 3 6)
    (- 1 9)             # Negative result
    (* (- 8 6) 9)
    (>> (<< 1 4) 2)
    (+ 0xFF 0x1)        # Hex numbers
    (* 0o11 0o2)
    (+ 0xa 10)          # Numeric type mixing
    (+ 10.0e3 100e-2)   # Scientific notation for integers and floats
    """
    verify_policy(evaluator, pol, [ 10, 0, 0.3, 0, 3, 5.5, 5.5, 18, -8, 18, 4, 256, 18, 20,
                10001.0 ])

def test_compare(evaluator):
    pol = """
    (< 5 4)
    (> 1 0)
    (<= 10 10)
    (>= 2 (/ 10 2))
    (== (+ 1 2) (/ 9 3))
    (!= "foo" "foo")
    (== 0x0 0)
    """
    verify_policy(evaluator, pol, [ False, True, True, False, True, False, True ])

def test_logic(evaluator):
    pol = """           # Again, these bahave according to Python rules
    (and 1 "")          # "" evaluates to false
    (and 0 1)           #   as does 0 -- the first false value is returned
    (and 1 2)           # If all values are true, the last value is returned
    (or "" 17)          # or returns the first true value encountered
    (or "" "")          # if all values are false, or returns the last one
    (not "")            # The only false values are: 0 and ""
    (not -0)
    """
    verify_policy(evaluator, pol, [ "", 0, 2, 17, "", True, True ])

def test_extended_logic(evaluator):
    pol = """           # Again, these bahave according to Python rules
    (and 1 1 "")          # "" evaluates to false
    (and 0 0 1)           #   as does 0 -- the first false value is returned
    (and 1 1 2)           # If all values are true, the last value is returned
    (or "" "" 17)          # or returns the first true value encountered
    (or "" "" "")          # if all values are false, or returns the last one
    (and 1 2 3 4 5 6 7 8 9 0)
    (or 0)
    """
    verify_policy(evaluator, pol, [ "", 0, 2, 17, "", 0, 0 ])

def test_vars(evaluator):
    pol = """
    (defvar foo "bar")
    (defvar a 5)
    (defvar b 6)
    (+ a b)
    (set a 8)
    (+ a b)
    (* foo 2)
    (defvar e3 7)
    (+ 1 e3)        # Make sure e3 is not mistaken for scientific notation
    """
    verify_policy(evaluator, pol, [ 'bar', 5, 6, 11, 8, 14, "barbar", 7, 8 ])

def test_funcs(evaluator):
    pol = """
    (def foo () 10)
    (def bar (a)
        (* 2 a))
    (/ (foo) (bar 5))
    (def baz (b)
        (- 2 (bar b)))
    (baz 12)
    (def foo (a) {
        (def bar (b) (+ b 1))   # Nested function
        (bar a)
    })
    (foo 9)
    """
    verify_policy(evaluator, pol, [ 'foo', 'bar', 1, 'baz',  -22, 'foo', 10 ])

def test_let(evaluator):
    pol = """
    (def foo (a) (+ 2 a))
    (defvar a 2)
    (let ((a 1) (b 2)) (foo a))
    a                               # Value of 'a' unaffected by let
    (let ((a 1) (b 2)) a b)         # multiple expressions in let
    """
    verify_policy(evaluator, pol, [ 'foo', 2, 3, 2, 2 ])

def test_minmax(evaluator):
    pol = """
    (min 1 2 3 0)
    (defvar a 8)
    (defvar c (min 8 7 6 5))
    (max 0 c a 3)
    """
    verify_policy(evaluator, pol, [ 0, 8, 5, 8 ])

def test_if(evaluator):
    pol = """
    (defvar a 1)
    (defvar b 0)
    (def f (cond)
        (if cond
            "yes"
            "no"))
    (if a 4 3)
    (if b 1 0)
    (f (> 2 1))
    """
    verify_policy(evaluator, pol, [ 1, 0, 'f', 4, 0, "yes"])

def test_scope(evaluator):
    pol = """
    (defvar a 10)
    (def foo (b) (set a b))         # set affects the global 'a'
    (foo 2)
    a
    (def foo (b) (defvar a b))      # defvar creates a local 'a'
    (foo 4)
    a
    (set a 5)
    (let ((a 4)) a)                 # let creates a local 'a'
    a
    (if (== a 5) (defvar a 4) 0)    # if creates a local 'a'
    a
    """
    verify_policy(evaluator, pol, [ 10, 'foo', 2, 2, 'foo', 4, 2, 5, 4, 5, 5, 5 ])

def test_multi_statements(evaluator):
    pol = """
    { 10 4 }                # A multi-statement evaluates to the last value
    (def f (a b) {          # Use them for function bodies
        (defvar c (+ a b))
        (set c (+ 1 c))
        c
    })
    (f 4 5)
    (defvar q 11)
    (let ((q 2) (r 3)) {            # Use them for let statements
        q r
        (- r q)
    })
    (if (== q 11) {                 # Use them in if statements
        "q maintains proper scope"
        (set q 12)                  # setq sets the value in closest scope
    } {                             # that knows about q
        "oops, q has the wrong value"
    })
    (- q 10)
    """
    verify_policy(evaluator, pol, [ 4, 'f', 10, 11, 1, 12, 2 ])

def test_multi_statements_lisp(evaluator):
    pol = """
    (def f (a b) (let ()           # Use them for function bodies
        (defvar c (+ a b))
        (set c (+ 1 c))
        c
    ))
    (f 4 5)

    (defvar q 11)
    (let ((q 2) (r 3))             # Use them for do statements
        (+ q r)
        (- r q)
    )
    q
    (if (== q 11) (let ()          # Use them in if statements
        "q maintains proper scope"
        (set q 12)
    ) (
        "oops, q has the wrong value"
    ))
    (- q 10)
    """
    verify_policy(evaluator, pol, [ 'f', 10, 11, 1, 11, 12, 2 ])

def test_entity_write(evaluator, entity):
    evaluator.stack.set('Entity', entity, True)
    pol = """
    (set Entity.a 1)
    """
    # Direct modification of Entity attributes is explicitly not enabled
    #  - but may be in the future if needed.
    with pytest.raises(Exception):
        Parser.eval(evaluator, pol)

def test_entities(evaluator, entity):
    evaluator.stack.set('Entity', entity, True)
    pol = """
    Entity.a                    # Read variables
    Entity.b
    (Entity.mod Entity.b 4)     # Call functions
    """
    verify_policy(evaluator, pol, [ 12, 7, 3 ])
    assert entity.a == 3 # The 'mod' function changes Entity.a

def test_externals(evaluator):
    pol = """
    (+ (abs -21) (abs 21))
    """
    verify_policy(evaluator, pol, [ 42 ])

def test_syntax_error(evaluator):
    pol = """
    (+ 2 2
    """
    with pytest.raises(Parser.PolicyError):
        Parser.eval(evaluator, pol)

def test_not_null(evaluator):
    pol = """
    (null 0 1 2 "")
    """
    verify_policy(evaluator, pol, [False])

def test_parse_error(evaluator):
    pol = """
    (2 + 2)
    """
    with pytest.raises(Parser.PolicyError):
        Parser.eval(evaluator, pol)

def test_null(evaluator):
    pol = """
    (null nil)
    """
    verify_policy(evaluator, pol, [True])

def test_multiple_defvar(evaluator):
    pol = """
    (defvar balloonEnabled 1)
    (defvar balloonEnabled 0)  # second defvar in the same scope does not
    balloonEnabled             # touch the value
    (defvar balloonEnabled 2)
    balloonEnabled
    """
    verify_policy(evaluator, pol, [1, 1, 1, 1, 1])

def test_setq(evaluator):
    pol = """
    (defvar balloonEnabled 1)
    balloonEnabled
    (setq balloonEnabled 2)
    balloonEnabled
    (set balloonEnabled 3)
    balloonEnabled
    """
    verify_policy(evaluator, pol, [1, 1, 2, 2, 3, 3])

def test_debug(evaluator):
    pol = """
    (debug "test" 1 nil "lala")
    """
    verify_policy(evaluator, pol, ["lala"])

def test_valid(evaluator):
    evaluator.stack.set('empty', [], True)
    pol = """
    (valid "test" 1 nil "lala")
    (valid "test" 1 "lala")
    (valid)
    (valid nil)
    (valid 0 "" empty)
    """
    verify_policy(evaluator, pol, [False, True, True, False, True])

def test_not_enough_arguments(evaluator):
    pol = """
    (and)
    """
    with pytest.raises(Parser.PolicyError) as result:
        verify_policy(evaluator, pol, [None])

    assert str(result.value) == \
        "not enough arguments for 'c_and' on line 2"

def test_bad_arity(evaluator):
    pol = """
    (not)
    """
    with pytest.raises(Parser.PolicyError) as result:
        verify_policy(evaluator, pol, [None])

    assert str(result.value) == \
        "arity mismatch in doc parsing of 'c_not' on line 2"

def test_bad_syntax_number(evaluator):
    pol = """
    156
    125f56
    """

    with pytest.raises(Parser.PolicyError) as result:
        verify_policy(evaluator, pol, [156, None])

    assert str(result.value) == \
        "undefined symbol f56 on line 3"

def test_bad_arity_def(evaluator):
    pol = """
    (def test (x y) {
    })
    (test 1)
    """

    with pytest.raises(Parser.PolicyError) as result:
        verify_policy(evaluator, pol, [None])

    assert str(result.value) == \
        "Function \"test\" invoked with incorrect arity on line 4"

def test_guest_list(guest_list, evaluator):
    evaluator.stack.set('Guests', guest_list, True)
    pol = """
    (def guestName (guest) (+ "This guest's name is " (guest.name)))
    (with Guests guest (guestName guest))
    """
    # The results of 'with' are returned in their own list
    # This means that (with ...) cannot be evaluated yet
    verify_policy(evaluator, pol, [ "guestName",
                       [ "This guest's name is Guest-1",
                         "This guest's name is Guest-2",
                         "This guest's name is Guest-4" ] ])

def test_nil_attribute(empty_guest, evaluator):
    evaluator.stack.set('guest', empty_guest, True)
    pol = """
    guest.num
    (== guest.num nil)
    (== guest.num 0)
    """
    verify_policy(evaluator, pol, [None, True, False])

def test_valid_nil_attribute(evaluator, empty_guest, valid_guest):
    evaluator.stack.set('guest', empty_guest, True)
    evaluator.stack.set('guest2', valid_guest, True)

    pol = """
    guest.num
    (valid guest.num)
    (valid guest2.num)
    """
    verify_policy(evaluator, pol, [None, False, True])
