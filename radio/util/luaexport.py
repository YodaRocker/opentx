#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import os
import traceback
import time
import re

PREC1 = 10
PREC2 = 100

CONSTANT_VALUE = ""
dups_cnst = []
dups_name = []
exports = []
exports_multiple = []
exports_script_outputs = []
exports_extra = []

warning = None
error = None

def checkName(name):
  global warning
  if name in dups_name:
    print "WARNING: Duplicate name %s found for constant %s" % (name, CONSTANT_VALUE)
    warning = True
  dups_name.append(name)
  if name != name.lower():
    print "WARNING:Name not in lower case %s found for constant %s" % (name, CONSTANT_VALUE)
    warning = True


def LEXP(name, description):
  # print "LEXP %s, %s" % (name, description)
  checkName(name)
  exports.append( (CONSTANT_VALUE, name, description) )

def LEXP_TELEMETRY(name, description):
  # print "LEXP %s, %s" % (name, description)
  checkName(name)
  exports.append( ("MIXSRC_FIRST_TELEM-1+"+CONSTANT_VALUE, name, description) )

def LEXP_MULTIPLE(nameFormat, descriptionFormat, valuesCount):
  # print "LEXP_MULTIPLE %s, %s, %s" % (nameFormat, descriptionFormat, valuesCount)
  for v in range(valuesCount):
    name = nameFormat + str(v)
    # print name
    checkName(name)
  exports_multiple.append( (CONSTANT_VALUE, nameFormat, descriptionFormat, valuesCount) )

def LEXP_EXTRA(name, description, value, condition = "true"):
  # print "LEXP_EXTRA %s, %s, %s, %s" % (name, description, value, condition)
  checkName(name)
  exports_extra.append( (CONSTANT_VALUE, name, description, value, condition) )
  # extra also added to normal items to enable searching
  exports.append( (CONSTANT_VALUE, name, description) )

if len(sys.argv) < 3:
  print "Error: not enough arguments!"
  print "Usage:"
  print " luaexport.py <version> <input txt> <output cpp> [<doc output>]"

version = sys.argv[1]
inputFile = sys.argv[2]
outputFile = sys.argv[3]
docFile = None
if len(sys.argv) >= 4:
  docFile = sys.argv[4]
print "Version %s" % version
print "Input file %s" % inputFile
print "Output file %s" % outputFile
if docFile:
  print "Documentation file %s" % docFile

inp = open(inputFile, "r")

while True:
  line = inp.readline()
  if len(line) == 0:
    break
  line = line.strip('\r\n')
  line = line.strip()
  #print "line: %s"  % line

  parts = line.split('LEXP')
  #print parts
  if len(parts) != 2:
    print "Wrong line: %s" % line
    continue
  cmd = 'LEXP' + parts[1]
  cnst = parts[0].rstrip(', ')
  if cnst.find('=') != -1:
    # constant contains =
    cnst = cnst.split('=')[0].strip()
  #print "Found constant %s with command: %s" % (cnst, cmd)
  try:
    CONSTANT_VALUE = cnst
    # if CONSTANT_VALUE in dups_cnst:
    #   print "WARNING: Duplicate CONSTANT_VALUE found: %s" % CONSTANT_VALUE
    #   warning = True
    #   continue
    # dups_cnst.append(CONSTANT_VALUE)
    # print cmd
    eval(cmd)
  except:
    print "ERROR: problem with the definition: %s" % line
    traceback.print_exc()
    error = True

inp.close()

out = open(outputFile, "w")

out.write("//This file was generated by luaexport.py script on %s for OpenTX version %s\n\n\n" 
            % ( time.asctime(), version))

header = """
struct LuaSingleField {
  uint16_t id;
  const char * name;
  const char * desc;
};

struct LuaMultipleField {
  uint16_t id;
  const char * name;
  const char * desc;
  uint8_t count;
};

"""
out.write(header)

out.write("""
// The list of Lua fields
// this aray is alphabetically sorted by the second field (name)
const LuaSingleField luaSingleFields[] = { 
""")
exports.sort(key = lambda x: x[1])  #sort by name
data = ["  {%s, \"%s\", \"%s\"}" % export for export in exports]
out.write(",\n".join(data))
out.write("\n};\n\n")
print "Generated %d items in luaFields[]" % len(exports)

out.write("""
// The list of Lua fields that have a range of values
const LuaMultipleField luaMultipleFields[] = {
""")
data = ["  {%s, \"%s\", \"%s\", %d}" % export for export in exports_multiple]
out.write(",\n".join(data))
out.write("\n};\n\n")
print "Generated %d items in luaMultipleFields[]" % len(exports_multiple)

#code generation for extra fields
case = """    case %s:
      if (%s) {
        lua_pushnumber(L, %s);
        return 1;
      }
      break;"""
case_clauses = [case % (cnst, condition, value) for (cnst, name, description, value, condition) in exports_extra]
case_body = "\n".join(case_clauses)
func_body = """
extern lua_State *L;

// The handling of extra Lua fields that are not
// accessible by the getValue()
static int luaGetExtraValue(int src)
{
  switch (src) {
%s
  }
  return 0;
}

""" % case_body
out.write(func_body)
print "Generated %d conditions in luaGetExtraValue()" % len(exports_extra)
out.close()

if docFile:
  #prepare fields
  all_exports = [(name, desc) for (id, name, desc) in exports]
  for (id, nameFormat, descriptionFormat, valuesCount) in exports_multiple:
    for v in range(1, valuesCount + 1):
      name = nameFormat + str(v)
      desc = descriptionFormat % v
      all_exports.append( (name, desc) )
  #natural sort by field name
  convert = lambda text: int(text) if text.isdigit() else text 
  alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key[0]) ] 
  all_exports.sort(key = alphanum_key)

  out = open(docFile, "w")
  out.write("Alphabetical list of Lua fields for OpenTX version %s\n\n\n" % version)
  FIELD_NAME_WIDTH = 25
  out.write("Field name%sField description\n" % (' '*(FIELD_NAME_WIDTH-len('Field name'))))
  out.write("----------------------------------------------\n")
  data = ["%s%s%s" % (name, ' '*(FIELD_NAME_WIDTH-len(name)) , desc) for (name, desc) in all_exports]
  out.write("\n".join(data))
  out.write("\n")

  out.close()

if warning:
  sys.exit(1)
elif error:
  os.remove(outputFile)
  sys.exit(2)
sys.exit(0)
