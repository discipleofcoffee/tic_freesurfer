
export TIC_FREESURFER_PATH=''  # Add path information here
export TIC_FREESURFER_PYTHONPATH=${TIC_FREESURFER_PATH}/freesurfer

export PYTHONPATH=${TIC_FREESURFER_PYTHONPATH}:$PYTHONPATH

alias  tic_freesurfer='python2 ${FREESURFER_PYTHONPATH}/tic_freesurfer.py'
