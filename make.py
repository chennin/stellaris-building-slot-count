#!/usr/bin/env python3
#Copyright (c) 2024 Chris Henning
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
import shutil, subprocess, copy
from srctools import Keyvalues as kv
from pathlib import Path

cwp.workshop_path = os.path.expanduser( os.path.expandvars( "~/stellaris-workshop" ) )
cwp.mod_docs_path = os.path.expanduser( os.path.expandvars( "~/stellaris-mod" ) )
cwp.vanilla_path = os.path.expanduser( os.path.expandvars( "~/stellaris-game" ) )

MOD_NAME = "Show Building Slot Capacity"
VERSION = "5"
SUPPORTED_VERSION = "v3.14.*"
# 3 = unlisted, 2 = hidden, 1 = friends, 0 = public
VISIBILITY = 0

files = {
  "SCRIPTED_VAR_FILENAME": "mod/common/scripted_variables/fl_bslot_vars.txt",
  "VANILLA_PLANET_VIEW": "mod/interface/planet_view.gui",
  "ZZ_DEFINES": "mod/common/scripted_variables/zzzzzzzzzzzz_fl_bslot_define.txt",
}
other_mods = [
  { "name": "UIOD", "num": 1623423360, "sbsc_sid": 2963495133 },
  { "name": "BPV", "num": 1587178040, "sbsc_sid": 2963495085 },
  { "name": "PDPV", "num": 1866576239, "sbsc_sid":2963495107 },
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
def legal_scripted_var(inlist, expected):
  for ele in inlist:
    if ele.value.startswith('@'):
      return (False, f"Scripted value values cannot be other scripted values ({ele.name})")
  return success_len(inlist, expected)

# Usual uncapped
def process_uncapped_vars(inlist, outlist):
  global min_uncapped
  vals = []
  for pc in inlist:
    if pc.name in [ "pc_machine", "pc_hive", "pc_ringworld_habitable",]:
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

# Ecu Ari 1995601384
def process_var_ariphaos(inlist, outlist):
    #@cap_planet_buildings
  for ele in inlist:
    if ele.name in [ "@MAX_PLANET_BUILDING_SLOTS" ]:
      outlist.extend( cwp.stringToCW( "@buildings_ecu_ari = {}".format( ele.value ) ) )
  return outlist

# Claire Edicts 2949397716
def process_edicts_claire(inlist, outlist):
  for edict in inlist:
    if edict.name in [ "architectonic_base", "architectonic_med", "architectonic_max" ]:
      for ele in edict.getElements("modifier"):
        if ele.hasAttribute("planet_max_buildings_add"):
          cadd = int(ele.getValue("planet_max_buildings_add"))
          outlist.extend( cwp.stringToCW( f"@buildings_edict_{edict.name} = {cadd}" ) )
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
                      break
                    elif ele4.getValue("name") == "buildings_background":
                      for ele5 in ele4.getElements("containerWindowType"):
                        if ele5.getValue("name") == "title_buildings": # UIOD started nesting
                          ele5.subelements.extend(bslot_display_cw)
                          break
    outlist.append(gt)
  return outlist

def test_planet_view(inlist):
  teststring = "fl_planet_num_buildings"
  instring = cwp.CWToString(inlist)
  return (teststring in instring, f"{teststring} not found in result")

def test_recurse(ele, test, found, val):
#  print(f"{ele}")
#  print(f"    Got {ele.name} {ele.value}")
  if found == True and val != 0:
    return (found, val)
  if test["testleft"] == ele.name and test["testright"] == ele.value:
    found = True
#    print("    ->> setting Found = True")
  elif test["keywanted"] == ele.name:
    val = ele.value
#    print(f"    ->> setting val = {val}")
  if ele.hasSubelements():
#    print("    recursing")
    for sele in ele.subelements:
      (found, val) = test_recurse(sele, test, found, val)
  return (found, val)

# [ { outmostblock, innerblock, testleft, testright, keywanted, prefix, suffix }, ]
# innerblock: smallest block containing both testleft and keywanted
def look_in_block(inlist, outlist, tests):
  for outer in inlist:
    for test in tests:
#      print(f'Outer checking {outer.name} = {test["outmostblock"]}')
      if test["outmostblock"] == outer.name:
        found = False
        val = 0
        for ele in outer.subelements:
#          print(f'  Inner checking {ele.name} = {test["innerblock"]}')
          if ele.name == test["keywanted"]:
            found = True
            val = ele.value
          elif test["innerblock"] == ele.name:
              (found, val) = test_recurse(ele, test, found, val)
        if found == True and val != 0:
#          print(f'  Found {val}')
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
             legal_scripted_var,
             testargs = { "expected": 4 }
)
process_file(f"{cwp.vanilla_path}/common/planet_classes/00_planet_classes.txt", 
             files["SCRIPTED_VAR_FILENAME"],
             process_uncapped_vars,
             legal_scripted_var,
             testargs = { "expected": 4 }
)
process_file(f"{cwp.vanilla_path}/common/planet_classes/02_planet_classes_megacorp.txt",
             files["SCRIPTED_VAR_FILENAME"],
             process_ecu_vanilla,
             legal_scripted_var,
             testargs = { "expected": 1 })
