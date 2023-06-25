"""
Transaction fee policies

VITE EPIC-002 Token fees:
- Deposit transaction   ->   0.0 EPIC
- Withdraw transaction  ->   0.5 EPIC
- Tip transaction       ->   0.7%
"""
from decimal import *


ctx = getcontext()
ctx.prec = 8


class Fee:
    """
    Base Fee class for EpicTipBot transactions fees.
    """
    pass

class ViteFee(Fee):
    """
    Fee class for the EpicTipBot Vite blockchain transactions
    """
    ADDRESS = "vite_7693d3816ef70526faaf1b48922357835d2df8f5a8f95ede06"
    WITHDRAW = Decimal('0.001').normalize(ctx)
    TIP = Decimal('0.01').normalize(ctx)

    @staticmethod
    def normalize(value: float | str | int | Decimal) -> Decimal:
        if isinstance(value, Decimal):
            return value.normalize(ctx)
        else:
            return Decimal(str(value)).normalize(ctx)

    @classmethod
    def get_tip_fee(cls, value: float | str | int | Decimal) -> Decimal:
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        return Decimal(value * cls.TIP).normalize(ctx)
