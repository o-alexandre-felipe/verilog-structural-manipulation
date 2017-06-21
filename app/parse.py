import re;

module_re = re.compile('\\bmodule\\b.*?\\bendmodule\\b', re.MULTILINE | re.DOTALL);

module_parts_re = re.compile("""
\\bmodule\\b\s*
  ([a-zA-Z_][a-zA-Z0-9_]*) # module name
  \s*(\#\s*\(.*?\))?  # parameters are serparated by commas, 
                      # the port list is separated with spaces
  \s*\((.*?)\)\s*;    # module port list
  (.*?)            # module body
  \\bendmodule\\b
""", re.MULTILINE | re.DOTALL | re.VERBOSE)

comments = re.compile('//.*?$|/\*.*?\*', re.MULTILINE | re.DOTALL | re.VERBOSE)

instance_re = re.compile("""
(\\b[a-zA-Z_][a-zA-Z0-9_]*\\b) # module name
\s*(\#\s*\(.*?\))? # parameter list this works only because of the ';' separating each instance
\s*?(\\b[a-zA-Z_][a-zA-Z0-9_]*\\b) # instance name
\s*?[(](.*?)[)]\s*; # port connections""", re.MULTILINE | re.DOTALL | re.VERBOSE)

""" Capture signal declarations
  <s> name;
  s [.:.] name;
"""
signal_re = lambda s, sep = ';': re.compile("""
((\\b%s\\b)\s*(\\[.*?:.*?\\])?\s*?(\\b[_a-zA-Z].*?\\b)\s*)%s
""" % (s, sep), re.MULTILINE | re.DOTALL | re.VERBOSE);

""" Capture different forms of parameter 
  parameter name = <>
  parameter <type> name = <>
  parameter <type> [range] name = <>

  type is restricted to lowercase words. """
parameter_re = re.compile("""
parameter
\\b\s*?(?:[a-z]*?)         # type
(?:\s*\[.*?\])?\s*?        # range
(\\b[_A-Za-z].*?\\b)\s*    # name
\\=\s*([^,;]*)              # value
""",  re.MULTILINE | re.DOTALL | re.VERBOSE)
v95 = False;


input_re = signal_re('input\\b\\s*(?:\\bwire\\b)?', '[;,]');
output_re = signal_re('output\\b\\s*(?:\\bwire\\b)?','[;,]');
inout_re = signal_re('inout\\b\\s*(?:\\bwire\\b)?', '[;,]');
wire_re = signal_re('wire\\b');

named_connection_re = re.compile("\s*[.](\\b[a-zA-Z_][a-zA-Z0-9_]*\\b)\s*\\((.*?)\\)\s*", 
   re.MULTILINE | re.DOTALL | re.VERBOSE);
name_re = re.compile("\\b(?<!')([_a-zA-Z][a-zA-Z0-9_]*?|\\\\.*?\s)\\b");






class signal_declaration:
  def __init__(self, src, _class, _range, _name):
    self.src = src;
    self._class = _class.strip();
    self._range = _range.strip();
    self.name = _name.strip();
  def __str__(self):
    if(self.src != None):
      return self.src;
    else:
      return self._class + ' ' + self._range + ' ' + self.name;
  def astype(self, _class):
    return signal_declaration(None, _class, self._range, self.name);
  def renamed(self, new_name):
    return signal_declaration(None, self._class, self._range, new_name);
  def translate_parameters(self, param_translation):
    """ Given a dictionary with parameters update the range 
        if any parameter is found """
    def trans(g):
      token = g.group(1);
      if(token in param_translation):
        return param_translation[token];
      else:
        return token;
    if(self.src == None):
      self._range = name_re.sub(trans, self._range);
    else:
      self.src = name_re.sub(trans, self.src);





