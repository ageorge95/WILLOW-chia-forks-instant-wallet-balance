import sys
from os import path as os_path
sys.path.insert(0,os_path.join(os_path.dirname(__file__)))

def select_backend(coin):
    if coin in ['XCC']:
        from _00_back_end_XCC import WILLOW_back_end
        return WILLOW_back_end
    if coin in ['XJK']:
        from _00_back_end_XJK import WILLOW_back_end
        return WILLOW_back_end
    else:
        from _00_back_end_XCH import WILLOW_back_end
        return WILLOW_back_end
