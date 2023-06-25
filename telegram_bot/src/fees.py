"""
Transaction fee policies

VITE EPIC-002 Token fees:
- Deposit transaction   ->   0.0 EPIC
- Withdraw transaction  ->   0.5 EPIC
- Tip transaction       ->   0.7%
"""
import decimal


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
    WITHDRAW = decimal.Decimal('0.001').normalize(ctx)
    TIP = decimal.Decimal('0.07')