class module_declaration:
  def __init__(self, s, src_file = None):
    r = module_parts_re.match(s);
    self.src = s;
    self.src_file = src_file;
    self.body_changed = False;
    self.num_instances = 0;
    if(r == None):
      raise "Invalid string for a module definition";
    else:
      self.num_insts = 0;
      self.name = r.group(1);
      self.ports_string = r.group(3);
      self.ports = [p.strip() for p in r.group(3).split(',')];
      self.body_src = r.group(4);
      self.find_inputs();
      self.find_outputs();
      self.find_wires();
      self.find_inouts();
      self.instances = {};
      self.sub_blocks = {};
      self.parameters = {};
      for p in parameter_re.findall(self.body_src):
        self.parameters[p[-2]] = p[-1].strip();
      if(r.group(2) != None):
        sp = r.group(2);
        sp = sp[sp.index('('):len(sp) - sp[::-1].index(')') - 1];

        for p in parameter_re.findall(sp):
          self.parameters[p[-2]] = p[-1].strip();

  def get_signal(self, name):
    """ Return a signal by it's name regardless of its type.  """
    if(name in self.outputs):
      return self.outputs[name];
    if(name in self.inputs):
      return self.inputs[name];
    if(name in self.wires):
      return self.wires[name];
    if(name in self.inouts):
      self.inouts[name];

  def get_signal_direction(self, signal):
    """ Determine the type of a signal, 
        based on the dictionary it is present. """
    if(signal in self.outputs):
      return 'output';
    elif(signal in self.inputs):
      return 'input';
    elif(signal in self.wires):
      return 'wire';
    elif(signal in self.inouts):
      return 'inout';
    else:
      return None;

  def find_wires(self):
    """ Using a regular expression find wires and store them
        in a dictionary wires """
    self.wires = {};
    for w in wire_re.findall(self.body_src) + wire_re.findall(self.ports_string + ','):
      self.wires[w[3]] = signal_declaration(*w);

  def find_inputs(self):
    """ Using a regular expression find inputs and store them
        in a dictionary inputs """
    self.inputs = {};
    for w in input_re.findall(self.body_src) + input_re.findall(self.ports_string + ','):
      self.inputs[w[3]] = signal_declaration(*w);

  def find_outputs(self):
    """ Using a regular expression find outputs and store them
        in a dictionary outputs """
    self.outputs = {};
    for w in output_re.findall(self.body_src) + output_re.findall(self.ports_string + ','):
      self.outputs[w[3]] = signal_declaration(*w);

  def find_inouts(self):
    """ Using a regular expression find inouts and store them
        in a dictionary inouts """
    self.inouts = {};
    for w in inout_re.findall(self.body_src) + inout_re.findall(self.ports_string + ','):
      self.inouts[w[3]] = signal_declaration(*w);
  
  def __str__(self):
    if(self.body_changed): 
      sm = "module " + self.name;
      sm += self.parameter_declaration_v2001();
      sm += '\n(\n' + self.port_list_string() + '\n);\n  '
      sm += self.parameter_declaration_v95();
      sm += self.signal_declarations_string();
      sm += ''.join(['\n  ' + str(e).strip() + ';' for e in self.instances.values()])
      sm += '\n\nendmodule\n\n'
      return sm;
    else:
      return self.src + '\n';

  def link(self, dict):
    """ This routine find instances in the module body
        and replace when possible with an object representing
        that instance, based on the available modules, passed
        via dict argument.
    """
    insts = instance_re.findall(self.body_src);
    for i in insts:
      s = i[0] + ' ' + i[1] + ' ' + i[2] + '(' + i[3] + ')';
      if(i[0] in dict):
        b = instance_declaration(src = s, ref = dict[i[0]], parent = self, name = i[2]);
        self.instances[i[2]] = b;
        self.sub_blocks[i[2]] = b;
      else:
        b = instance_declaration(src = s, ref = None, parent = self, name = i[2]);
        self.instances[i[2]] = b;


  def move_to_chiplet(self, sub_blocks, chiplet_name, chiplet_instname = None):
    
    c = chiplet_declaration(chiplet_name, self);
    if(chiplet_instname == None):
      chiplet_instname = chiplet_name;
    for b in sub_blocks:
      if(b in self.sub_blocks):
        """ Without the variable tmp the RTL is corrupted
            and it takes longer to execute """
        tmp = self.sub_blocks[b]; 
        c.include_instance(tmp)
        del self.sub_blocks[b];
        del self.instances[b];
      else:
        print "%s not found in %s" % (b, self.name);
    self.sub_blocks[chiplet_name] = c.get_instanciation(parent = self, name = chiplet_instname);
    self.instances[chiplet_name] = self.sub_blocks[chiplet_name];
    self.body_changed = True;
    return c;
  def dissolve_sub_block(self, block_name, prefix = ''):
    if(block_name in self.sub_blocks):
      new_wires, new_insts = self.sub_blocks[block_name].get_dissolved_content(prefix = prefix);
      for w in new_wires:
        if(w in self.wires):
          raise 'The wire %s already exists, aborted dissolving.' % w;
      for i in new_insts:
        if(i in self.instances):
          raise 'The instance %s already exists, aborted dissolving.' % i;
      """ Declares the required wires """
      for w in new_wires:
        self.wires[w] = new_wires[w];
      """ Declare the instances from inside the subblock """
      for i in new_insts:
        ii = new_insts[i];
        if(ii.ref != None):
          self.sub_blocks[i] = ii;
        self.instances[i] = ii;
      """ Remove the sub block from the instances """
      del self.sub_blocks[block_name];
      del self.instances[block_name];
      self.body_changed = True;
    else:
      raise 'sub_block not found, nothing to be dissolved.'

  def hierarchy_tree(self, instname, f = lambda entity, inst_name: [inst_name]):
    """ Create an hierarchical list containing some property
        of each instance, returnded by a function f."""
    r = [f(self, instname), []];
    for sb in self.sub_blocks:
      r[1].append(self.sub_blocks[sb].ref.hierarchy_tree(sb, f))
    return r; 
  def parameter_declaration_v2001(self):
    if(v95):
      return '';
    else:
      if(len(self.parameters) == 0):
        return '';
      else:
        plist = ['parameter %s = %s' % (k,v) for k,v in 
                 zip(self.parameters.keys(), self.parameters.values())];
        return "#(\n     " + (',\n  '.join(plist)) + ')';
  def parameter_declaration_v95(self):
    if(v95):
      plist = ['\n   parameter %s = %s;' (k,v) for k,v in 
                   zip(self.parameters.keys(), self.parameters.values())];
      return ''.join([plist]);
    else:
      return '';
  def signal_declarations_string(self):
    """ Verilog 1995 defines the types of the ports in the module body
        after verilog 2001 only the wires are declared in the module
        and the ports are fully declared in the port list. """
    sm = '';
    if(v95):
      sm = '\n// Input declarations\n'
      sm += '\n'.join([str(w) + ';' for w in self.inputs.values()]) 
      sm += '\n// Output declarations\n'
      sm += '\n'.join([str(w) + ';' for w in self.outputs.values()])
      sm += '\n// INOUT declarations\n'
      sm += '\n'.join([str(w) + ';' for w in self.inouts.values()])
    sm += '\n// Wire declarations\n';
    sm += '\n'.join([str(w) + ';' for w in self.wires.values()])
    return sm + '\n\n';

  def port_list_string(self):
    """ The module portlist declares ports that will be present in 
        the module, after verilog 2001 it also defines the type of the port """
    sm = '';
    if(v95):
      sm += '  ' + (',\n  '.join(self.inputs.keys() + self.outputs.keys() + self.inouts.keys()));
    else:
      sm += ',\n'.join([str(w) for w in self.inputs.values()] +
                       [str(w) for w in self.outputs.values()] + 
                       [str(w) for w in self.inouts.values()]);
    return sm;
  def stub(self):
    """ Write the same HDL struct without the instances 
        whose corresponding modules were not declared """
    sm = "module " + self.name + '\n(\n' + ',\n '.join(self.ports) + '\n);\n  '
    for p in self.parameters:
      sm += '\n  parameter %s = %s;' % (p, self.parameters[p]);
    sm += self.signal_declarations_string();
    sl = [];
    for e in self.sub_blocks.values():
        sl.append(str(e) + ';');
    sm += '\n  '.join(sl);
    sm += '\nendmodule\n'
    return sm;
















