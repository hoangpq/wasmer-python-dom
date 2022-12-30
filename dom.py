from wasmer import engine, Store, Module, Instance, ImportObject, Type
from wasmer import Function, FunctionType
from wasmer_compiler_cranelift import Compiler
import time
import json
from html_data import html_data
from dom_types import TEXT_NODE

store = Store()

wasm_bytes = open('./dom.wasm', 'rb').read()

store = Store(engine.Universal(Compiler))
module = Module(store, wasm_bytes)
import_object = ImportObject()

now = Function(
  store,
  lambda _: round(time.time()*1000),
  FunctionType([], [Type.F64])
)

import_object.register("env", { "now": now })
instance = Instance(module, import_object)

memory = instance.exports.memory
parse = instance.exports.parse_frag
malloc = instance.exports.__wbindgen_malloc
realloc = instance.exports.__wbindgen_realloc
free = instance.exports.__wbindgen_free

def __pass_string_to_wasm(arg):
  length = len(arg)
  ptr = malloc(length);
  memory = instance.exports.memory.uint8_view()
  offset = 0

  while offset < length:
    code = ord(arg[offset])
    if code > 0x7F:
      break
    memory[ptr + offset] = code
    offset += 1

  if offset != length:
    if offset != 0:
      arg = arg[offset:]
    
    arg_bytes = bytes(arg, 'utf-8')
    new_length = offset + len(arg_bytes) * 3
    ptr = realloc(ptr, length, new_length)
    memory[ptr+offset:ptr+offset+len(arg_bytes)] = arg_bytes
    offset += len(arg)
  
  return (ptr, offset)

def parseHtml(html):
  r0 = 0; r1 = 0
  try:
    (ptr, length) = __pass_string_to_wasm(html)
    parse(8, ptr, length);

    m32 = instance.exports.memory.uint32_view()
    r0 = m32[2]; r1 = m32[3]

    reader = bytearray(instance.exports.memory.buffer)
    return reader[r0:r0 + r1].decode('utf-8-sig')
  finally:
    free(r0, r1)

class Element:
  def __init__(self, tag_name, parent_node, attributes):
    self.tag_name = tag_name
    self.parent_node = parent_node
    self.attributes = attributes or []
    self.child_nodes = []

  def __str__(self):
    return self.tag_name + '(' + str(len(self.child_nodes)) + ')'

class Text(Element):
  def __init__(self, text):
    self.text = text
    super().__init__(None, None, None)

  def __str__(self) -> str:
    return self.text

nodes = []

def nodeFromArray(data, parent) -> Element:
  child_data = data[3:]
  if data[0] == TEXT_NODE:
    return Text(data[1])
  else:
    elem = Element(data[1], parent, data[2] if len(data) > 2 else [])
    elem.child_nodes = list(map(lambda e: nodeFromArray(e, elem), child_data))
    return elem

data = json.loads(parseHtml(html_data))

node = nodeFromArray(data, None)
# print(node.child_nodes[0])

def query_selector(node, search, matches):
  matches = []
  # search class
  if len(node.attributes) > 0: 
    for [key, value] in node.attributes:
      if key == 'class' and value.find(search) >= 0:
        matches.append(node)
  for child in node.child_nodes:
    matches += query_selector(child, search, matches)
  return matches


node = query_selector(node, 'js-stale-session-flash-signed-in', [])
print(node[0].attributes)
