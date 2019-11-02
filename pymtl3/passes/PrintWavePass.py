"""
========================================================================
PrintWavePass.py
========================================================================
Print single bit signal in wave form and multi-bit signal by showing
least significant bits.

To use, call top._print_wave(top)

Inspired by PyRTL's state machine screenshot, which shows the change of signal
values along ticks of the clock.

Link: https://ucsbarchlab.github.io/PyRTL/

Author : Kaishuo Cheng
Date   : Oct 4, 2019
"""

import time
from collections import defaultdict
from copy import deepcopy
import py
import sys
from pymtl3.dsl import Const
from pymtl3.passes.BasePass import BasePass, PassMetadata
import random

class PrintWavePass( BasePass ):

  def __call__( self, top ):
    top._print_wave = _help_print

def _process_binary(sig,base,max):
  """
  Returns int value from a signal in 32b form. Used for testing.

  Example: input: 0b00000000000000000000000000000000 10
           output: 0
  """
  if sig[1] == "b":
    sig = sig[2:]
  if base == 10:
    temp_int = int(sig,2)
    if sig[0] == '1':
      return temp_int -2 **32      #taking 2's complement.
                                    #leading 1 indicates a negative number
    else:
      return temp_int
    #hex number
  else:
    temp_hex = hex(int(sig,2))[2:]
    l = len(temp_hex)
    if l > max:
      temp_hex = temp_hex[l-max:]

    if l < max:
      temp_hex = '0'*(max-l) + temp_hex
    return temp_hex

def _help_print(self):
  char_length = 5
  tick = u'\u258f'
  up, down = u'\u2571', u'\u2572'
  x, low, high = u'\u2573', u'\u005f', u'\u203e'
  revstart, revstop = '\x1B[7m', '\x1B[0m'
  light_gray = '\033[47m'
  back='\033[0m'  #back to normal printing
  all_signals = self._collect_signals

  #spaces before cycle number
  max_length = 0
  for sig in all_signals:
    #   Example: s.in(12b)
    # length of signal name + (b) + number of digits, like 12
    # to add(32b) in front, add this to maxlength:
    #len(str(len(all_signals[sig][0][0])))+3
    this_length = len(sig)
    if this_length > max_length:
       if sig != "s.clk" and sig != "s.reset":
          max_length = this_length

  print(" "*(max_length+1),end = "")

  #handles clock tick symbol
  for i in range(0,len(all_signals["s.clk"])):
    #insert a space every 5 cycles
    if i % 5 == 0:
      print(tick + str(i)+ " "*(char_length-2) ,end="")
    else:
      print(tick + " "*(char_length-1) ,end="")
    if i % 5 == 1:
      print(" ",end ="")

  print("")
  #signals
  for sig in all_signals:
    if sig != "s.clk" and sig != "s.reset":
      print("")
      bit_length = len(all_signals[sig][0][0])-2
      pos = sig.find('.')
      suffix = ""   # once used for (32b)
      #print suffix
      print((sig[pos+1:]+suffix).rjust(max_length),end="")
      prev_sig = None
      # one bit
      if bit_length==1:
        for val in all_signals[sig]:

          #every 5 cycles add a space
          if val[1]%5 == 0:
            print(" ",end = "")
          if val[0][2] == '1':
            current_sig = high
          else:
            current_sig = low
          # detecting if first cycle
          if prev_sig is not None:
            if prev_sig == low and current_sig == high:
              print(up+current_sig*(char_length-1),end = "")
            elif prev_sig == high and current_sig == low:
              print(down+current_sig*(char_length-1),end = "")
            # prev and current signal agree
            else:
              print(current_sig*char_length,end = "")
          # first cycle
          else:
            print(current_sig*char_length,end = "")
          prev_sig = current_sig

        print("")
        #multiple bits
      else:
        next = 0
        val_list = all_signals[sig]
        for i in range(len(val_list)):
          # signals in this cycle is still the same as before
          if next > 0:
            next -=1
            continue

          val = val_list[i]
          for j in range(i,len(val_list)):
            # a space every 5 cycles
            if (j%5==4):
              break
            if (val_list[j][0] != val[0]):
              j = j-1
              break

          if i%5 == 0:
            print(back +" ",end = "")

          #first is reserved for X or " ". Rest is 5 char length.
          length = 4+ 5*(j-i)
          next = j-i
          if length >= bit_length//4:
            length = bit_length//4
            if bit_length %4 != 0:
              length+=1
            plus = False
          else:
            #reverse a place for +
            length = length -1
            plus = True

          current = _process_binary(val[0],16,length)
          # print a +, with one less space for signal number
          if(plus):
            if i==0:
              print(light_gray + " " +'\033[30m'+"+"+ current,end = "")
            else:
              print(light_gray + '\033[30m'+x + "+" +current,end = "")
          # no +, more spaces for signal number
          else:
            if i==0:
              print(light_gray + " " +'\033[30m'+ current,end = "")
            else:
              print(light_gray + '\033[30m'+x +current,end = "")
            print(" "*(4+5*(j-i)-length),end = "")

        print(back + "")

  print("")
