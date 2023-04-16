#!/usr/bin/env python3

import sys, os
import Diagraphers_Stellaris_Mods.cw_parser_2 as cwp

cwp.workshop_path = os.path.expanduser( os.path.expandvars( "~/stellaris-workshop" ) )
cwp.mod_docs_path = os.path.expanduser( os.path.expandvars( "~/stellaris-mod" ) )
cwp.vanilla_path = os.path.expanduser( os.path.expandvars( "~/stellaris-game" ) )

if len(sys.argv) <= 1:
  print("Provide a filename")
  sys.exit(1)

def recurse(ele, top_level, file):
  if ele.name == "planet_max_buildings_add":
    path = file.replace( os.path.expanduser('~/stellaris-game/'), '' )
    print(f"{path}\t{top_level}\t{ele.name} = {ele.value}")
  if ele.hasSubelements():
    for sele in ele.subelements:
      recurse(sele, top_level, sys.argv[1])

cw = cwp.fileToCW(sys.argv[1])
for ele in cw:
  top_level = ele.name
  if ele.hasSubelements:
    recurse(ele, top_level, sys.argv[1])