process_file(f"{cwp.workshop_path}/1995601384/common/scripted_variables/~~ariphaos_patch_overridable.txt",
             files["SCRIPTED_VAR_FILENAME"],
             process_var_ariphaos,
             legal_scripted_var,
             testargs = { "expected": 1 }
)
process_file(f"{cwp.workshop_path}/2949397716/common/edicts/bs_edicts.txt",
             files["SCRIPTED_VAR_FILENAME"],
             process_edicts_claire,
             legal_scripted_var,
             testargs = { "expected": 3 }
)
process_file(f"{cwp.vanilla_path}/common/districts/02_rural_districts.txt", 
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             legal_scripted_var,
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
               "testleft": "exists",
               "testright": "owner",
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
             legal_scripted_var,
             testargs = { "expected": 6 },

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
               "outmostblock": "district_resort",
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
               {
               "outmostblock": "district_prison",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
               {
               "outmostblock": "district_slave",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
              ] }
)
process_file(f"{cwp.vanilla_path}/common/static_modifiers/18_static_modifiers_first_contact_dlc.txt", 
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             legal_scripted_var,
             testargs = { "expected": 3 },

             genargs =  { "tests": [ 
               {
               "outmostblock": "paradisiacal_habitat_science",
               "innerblock": None,
               "testleft": None,
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
               {
               "outmostblock": "paradisiacal_habitat_energy",
               "innerblock": None,
               "testleft": None,
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
               {
               "outmostblock": "paradisiacal_habitat_mining",
               "innerblock": None,
               "testleft": None,
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
              ] }
)
process_file(f"{cwp.vanilla_path}/common/static_modifiers/20_static_modifiers_astral_planes.txt",
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             legal_scripted_var,
             testargs = { "expected": 1 },

             genargs =  { "tests": [
               {
               "outmostblock": "procedural_space_modifier",
               "innerblock": None,
               "testleft": None,
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "add"
               },
              ] }
)
process_file(f"{cwp.vanilla_path}/common/districts/00_special_districts.txt", 
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             legal_scripted_var,
             testargs = { "expected": 1 },

             genargs =  { "tests": [
               {
               "outmostblock": "district_orders_demesne",
               "innerblock": "triggered_planet_modifier",
               "testleft": "has_deposit",
               "testright": "d_dimensional_manipulation_device",
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "_mult"
               },
             ] }
)
process_file(f"{cwp.vanilla_path}/common/districts/00_special_districts.txt",
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             legal_scripted_var,
             testargs = { "expected": 1 },

             genargs =  { "tests": [
               {
               "outmostblock": "district_orders_demesne",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_", "suffix": "mult"
               },
             ] }
)
process_file(f"{cwp.vanilla_path}/common/starbase_modules/00_orbital_ring_modules.txt", 
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             legal_scripted_var,
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
             legal_scripted_var,
             testargs = { "expected": 3 },
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
             ] }
)
process_file(f"{cwp.vanilla_path}/common/buildings/13_fallen_empire_buildings.txt",
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             legal_scripted_var,
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
             legal_scripted_var,
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
process_file(f"{cwp.vanilla_path}/common/deposits/11_astral_planes_deposits.txt",
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             legal_scripted_var,
             testargs = { "expected": 1 },
             genargs =  { "tests": [
               {
               "outmostblock": "d_fractal_seed",
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
             legal_scripted_var,
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
             legal_scripted_var,
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
             legal_scripted_var,
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
             legal_scripted_var,
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
# Claire 2949397716
process_file(f"{cwp.workshop_path}/2949397716/common/districts/00_urban_districts.txt",
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             legal_scripted_var,
             testargs = { "expected": 3 },
             genargs =  { "tests": [
               {
               "outmostblock": "district_industrial",
               "innerblock": "triggered_planet_modifier",
               "testleft": "is_crafter_empire",
               "testright": "yes",
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_claire_", "suffix": "_mult"
               },
               {
               "outmostblock": "district_city",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_claire_", "suffix": "add"
               },
               {
               "outmostblock": "district_crashed_slaver_ship",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_claire_", "suffix": "add"
               },
              ] }
)
process_file(f"{cwp.workshop_path}/2949397716/common/districts/01_arcology_districts.txt",
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             legal_scripted_var,
             testargs = { "expected": 1 },
             genargs =  { "tests": [
               {
               "outmostblock": "district_arcology_housing",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_claire_", "suffix": "add"
               },
              ] }
)
process_file(f"{cwp.workshop_path}/2949397716/common/districts/03_habitat_districts.txt",
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             legal_scripted_var,
             testargs = { "expected": 1 },
             genargs =  { "tests": [
               {
               "outmostblock": "district_hab_housing",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_claire_", "suffix": "add"
               },
              ] }
)
process_file(f"{cwp.workshop_path}/2949397716/common/districts/04_ringworld_districts.txt",
             files["SCRIPTED_VAR_FILENAME"],
             look_in_block,
             legal_scripted_var,
             testargs = { "expected": 1 },
             genargs =  { "tests": [
               {
               "outmostblock": "district_rw_city",
               "innerblock": "planet_modifier",
               "testleft": "planet_modifier",
               "testright": None,
               "keywanted": "planet_max_buildings_add",
               "prefix": "bslot_claire_", "suffix": "add"
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
# Copy localisation files to other langs
p = Path(f"{cwp.vanilla_path}/localisation/")
# Vanilla lang folders (not hidden folders):
langs = [x.name for x in p.iterdir() if x.is_dir() and not x.name.startswith(".") and x.name != "english" ]
srclocfile = "mod/localisation/english/fl_bslot_l_english.yml"
outloc = []
try:
  with open(srclocfile, "r") as file:
    outloc = file.readlines()
except Exception as e:
  fail(f"Could not open src loc file {srclocfile}: {e}")
for lang in langs:
  # Copy loc files
  try:
    locfilename = f"mod/localisation/{lang}/fl_bslot_l_{lang}.yml"
    if not os.path.exists(locfilename):
      os.makedirs( os.path.dirname(locfilename), exist_ok=True )
    with open(locfilename, "w", encoding='utf-8-sig') as file:
      for line in outloc:
        if line.startswith("l_"):
          file.write(f"l_{lang}:\n")
        else:
          file.write(line)
  except Exception as e:
    fail(f"Failed to write loc file {locfilename}: {e}")

# Descriptors and Other Planet Views
make_descriptor("mod/descriptor.mod")
# Copy all files from base mod to other mods
for mod in other_mods:
  mod_dir = "mod_{}".format(mod["name"])
  rsync = subprocess.run([ "rsync", "-a", "--delete", "--exclude-from", "./rsync-exclude", "mod/", mod_dir ], capture_output=True)
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
  if not os.path.exists( "{}/{}".format(mod_dir, "thumbnail.png") ):
    print("Warn: missing {}/thumbnail.png".format(mod_dir))

# Make steamcmd.txt
alldirs = copy.copy(other_mods)
alldirs.append( { "name": "", "num": 0, "sbsc_sid": 2963495048 })
desc = "New description."
try:
  with open( "steamdesc.txt", "r" ) as descfile:
    desc = descfile.read()
except Exception as e:
  fail(f"No description found {e}")

for mod in alldirs:
  outfile = "workshop/mod/steamcmd.txt"
  if mod["name"] != "":
    outfile = "workshop/mod_{}/steamcmd.txt".format( mod["name"] )
  name = f"{MOD_NAME}"
  if mod["name"] != "":
    name += " - {}".format(mod["name"])
  if not os.path.exists( os.path.dirname(outfile) ):
    os.makedirs( os.path.dirname(outfile), exist_ok=True )
  if not os.path.exists( "{}/{}".format( os.path.dirname(outfile), "loadorder.txt") ):
    print("Warn: missing {}/loadorder.txt".format( os.path.dirname(outfile) ))
  if not os.path.exists(outfile):
    shutil.copy("steamcmd-template.txt", outfile)
  file = open(outfile, 'r')
  steamcmdtxt = kv.parse(file, outfile)
  file.close()
  # Workshop files in workshop/mod*, but content files in mod*
  newpath = "{}/{}".format(os.getcwd(), os.path.dirname(outfile).replace("workshop/", "") )
  witem = steamcmdtxt.find_block("workshopitem")
  witem["contentfolder"] = witem["contentfolder"].replace("FULLMODPATH", newpath)
  witem["previewfile"] = witem["previewfile"].replace("FULLMODPATH", newpath)
  witem["title"] = name
  witem["visibility"] = f"{VISIBILITY}"
  if "publishedfileid" not in witem:
    witem["publishedfileid"] = str(mod["sbsc_sid"])
  lofilename = "{}/{}".format( os.path.dirname( outfile ), "loadorder.txt" )
  loadorder = "UNDEFINED"
  if os.path.isfile(lofilename):
    with open(lofilename, "r") as lofile:
      loadorder = lofile.read()
  moddesc = desc.replace("%LOADORDER%", loadorder)
  moddesc = moddesc.replace('"', "'")
  witem["description"] = moddesc
  try:
    with open(outfile, 'w') as file:
      for line in steamcmdtxt.export():
        # Re-interprets escapes but does not handle real unicode https://stackoverflow.com/a/24519338/6791494
        file.write( bytes(line, "utf-8").decode("unicode_escape") )
  except Exception as e:
    fail(f"Failed to write steamcmd.txt for {name} {e}")
