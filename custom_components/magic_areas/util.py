import functools
import operator


def flatten_list(input_list):
    return functools.reduce(operator.iconcat, input_list, [])
