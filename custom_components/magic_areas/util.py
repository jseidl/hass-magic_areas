from collections.abc import Iterable

basestring = (str, bytes)


def is_entity_list(item):
    return isinstance(item, Iterable) and not isinstance(item, basestring)


def flatten_entity_list(input_list):

    for i in input_list:
        if is_entity_list(i):
            for sublist in flatten_entity_list(i):
                yield sublist
        else:
            yield i
