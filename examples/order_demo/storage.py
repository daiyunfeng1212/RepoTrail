"""存储示例：构建回执，不连接外部数据库。"""


def save_order(order, total):
    """返回订单回执。"""
    return {'product': order['product'], 'total': total, 'status': 'accepted'}
