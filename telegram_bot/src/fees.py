"""
Transaction fee policies

VITE EPIC-002 Token fees:
- Deposit transaction   ->   0.0 EPIC
- Withdraw transaction  ->   0.5 EPIC
- Tip transaction       ->   0.7%
"""
from decimal import *

from .keys import FEE_ADDRESS


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
    ADDRESS = FEE_ADDRESS
    WITHDRAW = Decimal('0.05').normalize(ctx)
    TIP = Decimal('0.01').normalize(ctx)

    def fee_values(self):
        return {"withdraw": self.WITHDRAW, 'tip': float(str(self.TIP)) * 100}

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
