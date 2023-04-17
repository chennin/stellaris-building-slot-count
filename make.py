#!/usr/bin/env python3
#Copyright (c) 2023 Chris Henning
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.

import sys, os, io
import Diagraphers_Stellaris_Mods.cw_parser_2 as cwp
import shutil, subprocess

cwp.workshop_path = os.path.expanduser( os.path.expandvars( "~/stellaris-workshop" ) )
cwp.mod_docs_path = os.path.expanduser( os.path.expandvars( "~/stellaris-mod" ) )
cwp.vanilla_path = os.path.expanduser( os.path.expandvars( "~/stellaris-game" ) )

MOD_NAME = "Show Building Slot Capacity"
VERSION = "1"
SUPPORTED_VERSION = "3.7.*"

files = {
  "SCRIPTED_VAR_FILENAME": "mod/common/scripted_variables/fl_bslot_vars.txt",
  "VANILLA_PLANET_VIEW": "mod/interface/planet_view.gui",
  "ZZ_DEFINES": "mod/common/scripted_variables/zzzzzzzzzzzz_fl_bslot_define.txt",
}
other_mods = [
  { "name": "UIOD", "num": 1623423360 },
  { "name": "BPV", "num": 1587178040 },
]
min_uncapped = 0
bslot_display = """
					effectButtonType = {{
						name = "fl_planet_num_buildings"
						spriteType = "GFX_fl_button_48_24"

						position = {{ x = {pos_x} y = {pos_y} }}
						orientation = upper_right
						buttonFont = {font}
						
						buttonText = "$fl_button_text$"
						effect = fl_num_building_effect
					}}
"""

def fail(message):
  print(f"{message}", file=sys.stderr)
  sys.exit(1)

def clear_files():
  global files
  for mod in other_mods:
    files[ f"{mod['name']}_PLANET_VIEW" ] = f"mod_{mod['name']}/interface/planet_view.gui" 
  for file in files:
    try:
      os.unlink(files[file])
    except FileNotFoundError as e:
      pass
#      print(e)
    except Exception as e:
      fail(e)

def make_descriptor( path, mod = { "name": None, "num": None } ):
  outlines = []
  try:
    with open("mod/descriptor.mod", "r") as file:
      lines = file.readlines()
  except Exception as e:
    fail(e)

  for line in lines:
    match line[:4]:
      case "name":
        name = MOD_NAME
        if mod["name"] is not None:
          name += f" - {mod['name']}"
        line = f"name=\"{name}\"\r\n"

      case "vers":
        line = f"version=\"{VERSION}\"\r\n"
      case "supp":
        line = f"supported_version=\"{SUPPORTED_VERSION}\"\r\n"
    outlines.append(line)

  try:
    with open(path, "w") as file:
      file.writelines(outlines)
  except Exception as e:
    fail(e)

def process_file(infilename, outfilename, makefunc, testfunc, genargs = {}, testargs = {}):
  try:
    cw = cwp.fileToCW(infilename)
  except Exception as e:
    fail(e)

  ele_to_add = makefunc(cw, [], **genargs)
  diditwork = testfunc(ele_to_add, **testargs)
  if not diditwork[0]:
    fail(f"Error parsing {infilename}: {diditwork[1]}")
    
  try:
    if not os.path.exists(outfilename):
      os.makedirs( os.path.dirname(outfilename), exist_ok=True )
    with io.open(outfilename, 'a', newline="\r\n") as outfile:
      outfile.write(f"#\n")
      outfile.write(cwp.CWToString(ele_to_add))
      outfile.write("\n")
  except Exception as e:
    raise
    fail(e)

# Capital vars
# Decide what to keep of the list
def process_capital_vars(inlist, outlist):
  for ele in inlist:
    if ele.name.startswith("@buildings"):
      outlist.append(ele)
  return outlist
# Returns a tuple indicating the file was processed correctly, and a message if not
def success_len(inlist, expected):
  length = len(inlist)
  return (length == expected, f"List length {length} doesn't match expected {expected}")

