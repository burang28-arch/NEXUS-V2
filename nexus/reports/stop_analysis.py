from __future__ import annotations
from pathlib import Path
from typing import Any
import pandas as pd

class StopAnalysis:
    @classmethod
    def prepare(cls, frame: pd.DataFrame, config: dict[str, Any]):
        stop=float(config["risk"]["stop_loss_pct"]); t1=float(config["exit"]["tp1_pct"]); t2=float(config["exit"]["tp2_pct"])
        valid=stop>0 and t1>0 and t2>t1
        rows=[]
        for side,col in (("LONG","long_setup"),("SHORT","short_setup")):
            count=int(frame[col].fillna(False).sum())
            rows += [
                {"side":side,"reason":"valid","count":count if valid else 0,"share_of_side_setups_pct":100.0 if valid and count else 0.0},
                {"side":side,"reason":"invalid_config","count":0 if valid else count,"share_of_side_setups_pct":0.0 if valid or not count else 100.0},
            ]
        return pd.DataFrame(rows)
    @classmethod
    def export(cls,frame,config,output_path:Path):
        report=cls.prepare(frame,config); output_path.parent.mkdir(parents=True,exist_ok=True); report.to_csv(output_path,index=False); return report
