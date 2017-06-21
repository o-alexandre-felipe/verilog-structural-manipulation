#!/bin/env python
import pygtk;
import sys;
import os;
import re;
pygtk.require('2.0')
import gtk;
from parse import *

class ChipletDialog(gtk.Dialog):
  def __init__(self, parent, block_list, mod_name_str = '', inst_name_str = ''):
    gtk.Dialog.__init__(self, "Create Chiplet", parent, 0,
        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
         gtk.STOCK_OK, gtk.RESPONSE_OK));

    self.set_default_size(150, 100)

    label = gtk.Label("You are up to move some blocks to a new chiplet:");
    block_list_view = self.filled_gtkList(block_list);
    instname_label = gtk.Label('Instance Name:');
    self.instname_entry = gtk.Entry();
    self.instname_entry.set_text(inst_name_str)
    modulename_label = gtk.Label('Module Name:');
    self.modname_entry  = gtk.Entry();
    self.modname_entry.set_text(mod_name_str)
    box = self.get_content_area()
    box.add(label);
    box.add(block_list_view);
    box.add(instname_label);
    box.add(self.instname_entry);
    box.add(modulename_label);
    box.add(self.modname_entry);
    self.show_all()

  def filled_gtkList(self, items):
    model = gtk.ListStore(str);
    for s in items:
      model.append([s]);
    listView = gtk.TreeView(model);
    renderer = gtk.CellRendererText()
    column = gtk.TreeViewColumn("Sub-block", renderer, text=0)
    listView.append_column(column);
    return listView;
