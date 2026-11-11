"""订单入口：接收输入并调用校验、计价与持久化模块。"""
from validation import validate_order
from pricing import calculate_total
from storage import save_order


def submit_order(payload):
    """提交订单，从输入字典到订单回执。"""
    order = validate_order(payload)
    total = calculate_total(order)
    return save_order(order, total)


if __name__ == '__main__':
    print(submit_order({'product': 'book', 'price': 40, 'quantity': 2}))
