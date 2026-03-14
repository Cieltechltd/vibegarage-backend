import sys
from types import ModuleType


audioop = ModuleType("audioop")
audioop.error = Exception
audioop.getsample = lambda data, size, index: 0  
audioop.max = lambda data, size: 0
audioop.minmax = lambda data, size: (0, 0)

sys.modules["audioop"] = audioop