class instance_declaration:
  def __init__(self, src, ref = None, parent = None, 
               name = None, params = None, connections = None):
    if((name == None) or (params == None) or (connections == None) or (ref == None)):
      g = instance_re.match(src + ';');
      if(g != None):
        self.params = g.group(2);
        self.name = g.group(3);
        self.connections = g.group(4);
        self.ref_name = g.group(1);
    else:
      self.src = src;
      self.name = name;
      self.params = params;
      self.connections = connections;
    self.src = src;
    if(ref != None):
      self.ref = ref;
      ref.num_instances += 1;
      self.ref_name = self.ref.name;
    else:
      self.ref = None;
    self.parent = parent;
  def __str__(self):
    return self.src;
  def stub(self):
    if(self.ref != None):
      return self.src;
  def get_port_connections_strings(self):
    """ Retrieve the text that defines each connection """
    if(self.connections == None):
      return [];
    pl = [s for s in named_connection_re.findall(self.connections)];
    return pl;
  def get_parameter_connections_strings(self):
    if(self.params == None):
      return [];
    pl = [s for s in named_connection_re.findall(self.params)];
    return pl;

  def get_connections(self):
    """
      return a list of the signals connected to this instance
      with the directions of the port to which it is connected
        - inout is dominant over input and ouput.
        - output is dominant over input.
      This provide the directions to the ports in a module
      that whould encapsulate this instance as is.
    """    
    outputs = {};
    inputs = {};
    inouts = {};
    pl = self.get_port_connections_strings();
    
    """ Create a list of ports from signals connected to the ports """
    for i in range(0, len(pl)):
      """ No support for ordered connections yet """
      names = [s.strip() for s in name_re.findall(pl[i][1])];
      """ Process an named connection """
      direction = self.ref.get_signal_direction(pl[i][0].strip());
      """ Add the signal to the correct bin """
      if(direction == 'output'):
        for n in names:
          s = self.parent.get_signal(n);
          if(s != None):
            outputs[n] = s.astype('output');
      elif(direction == 'input'):
        for n in names:
          s = self.parent.get_signal(n);
          if(s != None):
            inputs[n] = s.astype('input');
      elif(direction == 'inout'):
        for n in names:
          s = self.parent.get_signal(n);
          if(s != None):
            inouts[n] =  s.astype('inout');
      
    """ Remove inputs and outputs that also appears as inout. """
    for p in inputs:
      if ((p in outputs) or (p in inouts)):
        del inputs[p];
    """ Remove inputs that also appear as output. """
    for p in outputs:
      if (p in inouts):
        del outputs[p];
    return inputs, outputs, inouts;

  def reconnect(self, signal_translation = {}, parameter_translation = {}, parent = None, prefix = ''):
    def translate_signals(m):
      token = m.group(1);
      if(token in signal_translation):
        return signal_translation[token];
      elif(token in parameter_translation):
        return parameter_translation[token];
      else:
        return prefix + token;

    def translate_named_connection(m):
      s = '\n    .' + m.group(1) + '(';
      s += name_re.sub(translate_signals, m.group(2)) + ')'
      return s;
    s = self.ref_name;
    if(self.params != None):
      s += named_connection_re.sub(translate_named_connection, self.params);
    s +=' ' + prefix + self.name + '('; # instance name (now with prefix)
    if(self.connections != None):
      s += named_connection_re.sub(translate_named_connection, self.connections);
    s += ')'
    # Keep the same module as the parent of this instance.
    newinst = instance_declaration(src = s, ref = self.ref,
                 parent = parent, name = prefix + self.name);
    return newinst;
  def get_resolved_parameters(self):
    param_translations = {};
    for p in self.ref.parameters:
      param_translations[p] = '%s' % self.ref.parameters[p];
    if(self.params != None):
      pl = named_connection_re.findall(self.params);
      for p,r in pl:
        param_translations[p] = '%s' % r;
    return param_translations;

  def get_dissolved_content(self, prefix):
    if(self.ref == None):
      return None;
    my_params = self.get_resolved_parameters();
    """ Return a list of connected ports """
    p = self.get_port_connections_strings();
    my_ports = {};
    for u in p:
      my_ports[u[0]] = "%s" % u[1];
    new_wires = {};
    for w in self.ref.wires:
      if(not w in my_ports):
        wi = self.ref.wires[w].renamed(prefix + w);
        wi.translate_parameters(my_params);
        new_wires[prefix + w] = wi;
    
    new_insts = {};
    for sb in self.ref.instances:
      working_inst = self.ref.instances[sb].reconnect(
                  parent = self.parent,
                signal_translation = my_ports, 
             parameter_translation = my_params,
         prefix = prefix
      );
      new_insts[prefix + '_' + sb] = working_inst;
      sw = str(working_inst);
    return new_wires, new_insts;