# Usual uncapped
def process_uncapped_vars(inlist, outlist):
  global min_uncapped
  vals = []
  for pc in inlist:
    if pc.name in [ "pc_machine", "pc_hive", "pc_ringworld_habitable" ]:
      for ele in pc.getElements("modifier"):
        if ele.hasAttribute("planet_max_buildings_add"):
          vals.append( int(ele.getValue("planet_max_buildings_add")) )
          outlist.extend( cwp.stringToCW( "@buildings_{} = {}".format( pc.name, ele.getValue("planet_max_buildings_add") ) ) )
  # Minimum (default) to add for uncapped
  min_uncapped = min(vals)
  outlist.extend( cwp.stringToCW( "@buildings_uncapped = {}".format( min_uncapped ) ) )
  return outlist

# Ecu vanilla
def process_ecu_vanilla(inlist, outlist):
  for pc in inlist:
    if pc.name in [ "pc_city" ]:
      for ele in pc.getElements("modifier"):
        if ele.hasAttribute("planet_max_buildings_add"):
          outlist.extend( cwp.stringToCW( "@buildings_{} = {}".format( pc.name, ele.getValue("planet_max_buildings_add") ) ) )
  return outlist

# Ecu Ari
def process_ecu_ariphaos(inlist, outlist):
  for pc in inlist:
    if pc.name in [ "pc_city" ]:
      for ele in pc.getElements("modifier"):
        if ele.hasAttribute("planet_max_buildings_add"):
          ari_diff = int(ele.getValue("planet_max_buildings_add")) - min_uncapped
          outlist.extend( cwp.stringToCW( f"@buildings_ecu_ari = {ari_diff}" ) )
  return outlist

def process_planet_view(inlist, outlist, mod_name) :
  poscw = cwp.fileToCW("mod/common/scripted_variables/fl_position_vars.txt")
  posvars = [ k for k in poscw if mod_name in k.name ]
  for posvar in posvars:
    outlist.append( posvar )
  bslot_display_cw = cwp.stringToCW( bslot_display.format(pos_x = f"@fl_pos_{mod_name}_x", pos_y = f"@fl_pos_{mod_name}_y", font = f"@fl_font_{mod_name}") )
#  print(bslot_display_cw)
  for gt in inlist:
    if gt.name == "guiTypes":
      for ele in gt.getElements("containerWindowType"):
        if ele.getValue("name") == "planet_view":
          for ele2 in ele.getElements("containerWindowType"):
            if ele2.getValue("name") == "summary_window":
              for ele3 in ele2.getElements("containerWindowType"):
                if ele3.getValue("name") == "colonized_planet_window":
                  for ele4 in ele3.getElements("containerWindowType"):
                    if ele4.getValue("name") == "title_buildings":
                      ele4.subelements.extend(bslot_display_cw)
    outlist.append(gt)
  return outlist

def test_planet_view(inlist):
  teststring = "fl_planet_num_buildings"
  instring = cwp.CWToString(inlist)
  return (teststring in instring, f"{teststring} not found in result")

def test_recurse(ele, test, found, val):
#  print(f"{ele}")
#  print(f"{ele.name} {ele.value}")
  if found == True and val != 0:
    return (found, val)
  if test["testleft"] == ele.name and test["testright"] == ele.value:
    found = True
#    print("->> setting Found = True")
  elif test["keywanted"] == ele.name:
    val = ele.value
#    print(f"->> setting val = {val}")
  if ele.hasSubelements():
#    print("recursing")
    for sele in ele.subelements:
      (found, val) = test_recurse(sele, test, found, val)
  return (found, val)

# [ { outmostblock, innerblock, testleft, testright, keywanted, prefix, suffix }, ]
# innerblock: smallest block containing both testleft and keywanted
def look_in_block(inlist, outlist, tests):
  for outer in inlist:
    for test in tests:
      if test["outmostblock"] == outer.name:
        found = False
        val = 0
        for ele in outer.subelements:
          if test["innerblock"] == ele.name:
              (found, val) = test_recurse(ele, test, found, val)
        if found == True and val != 0:
          name = test["testright"]
          if name == "yes":
            name = test["testleft"]
          if name == None:
            name = ""
          outlist.extend( cwp.stringToCW( "@{}{}_{}{} = {}".format(test["prefix"], test["outmostblock"], name, test["suffix"], val) ) )
  return outlist

