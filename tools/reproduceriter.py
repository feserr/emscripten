#!/usr/bin/env python

'''

* This is a work in progress *

Reproducer Rewriter
===================

Processes a project and rewrites it so as to generate deterministic,
reproducible automatic results. For example, you can run this on a
game, and then when the game is run it will record user input and
sources of nondeterminism like Math.random(). You can then run
that recording as a benchmark or as a demo, it should give nearly
identical results every time it is run to the data that was
recorded.

Usage:

1. Run this script as

    reproduceriter.py IN_DIR OUT_DIR FIRST_JS [WINDOW_LOCATION] [ON_IDLE]

   IN_DIR should be the project directory, and OUT_DIR will be
   created with the instrumented code (OUT_DIR will be overwritten
   if it exists). FIRST_JS should be a path (relative to IN_DIR) to
   the first JavaScript file loaded by the project (this tool
   will add code to that). 

   You will need to call

    Recorder.start();

   at the right time to start the relevant event loop. For
   example, if your application is a game that starts receiving
   events when in fullscreen, add something like

    if (typeof Recorder != 'undefined') Recorder.start();

   in the button that launches fullscreen. start() will start
   either recording when in record mode, or replaying when
   in replay mode, so you need this in both modes.

2. Run the instrumented project in OUR_DIR and interact with
   the program. When you are done recording, open the web
   console and run

    Recorder.finish();

   This will write out the recorded data into the current tab.
   Save it as

    repro.data

   in OUT_DIR.

3. To re-play the recorded data, run the instrumented build
   with

    &reproduce=repro.data

   Note that as mentioned above you need to call

    Recorder.start();

   when the recorded event loop should start to replay.

Notes:

 * When we start to replay events, the assumption is that
   there is nothing asynchronous that affects execution. So
   asynchronous loading of files should have already
   completed.

   TODO: start running recorded events with some trigger, for example the fullscreen button in BananaBread

Examples

 * BananaBread: Unpack into a directory called bb, then one
   directory up, run

    emscripten/tools/reproduceriter.py bb bench js/game-setup.js game.html?low,low,reproduce=repro.data "function(){ print('triggering click'); document.querySelector('.fullscreen-button.low-res').callEventListeners('click'); window.onIdle = null; }"

   The last parameter specifies what to do when the event loop is idle: We fire an event and then set onIdle (which was this function) to null, so this is a one-time occurence.
'''

import os, sys, shutil, re

assert len(sys.argv) >= 4, 'Usage: reproduceriter.py IN_DIR OUT_DIR FIRST_JS [WINDOW_LOCATION]'

# Process input args

in_dir = sys.argv[1]
out_dir = sys.argv[2]
first_js = sys.argv[3]
window_location = sys.argv[4] if len(sys.argv) >= 5 else ''
on_idle = sys.argv[5] if len(sys.argv) >= 6 else ''

dirs_to_drop = 0 if not os.path.dirname(first_js) else len(os.path.dirname(first_js).split('/'))

if os.path.exists(out_dir):
  shutil.rmtree(out_dir)
assert os.path.exists(os.path.join(in_dir, first_js))

# Copy project

print 'copying tree...'

shutil.copytree(in_dir, out_dir)

# Add customizations in all JS files

print 'add customizations...'

for parent, dirs, files in os.walk(out_dir):
  for filename in files:
    if filename.endswith('.js'):
      fullname = os.path.join(parent, filename)
      print '   ', fullname
      js = open(fullname).read()
      js = re.sub('document\.on(\w+) ?= ?([\w.$]+)', lambda m: 'Recorder.onEvent("' + m.group(1) + '", ' + m.group(2) + ')', js)
      js = re.sub('''([\w.'"\[\]]+)\.addEventListener\(([\w,. $]+)\)''', lambda m: 'Recorder.addListener(' + m.group(1) + ', ' + m.group(2) + ')', js)
      open(fullname, 'w').write(js)

# Add our boilerplate

print 'add boilerplate...'

open(os.path.join(out_dir, first_js), 'w').write(
  open(os.path.join(os.path.dirname(__file__), 'reproduceriter.js')).read() % (
    window_location, window_location.split('?')[-1], on_idle or 'null', dirs_to_drop) + open(os.path.join(in_dir, first_js)).read() + '''
if (typeof nagivator == 'undefined') {
  window.runEventLoop();
}
''')

print 'done!'