class chiplet_declaration(module_declaration):
  def __init__(self, name, parent):
    self.ports = [];
    self.name = name;
    self.parent = parent;
    self.inputs = {};
    self.outputs = {}
    self.inouts = {};
    self.wires = {};
    self.sub_blocks = {};
    self.instances = {};
    self.parameters = {};
    self.body_changed = True;
    self.num_instances = 0;
  def include_instance(self, inst):
    """
       Insert an instance int the current chiplet,
       update it's interface, and resolve conflicts 
       regarding port directions.
    """
    i, o, io = inst.get_connections();
    params = inst.get_parameter_connections_strings();
    """ process instance connections """
    for u in i:
      self.inputs[u] = i[u];
    for u in o:
      self.outputs[u] = o[u];
    for u in io:
      self.inouts[u] = io[u];
    
    for u in params:
      for v in name_re.findall(u[1]):
        self.parameters[v] = '0'; # this must be overloaded
    """ Resolve conflicting port directions """
    for u in self.inputs.keys():
      if((u in self.outputs) or (u in self.inouts)):
        del self.inputs[u];

    for u in self.outputs.keys():
      if(u in self.inouts):
        del self.outputs[u];
    # If some symbol used in port connections is a parameter
    # pass it as a parameter, not as an input or output.
    for plist in (i, o, io):
      for p in plist:
        if(p in self.parent.parameters):
          del plist[p];
          self.parameters[p] = 0;
        else:
          # Parameters used to declare signals used in the instances.
          for par in name_re.findall(plist[p]._range):
            self.parameters[par] = 0;

    """ Update port list """
    self.ports = self.inputs.keys() + self.outputs.keys() + self.inouts.keys();
    """ Place instance inside the chiplet """
    self.sub_blocks[inst.name] = inst;
    self.instances[inst.name] = inst;

  def get_instanciation(self, parent, name):
    s = self.name + ' ' 
    if(len(self.parameters) != 0):
      s += "#(" + (',\n  '.join(['.%s(%s)' % (p,p) for p in self.parameters])) + '\n)';
    s +=  name + '(\n  ';
    s += ',\n  '.join(['.%s(%s)' % (p, p) for p in self.ports]);
    s += '\n)';
    si = instance_declaration(src = s, ref = self, parent = parent, name = name)
    return si;
    
