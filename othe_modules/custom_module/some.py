import os 
from pathlib import Path

from master import Submodule

Base_Folder = "Damaged Reports6"

mdl = Submodule(BASE_FOLDER=Base_Folder,headers=None)

try:
    mdl.execute_sequence()
except Exception as e:
    print(e)