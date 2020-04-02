def order_handler():
    order = {}

    def ordered_handler(f):
        order[f.__name__] = len(order)
        return f

    def compare_handler(a, b):
        return [1, -1][order[a] < order[b]]

    return ordered_handler, compare_handler
