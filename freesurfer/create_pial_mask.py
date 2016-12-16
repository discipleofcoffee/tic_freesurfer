#!/usr/bin/env python

"""
create volume brain mask from pial surface and aseg
"""
import shutil

import argparse
import os
from nipype.interfaces.freesurfer import VolumeMask

import subprocess

import logging

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)

#
#
#
# mri_surf2vol --hemi lh --surf pial --o mask_surf2vol.pial_lh.nii.gz --identity 34P1029 --template ../../mri/brain.mgz --mkmask --fillribbon --fill-projfrac -2 0 0.05
# mri_surf2vol --hemi rh --surf pial --o mask_surf2vol.pial_rh.nii.gz --identity 34P1029 --template ../../mri/brain.mgz --mkmask --fillribbon --fill-projfrac -2 0 0.05
#
# fslmaths mask_surf2vol.pial_rh.nii.gz -add mask_surf2vol.pial_lh.nii.gz -bin pial.nii.gz
#
# tic_labels_remove aseg.nii.gz --out_nii mask.nii.gz --remove 46 47 7 8 42 3 16 15 --bin
#
# fslmaths mask.nii.gz -dilM -ero 1.mask.nii.gz
# fslmaths 1.mask.nii.gz -add pial.nii.gz -bin -fillh -dilM -ero -fillh -ero -dilM 2.mask.nii.gz

def create_pial_mask(subject_id, subjects_dir, verbose=False):

    ribbon = os.path.abspath(os.path.join(subjects_dir, subject_id, 'mri','ribbon'))
    aseg = os.path.abspath(os.path.join(subjects_dir, subject_id, 'mri','aseg'))

    mc = MRIConvert()
    mc.inputs.in_file = ribbon + '.mgz'
    mc.inputs.out_file = ribbon + '.nii.gz'
    mc.inputs.out_type = 'nii'
    mc.cmdline
    mc.run()

    mc = MRIConvert()
    mc.inputs.in_file = aseg + '.mgz'
    mc.inputs.out_file = aseg + '.nii.gz'
    mc.inputs.out_type = 'nii'
    mc.cmdline
    mc.run()
    
#tic_labels_remove aseg.nii.gz --out_nii 1.mask.nii.gz --remove 3 42
#fslmaths 1.mask.nii.gz -bin 1.mask.nii.gz

#fslmaths 1.mask.nii.gz -add ribbon.nii.gz -bin 2.mask.nii.gz
#fslmaths 2.mask.nii.gz -kernel sphere 10 -dilM -ero -fillh 3.mask.nii.gz

    return

# ======================================================================================================================
# region Main Function
#

def main():
    ## Parsing Arguments
    #
    #

    usage = "usage: %prog [options] arg1 arg2"

    parser = argparse.ArgumentParser(prog='create_pial_mask')

    parser.add_argument("subject_id", help="Subject ID", default=os.getcwd())
    parser.add_argument("--subjects_dir", help="Subject's Directory (default=$SUBJECTS_DIR)",
                        default=os.getenv('SUBJECTS_DIR'))

    parser.add_argument('-v', '--verbose', help="Verbose flag", action="store_true", default=False)

    inArgs = parser.parse_args()

    create_pial_mask(inArgs.subject_id, inArgs.subjects_dir)


#endregion

if __name__ == "__main__":
    sys.exit(main())