class structural_parser:
  def __init__(self, fname = None, no_link = False):
    self.modules_by_name = {};
    self.modules_by_file = {};
    self.unresolved = set();
    self.modules = [];
    if(fname == None):
      return;    # supported for python2.7
    # self.modules_by_name = {m.name: m for m in self.modules};
    self.parse_file(fname);
    if(not no_link):
      self.link();


  def parse_file(self, fname):      
    fh = open(fname);
    fs = comments.sub("", fh.read());
    fh.close();
    tmodules = [module_declaration(s, fname) for s in module_re.findall(fs)];
    self.modules_by_file[fname] = tmodules;
    for m in tmodules:
      self.modules_by_name[m.name] = m;
      """ If the HDL was linked with unresolved
       modules, then a file defining a module that was unresolved
       is loaded, remove it from the list of unresolved.
       however its references will be resolved only after
       calling the link method. """
      self.unresolved.discard(m.name)    
    self.modules += tmodules;
  def save_hdl_file(self, fname):
    if(fname in self.modules_by_file):
      fh = open(fname, "w");
      for m in self.modules_by_file[fname]:
        fh.write(str(m));
        m.body_changed = False;
      fh.close();
  def write_stub(self, fname):
    fh = open(fname, "w");
    for m in self.modules:
      fh.write(m.stub());
    fh.close();
  def write_hdl(self, fname):
    fh = open(fname, "w");
    for m in self.modules:
      fh.write(str(m));
    fh.close();

  def link(self):
    """ when the modules were parsed, the list of available 
        modules was not available, now we are able to parse
        instances and associate each instance with the corresponding
        module declaration """
    for m in self.modules:
      m.link(self.modules_by_name);
      for u in m.instances:
        if(not u in m.sub_blocks):
          """ Keep a set of unresolved modules """
          self.unresolved.add(u);
