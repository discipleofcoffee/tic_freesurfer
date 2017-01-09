#!/usr/bin/env bash

# The following two lines should be placed your .tic directory in your tic.sh
# setup file. This assumes that tic_freesurfer is installed in the $TIC_PATH.  It is
# OK to put TIC_FREESURFER in a different location. You just need to specify the the
# TIC_FREESURFER_PATH correctly.

# export TIC_FREESURFER_PATH=$TIC_PATH/tic_freesurfer/''  # Add path information here
# source $TIC_FREESURFER_PATH/tic_freesurfer_bash_setup.sh

export PYTHONPATH=${TIC_FREESURFER_PYTHONPATH}:$PYTHONPATH

alias  tic_freesurfer='python3 ${TIC_FREESURFER_PYTHONPATH}/freesurfer.py'
