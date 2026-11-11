"""输入校验：检查商品、价格和数量。"""


def validate_order(payload):
    """返回校验后的订单。"""
    if not payload.get('product'):
        raise ValueError('product is required')
    if payload.get('price', -1) < 0 or payload.get('quantity', 0) <= 0:
        raise ValueError('price must be nonnegative and quantity must be positive')
    return dict(payload)
