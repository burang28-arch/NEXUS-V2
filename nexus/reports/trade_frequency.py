from __future__ import annotations
from pathlib import Path
from typing import Any
import pandas as pd


class TradeFrequencyAnalyzer:
    @classmethod
    def prepare(cls, frame: pd.DataFrame, trades: pd.DataFrame, config: dict[str, Any]):
        long_setup = frame["long_setup"].fillna(False)
        short_setup = frame["short_setup"].fillna(False)
        long_bb = frame.get("long_band_touch", pd.Series(False, index=frame.index)).fillna(False)
        short_bb = frame.get("short_band_touch", pd.Series(False, index=frame.index)).fillna(False)
        executed_long = int((trades.get("side", pd.Series(dtype=str)) == "LONG").sum())
        executed_short = int((trades.get("side", pd.Series(dtype=str)) == "SHORT").sum())
        stages = [
            ("total_candles", len(frame), len(frame)),
            ("bollinger_touch_on_l2", int(long_bb.sum()), int(short_bb.sum())),
            ("confirmed_rsi_divergence", int(long_setup.sum()), int(short_setup.sum())),
            ("executed_trades", executed_long, executed_short),
        ]
        rows=[]; previous=None
        for stage,long_count,short_count in stages:
            total = long_count if stage=="total_candles" else long_count+short_count
            rows.append({
                "stage":stage,"long_count":long_count,"short_count":short_count,
                "total_count":total,
                "dropped_from_previous":0 if previous is None else max(0,previous-total),
                "pass_rate_from_previous_pct":100.0 if previous in (None,0) else total/previous*100.0,
            })
            previous=total
        rejects = pd.DataFrame([
            {"reason":"no_confirmed_divergence_after_band_touch",
             "long_count":max(0,int(long_bb.sum())-int(long_setup.sum())),
             "short_count":max(0,int(short_bb.sum())-int(short_setup.sum()))},
            {"reason":"position_open_or_margin_limit",
             "long_count":max(0,int(long_setup.sum())-executed_long),
             "short_count":max(0,int(short_setup.sum())-executed_short)},
        ])
        rejects["total_count"] = rejects["long_count"] + rejects["short_count"]
        rejects["share_of_all_direction_checks_pct"] = rejects["total_count"]/(len(frame)*2)*100.0
        return pd.DataFrame(rows), rejects

    @classmethod
    def export(cls, frame, trades, config, frequency_output: Path, rejects_output: Path):
        frequency,rejects=cls.prepare(frame,trades,config)
        frequency_output.parent.mkdir(parents=True,exist_ok=True)
        rejects_output.parent.mkdir(parents=True,exist_ok=True)
        frequency.to_csv(frequency_output,index=False)
        rejects.to_csv(rejects_output,index=False)
        return frequency,rejects
