#!/usr/bin/env bash

export TIC_FREESURFER_PATH=${TIC_PATH}/tic_freesurfer  # Add path information here
export TIC_FREESURFER_PYTHONPATH=${TIC_FREESURFER_PATH}/freesurfer
export PYTHONPATH=${TIC_FREESURFER_PYTHONPATH}:$PYTHONPATH

alias  tic_freesurfer='python ${TIC_FREESURFER_PYTHONPATH}/freesurfer.py'