class HDL_Explorer:
  # close the window and quit
  def delete_event(self, widget, event, data=None):
      gtk.main_quit()
      return False
  def create_childs(self, parent, root):
      child_node = self.treestore.append(parent, (root[0][0],));
      for child in sorted(root[1]):
        if(isinstance(child, list)):
          self.create_childs(child_node, child);
  def sample(self): 
      # we'll add some data now - 4 rows with 3 child rows each
      for parent in range(4):
          piter = self.treestore.append(None, ['parent %i' % parent])
          for child in range(3):
              self.treestore.append(piter, ['child %i of parent %i' %
                                            (child, parent)])
  def init_toolbar(self):
    script_dir = os.path.dirname(os.path.realpath(__file__));
    toolbar = gtk.Toolbar()
    toolbar.set_style(gtk.TOOLBAR_ICONS)
    iconsave = gtk.Image();
    iconsave.set_from_file(script_dir + '/img/save_as.png');
    sel = self.treeview.get_selection()
    sel.set_mode(gtk.SELECTION_MULTIPLE);
    #newtb = gtk.ToolButton(gtk.STOCK_NEW)
    #opentb = gtk.ToolButton(gtk.STOCK_OPEN)
    #savetb = gtk.ToolButton(gtk.STOCK_SAVE)
    #savetb = gtk.ToolButton(iconsave)
    sep = gtk.SeparatorToolItem()
    #quittb = gtk.ToolButton(gtk.STOCK_QUIT)

    icondissolve = gtk.Image();
    icondissolve.set_from_file(script_dir + '/img/02_Out-32.png');
    #dissolvetb = gtk.ToolButton(icondissolve, 'Dissolve sub block.');
    
    iconpack = gtk.Image();
    iconpack.set_from_file(script_dir + '/img/pack.png');
    #packtb = gtk.ToolButton(iconpack, 'Pack in to new chiplet.')


    #toolbar.insert(newtb, 0)
    #toolbar.insert(opentb, 1)
    #toolbar.insert(savetb, 2)
    #toolbar.insert(sep, 3)
    #toolbar.insert(quittb, 4)
    toolbar.append_item(text = 'Save HDL', 
        tooltip_text = 'Save a modified version of the top level HDL.',
        tooltip_private_text = None,
        icon = iconsave,
        callback = self.save_hdl_callback,
        user_data = None);
    
    toolbar.append_item(text = 'Dissolve', 
        tooltip_text = 'Dissolve Selected Blocks.',
        tooltip_private_text = 'dissolve button',
        icon = icondissolve,
        callback = self.dissolve_callback,
        user_data = sel);

    toolbar.append_item(text = 'Pack', 
        tooltip_text = 'Pack selected sub blocks in a new chiplet.',
        tooltip_private_text = 'pack button',
        icon = iconpack,
        callback = self.pack_callback,
        user_data = sel);
    toolbar.set_tooltips(enable=True);
    # quittb.connect("clicked", gtk.main_quit)
    return toolbar;

  def get_selected_top_level_instances(self, sel):
    """ Return a list with instances selected at top level, 
        i.e. integration blocks. """
    model, path_list = sel.get_selected_rows();
    return [model.get_value(model.get_iter(path), 0)
                for path in path_list if len(path) == 2];


  def save_hdl_callback(self, button):
    files2save = set();
    for m in self.work.modules:
      if(m.body_changed):
        files2save.add(m.src_file);
    for fname in files2save:
      print "Saving %s" % fname;
      self.work.save_hdl_file(fname);
    pass;

  def create_chiplet(self, instances, mod_name, inst_name):
    c = self.top_hdl.move_to_chiplet(instances, mod_name, inst_name); 
    self.work.modules_by_name[mod_name] = c;
    self.work.modules.append(c);
    c.src_file = "%s/%s.v" % (os.path.dirname(self.top_hdl.src_file), c.name);
    self.work.modules_by_file[c.src_file] = [c];

  def pack_callback(self, button, sel):
    list_of_instances = self.get_selected_top_level_instances(sel);
    for i in list_of_instances:
      if not i in self.top_hdl.sub_blocks:
        print "Instance %d is not resolved and can't be moved to a chiplet" % i.name;
    list_of_instances = [i for i in list_of_instances if i in self.top_hdl.sub_blocks];
    idx = 0;
    while 1:
      chiplet_name = "chiplet_%d" % idx;
      if(not chiplet_name in self.work.modules_by_name):
        if(not chiplet_name in self.top_hdl.instances):
          break;
      idx += 1;
    pack_dialog = ChipletDialog(None, list_of_instances, chiplet_name, chiplet_name);
    u = pack_dialog.run();
    if(u == gtk.RESPONSE_OK):
      chiplet_name = pack_dialog.modname_entry.get_text();
      chiplet_inst_name = pack_dialog.instname_entry.get_text();
      self.create_chiplet(list_of_instances, chiplet_name, chiplet_inst_name); 
      self.update_treestore(); # Naive solution
    # This will close the dialog
    pack_dialog.destroy();
    return True;

  def dissolve_callback(self, button, sel):
    list_of_instances = self.get_selected_top_level_instances(sel);
    for b in list_of_instances:
      self.top_hdl.dissolve_sub_block(b, "%s_disolved___" % b)
    self.update_treestore(); # Naive solution 

  def update_treestore(self):
    # Clear treestore if any item present.
    for row in self.treestore:
      self.treestore.remove(row.iter);
    loaded_tree = self.top_hdl.hierarchy_tree(self.top_hdl.name);
    # we'll add some data now - 4 rows with 3 child rows each
    self.create_childs(None, loaded_tree);
    self.treeview.expand_row(path = (0,), open_all = False);
    
  def update_hierarchy_view(self):
    self.update_treestore();
    # create the TreeViewColumn to display the data
    self.tvcolumn0 = gtk.TreeViewColumn('instance')
    # add tvcolumn to treeview
    self.treeview.append_column(self.tvcolumn0)
     
    # create a CellRendererText to render the data
    self.cell0 = gtk.CellRendererText()
    # add the cell to the tvcolumn and allow it to expand
    self.tvcolumn0.pack_start(self.cell0, True)
    # set the cell "text" attribute to column 0 - retrieve text
    # from that column in treestore
    self.tvcolumn0.add_attribute(self.cell0, 'text', 0)
    # make it searchable
    self.treeview.set_search_column(0)

    # Allow sorting on the column
    self.tvcolumn0.set_sort_column_id(0)
    # Allow drag and drop reordering of rows?
    self.treeview.set_reorderable(False)

  def init_work_hdl(self, files):
    p = structural_parser();
    print "Parsing..."
    for f in files:
      p.parse_file(f);
    print "Linking"
    p.link();
    print '%d modules' % (len(p.modules))
    if(len(p.unresolved) != 0):
      print '%d unresolved modules instantiated' % (len(p.unresolved))
      for m in p.unresolved:
        print "  - %s is unresolved" % m;
      print 'Instances of unresolved modules will not be shown'
    self.work = p;

    
  def set_top_module(self, top = None):
    self.top_hdl = self.work.modules_by_name[top];
    self.update_hierarchy_view();

  def __init__(self):
    
    # Create a new window
    self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    self.window.set_title('Hierarchy Arranger')
    self.window.set_size_request(500, 800)
    self.scrolled_window = gtk.ScrolledWindow();
    self.scrolled_window.set_border_width(10);

    self.scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
    
    
    # treestore instance name.
    self.treestore = gtk.TreeStore(str)
    # create the TreeView using treestore
    self.treeview = gtk.TreeView(self.treestore)


    self.window.connect("delete_event", self.delete_event)
    # Allow multiple blocks selection.
    toolbar = self.init_toolbar();

    vbox = gtk.VBox(False, 3)
    
    self.scrolled_window.add(self.treeview);

    vbox.pack_start(toolbar, False, False, 0);
    vbox.pack_start(self.scrolled_window, True, True, 1)
    self.window.add(vbox);
    self.window.show_all()


def file_parser(flist):
  p = structural_parser();
  print "Parsing..."
  for f in flist:
    p.parse_file(f);
  print "Linking"
  p.link();
  print '%d modules' % (len(p.modules))
  if(len(p.unresolved) != 0):
    print '%d unresolved modules instantiated' % (len(p.unresolved))
    for m in p.unresolved:
      print "  - %s is unresolved" % m;
    print 'Instances of unresolved modules will not be shown'
  return p;

def main():
  HDLE = HDL_Explorer();
  if(sys.argv[1] == '-top'):
    HDLE.init_work_hdl(sys.argv[3:]);
    HDLE.set_top_module(sys.argv[2]);
  else:
    HDLE.init_work_hdl(sys.argv[1:]);
    p = HDLE.work;
    u = [m for m in p.modules_by_name if(p.modules_by_name[m].num_instances == 0)];
    if(len(u) == 1):
      HDLE.set_top_module(u[0]);
    else:
      print "Multiple TOP modules defined, choose one via -top argument."
      print "The candidates are:"
      for m in u:
        print "  - %s from file %s" % (m, p.modules_by_name[m].src_file);
      return;
  gtk.main();


if __name__ == '__main__':
  main();
