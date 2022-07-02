from collections import Iterable


def flatten_entity_list(input_list):

    basestring = (str, bytes)

    for i in input_list:
        if isinstance(i, Iterable) and not isinstance(i, basestring):
            for sublist in flatten_entity_list(i):
                yield sublist
        else:
            yield i
