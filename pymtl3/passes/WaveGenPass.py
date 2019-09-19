from __future__ import absolute_import, division, print_function

import time
from collections import defaultdict
from copy import deepcopy

import py
import sys
from pymtl3.dsl import Const
from pymtl3.passes.BasePass import BasePass, PassMetadata

from .errors import PassOrderError



class WaveGenPass( BasePass ):

  def __call__( self, top ):

    if not hasattr( top._sched, "schedule" ):
      raise PassOrderError( "schedule" )

    if hasattr( top, "_cl_trace" ):
      schedule = top._cl_trace.schedule
    else:
      schedule = top._sched.schedule

    top._vcd = PassMetadata()

    schedule.append( self.make_wav_gen_func( top, top._vcd ) )
  def make_wav_gen_func( self, top, vcdmeta ):
 

        # Preprocess some metadata

    component_signals = defaultdict(set)

    all_components = set()

    # We only collect non-sliced leaf signals
    # TODO only collect leaf signals and for nested structs
    for x in top._dsl.all_signals:
      for y in x.get_leaf_signals():
        host = y.get_host_component()
        component_signals[ host ].add(y)

    # We pre-process all nets in order to remove all sliced wires because
    # they belong to a top level wire and we count that wire

    trimmed_value_nets = []
    vcdmeta.clock_net_idx = None

    # FIXME handle the case where the top level signal is in a value net
    for writer, net in top.get_all_value_nets():
      new_net = []
      for x in net:
        if not isinstance(x, Const) and not x.is_sliced_signal():
          new_net.append( x )
          if repr(x) == "s.clk":
            # Hardcode clock net because it needs to go up and down
            assert vcdmeta.clock_net_idx is None
            vcdmeta.clock_net_idx = len(trimmed_value_nets)

      if new_net:
        trimmed_value_nets.append( new_net )

    # Inner utility function to perform recursive descent of the model.
    # Shunning: I mostly follow v2's implementation

    def recurse_models( m, level ):

      # Special case the top level "s" to "top"

      my_name = m.get_field_name()
      if my_name == "s":
        my_name = "top"

      m_name = repr(m)

      # Define all signals for this model.
      for signal in component_signals[m]:
        trimmed_value_nets.append( [ signal ] )


      # Recursively visit all submodels.
      for child in m.get_child_components():
        recurse_models( child, level+1 )

    # Begin recursive descent from the top-level model.
    recurse_models( top, 0 )



    for i, net in enumerate(trimmed_value_nets):

      # Set this to be the last cycle value
      setattr( vcdmeta, "last_{}".format(i), net[0]._dsl.Type().bin() )

    # Now we create per-cycle signal value collect functions

    vcdmeta.sim_ncycles = 0

    dump_vcd_per_signal = """
      value_str = {1}.bin()
      if "{1}" in vcdmeta.sigs:
        sig_val_lst = vcdmeta.sigs["{1}"]
        sig_val_lst.append((value_str, vcdmeta.sim_ncycles))
        vcdmeta.sigs["{1}"] = sig_val_lst
      else:
        vcdmeta.sigs["{1}"] = [(value_str, vcdmeta.sim_ncycles)]"""

    # TODO type check

    # Concatenate the strings for all signals

    # Give all ' and " characters a preceding backslash for .format
    vcd_srcs = []
    for i, net in enumerate( trimmed_value_nets ):
      if i != vcdmeta.clock_net_idx:
        vcd_srcs.append( dump_vcd_per_signal.format( i, net[0]) )

    deepcopy # I have to do this to circumvent the tools

    vcdmeta.sigs = {}
    char_length = 5

    src =  """
def dump_vcd():
  _tick = u'\u258f'
  _up, _down = u'\u2571', u'\u2572'
  _x, _low, _high = u'\u2573', u'\u005f', u'\u203e'
  _revstart, _revstop = '\x1B[7m', '\x1B[0m'

  try:
    # Type check
    {1}
    # Dump VCD
    {2}
  except Exception:
    raise

  if True:
    # print(sigs)
    print(\n)
    print(\n)
    print("cycle num:" + str(vcdmeta.sim_ncycles))
    for sig in vcdmeta.sigs:
      if sig != "s.clk" and sig != "s.reset":
        print(\n)
        print("")
        sys.stdout.write(sig)

        next_char_length = char_length
        
        prev_val = None

        for val in vcdmeta.sigs[sig]:
          if prev_val is not None:
            if prev_val[0] == '0b0':
              for i in range(0,next_char_length): sys.stdout.write(_low)
              if val[1]%5 == 0:
                sys.stdout.write(" ")
              if val[0] == '0b1':
                sys.stdout.write(_up)
                next_char_length = char_length - 1
              else:
                next_char_length = char_length
            elif prev_val[0] == '0b1':
              for i in range(0,next_char_length): sys.stdout.write(_high)
              if val[1]%5== 0:
                sys.stdout.write(" ")
              if val[0] == '0b0':
                sys.stdout.write(_down)
                next_char_length = char_length - 1
              else:
                next_char_length = char_length
          prev_val = val

  vcdmeta.sim_ncycles += 1
""".format("", "", "".join(vcd_srcs) )

    s, l_dict = top, {}

    exec(compile( src, filename="temp", mode="exec"), globals().update(locals()), l_dict)
    return l_dict['dump_vcd']