#  " [ { "outmostblock":, "keywanted": } ]
def look_in_defines(inlist, outlist, tests):
  for outer in inlist:
    for test in tests:
      if test["outmostblock"] == outer.name:
        for ele in outer.subelements:
          if test["keywanted"] == ele.name:
            outlist.extend( cwp.stringToCW( "@{} = {}".format(ele.name, ele.value) ) )
  return outlist

clear_files()
process_file(f"{cwp.vanilla_path}/common/buildings/00_capital_buildings.txt",
             files["SCRIPTED_VAR_FILENAME"],
             process_capital_vars,
             success_len,
             testargs = { "expected": 4 }
)
process_file(f"{cwp.vanilla_path}/common/planet_classes/00_planet_classes.txt", 
             files["SCRIPTED_VAR_FILENAME"],
             process_uncapped_vars,
             success_len,
             testargs = { "expected": 4 }
)
process_file(f"{cwp.vanilla_path}/common/planet_classes/02_planet_classes_megacorp.txt",
             files["SCRIPTED_VAR_FILENAME"],
             process_ecu_vanilla,
             success_len,
             testargs = { "expected": 1 })
process_file(f"{cwp.workshop_path}/1995601384/common/planet_classes/02_planet_classes_megacorp.txt",
             files["SCRIPTED_VAR_FILENAME"],
             process_ecu_ariphaos,
             success_len,
             testargs = { "expected": 1 }
)
process_file(f"{cwp.vanilla_path}/common/districts/02_rural_districts.txt", 
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             success_len,
             testargs = { "expected": 2 },

             genargs =  { "tests": [
               {
               "outmostblock": "district_farming",
               "innerblock": "triggered_planet_modifier",
               "testleft": "has_valid_civic",
               "testright": "civic_agrarian_idyll",
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "_mult"
               },
               {
               "outmostblock": "district_mining_uncapped",
               "innerblock": "triggered_planet_modifier",
               "testleft": "has_origin",
               "testright": "origin_subterranean",
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "_mult"
               } ]
              }
#             genargs = { "test": [ 
#                      ("district_farming", "has_valid_civic", "civic_agrarian_idyll"),
#                      ("district_mining_uncapped", "has_origin", "origin_subterranean")
#             ] },
)
process_file(f"{cwp.vanilla_path}/common/districts/00_urban_districts.txt", 
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             success_len,
             testargs = { "expected": 3 },

             genargs =  { "tests": [ 
               {
               "outmostblock": "district_industrial",
               "innerblock": "triggered_planet_modifier",
               "testleft": "is_crafter_empire",
               "testright": "yes",
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "_mult"
               },
               {
               "outmostblock": "district_city",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
               {
               "outmostblock": "district_crashed_slaver_ship",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
              ] }
)
process_file(f"{cwp.vanilla_path}/common/districts/00_special_districts.txt", 
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             success_len,
             testargs = { "expected": 1 },

             genargs =  { "tests": [ { 
               "outmostblock": "district_orders_demesne",
               "innerblock": "triggered_planet_modifier",
               "testleft": "has_deposit",
               "testright": "d_dimensional_manipulation_device",
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "_mult"
             } ] }
#             genargs = { "test": [
#                    ("district_orders_demesne", "has_deposit", "d_dimensional_manipulation_device")
#             ] }
)
process_file(f"{cwp.vanilla_path}/common/starbase_modules/00_orbital_ring_modules.txt", 
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             success_len,
             testargs = { "expected": 1 },
             genargs =  { "tests": [ { 
               "outmostblock": "orbital_ring_habitation",
               "innerblock": "triggered_planet_modifier",
               "testleft": "holding",
               "testright": "holding_orbital_assembly_complex",
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "_mult"
             } ] }
)
process_file(f"{cwp.vanilla_path}/common/buildings/00_capital_buildings.txt",
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             success_len,
             testargs = { "expected": 7 },
             genargs =  { "tests": [ 
               { 
               "outmostblock": "building_imperial_capital",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
               { 
               "outmostblock": "building_resort_major_capital",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
               { 
               "outmostblock": "building_slave_major_capital",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
               { 
               "outmostblock": "building_slave_capital",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
               { 
               "outmostblock": "building_resort_capital",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
               { 
               "outmostblock": "building_hab_capital",
               "innerblock": "triggered_planet_modifier",
               "testleft": "has_ascension_perk",
               "testright": "ap_voidborn",
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "_add"
               },
               { 
               "outmostblock": "building_hab_capital",
               "innerblock": "triggered_planet_modifier",
               "testleft": "has_active_tradition",
               "testright": "tr_prosperity_void_works",
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "_add"
               },
             ] }
)
process_file(f"{cwp.vanilla_path}/common/buildings/13_fallen_empire_buildings.txt",
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             success_len,
             testargs = { "expected": 1 },
             genargs =  { "tests": [
               {
               "outmostblock": "building_fe_xeno_zoo",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
             ] }
)
process_file(f"{cwp.vanilla_path}/common/deposits/01_blocker_deposits.txt",
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             success_len,
             testargs = { "expected": 2 },
             genargs =  { "tests": [ 
               { 
               "outmostblock": "d_venomous_insects",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
               { 
               "outmostblock": "d_rotten_soil",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
             ] }
)
process_file(f"{cwp.vanilla_path}/common/technology/00_soc_tech.txt",
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             success_len,
             testargs = { "expected": 2 },
             genargs =  { "tests": [ 
               { 
               "outmostblock": "tech_planetary_infrastructure_1",
               "innerblock": "modifier",
               "testleft": "modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
               { 
               "outmostblock": "tech_planetary_infrastructure_2",
               "innerblock": "modifier",
               "testleft": "modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
             ] }
)
process_file(f"{cwp.vanilla_path}/common/governments/civics/00_civics.txt",
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             success_len,
             testargs = { "expected": 1 },
             genargs =  { "tests": [ 
               { 
               "outmostblock": "civic_functional_architecture",
               "innerblock": "modifier",
               "testleft": "modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
             ] }
)
process_file(f"{cwp.vanilla_path}/common/traditions/00_adaptability.txt",
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             success_len,
             testargs = { "expected": 1 },
             genargs =  { "tests": [ 
               { 
               "outmostblock": "tr_adaptability_adaptive_ecology",
               "innerblock": "modifier",
               "testleft": "modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
             ] }
)
# Storage Building and District 2762644349
process_file(f"{cwp.workshop_path}/2762644349/common/districts/storage_districts.txt",
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             success_len,
             testargs = { "expected": 1 },
             genargs =  { "tests": [ 
               { 
               "outmostblock": "district_storage",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
             ] }
)
process_file(f"{cwp.vanilla_path}/common/defines/00_defines.txt",
             files["ZZ_DEFINES"],
             look_in_defines,
             success_len,
             testargs = { "expected": 1 },
             genargs = { "tests": [
               {
               "outmostblock": "NGameplay",
               "keywanted": "MAX_PLANET_BUILDING_SLOTS",
               },
             ] }
)
# Vanilla Planet View
process_file(f"{cwp.vanilla_path}/interface/planet_view.gui",
             files["VANILLA_PLANET_VIEW"],
             process_planet_view,
             test_planet_view,
             testargs = {},
             genargs = { "mod_name": "van" },
)
# Descriptors and Other Planet Views
for mod in other_mods:
  mod_dir = "mod_{}".format(mod["name"])
#  shutil.copytree("mod", mod_dir, dirs_exist_ok=True, ignore = shutil.ignore_patterns("planet_view.gui"))
  rsync = subprocess.run([ "rsync", "-a", "--delete", "mod/", mod_dir ], capture_output=True)
  if rsync.returncode != 0:
    fail(f"Copying mods had an error: {rsync.stderr}")
  make_descriptor(f"{mod_dir}/descriptor.mod".format(mod["name"]), mod = mod)

  process_file(f"{cwp.workshop_path}/{mod['num']}/interface/planet_view.gui",
             f"{mod_dir}/interface/planet_view.gui",
             process_planet_view,
             test_planet_view,
             testargs = {},
             genargs = { "mod_name": mod["name"] },
  )
