"""
Backward-compatibility shim.
External code that does `from src.engine import RichgoCortexEngine`
continues to work without modification.

New code should import directly from the sub-modules:
  from src.core.engine      import RichgoCortexEngine
  from src.analytics.spatial  import SUPPLY_SPILLOVER
  from src.analytics.temporal import REGIONAL_INCOME_MAN_WON
"""
from src.core.engine         import RichgoCortexEngine          # noqa: F401
from src.analytics.spatial   import SUPPLY_SPILLOVER            # noqa: F401
from src.analytics.temporal  import REGIONAL_INCOME_MAN_WON    # noqa: F401

__all__ = ["RichgoCortexEngine", "SUPPLY_SPILLOVER", "REGIONAL_INCOME_MAN_WON"]
