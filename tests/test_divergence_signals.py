import pandas as pd
from nexus.signals import _divergence_signals


def _frame():
    n=24
    frame=pd.DataFrame({
        "low":[110.0]*n,"high":[120.0]*n,"rsi":[50.0]*n,
        "bb_lower":[100.0]*n,"bb_upper":[130.0]*n,
    })
    # L1 bullish low at 5, full 3/3 pivot, RSI 25
    frame.loc[2:8,"low"]=[108,106,104,100,104,106,108]
    frame.at[5,"rsi"]=25.0
    # L2 bullish lower low at 14, fast 3/1 pivot, RSI 34 and BB touch
    frame.loc[11:15,"low"]=[105,102,99,95,101]
    frame.at[14,"rsi"]=34.0
    frame.at[14,"bb_lower"]=96.0
    return frame


def test_bullish_divergence_signal_uses_l1_3_right_l2_1_right():
    frame=_frame()
    result=_divergence_signals(frame,"LONG",3,3,1,30.0,8.0,True)
    assert bool(result.at[15,"setup"])
    assert result.at[15,"l1_price"] == 100.0
    assert result.at[15,"l2_price"] == 95.0
    assert result.at[15,"rsi_difference"] == 9.0


def test_band_touch_is_required():
    frame=_frame(); frame.at[14,"bb_lower"]=94.0
    result=_divergence_signals(frame,"LONG",3,3,1,30.0,8.0,True)
    assert not bool(result["setup"].any())
