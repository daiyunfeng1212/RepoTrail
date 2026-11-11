"""计价模块：根据商品价格与数量计算总价。"""


def calculate_total(order):
    """计算总价。"""
    return order['price'] * order['quantity']
