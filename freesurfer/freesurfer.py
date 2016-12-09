#!/usr/bin/env python

"""
tic_freesurfer.py provides a basic interface for Freesurfer recon-all and QA.
"""
import shutil

import sys
import os  # system functions
import re
import json

import argparse
import iwUtilities as util
import subprocess

import nipype.interfaces.fsl as fsl
import nipype.interfaces.freesurfer as fs
from nipype.pipeline.engine import Workflow, Node

import datetime
import getpass
from collections import OrderedDict

import logging

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)


# ======================================================================================================================
# region Support Functions


def cp_file_with_timestamp(fname, suffix, user=getpass.getuser(), fmt='{fname}.{suffix}.{user}.d%Y%m%d_%H%M%S'):
    return datetime.datetime.now().strftime(fmt).format(fname=fname, suffix=suffix, user=user)


def get_info(in_freesurfer_id, in_freesurfer_subjects_dir=os.getenv('SUBJECTS_DIR'), t1=None, t2=None, flair=None):

    freesurfer_id = in_freesurfer_id
    freesurfer_subjects_dir = in_freesurfer_subjects_dir
    freesurfer_subject_dir = os.path.join(freesurfer_subjects_dir, freesurfer_id)

    #     if os.path.isdir( freesurfer_subjects_dir ):
    #          print('Freesurfer ' + freesurfer_subjects_dir + ' does not exist')
    #          sys.exit()

    #     if os.path.isdir( freesurfer_subject_dir ):
    #          print('Freesurfer ' + freesurfer_subject_dir + 'does not exist')
    #          sys.exit()

    input_files = OrderedDict((('t1', os.path.abspath(t1) if t1 else None),
                               ('t2', os.path.abspath(t2) if t2 else None),
                               ('flair', os.path.abspath(flair) if flair else None)
                               )
                              )

    base = OrderedDict((('subject_id', freesurfer_id),
                        ('subjects_dir', freesurfer_subjects_dir),
                        ('subject_dir', freesurfer_subject_dir),
                        ('mri', util.path_relative_to(freesurfer_subject_dir, 'mri')),
                        ('surf', util.path_relative_to(freesurfer_subject_dir, 'surf')),
                        ('scripts', util.path_relative_to(freesurfer_subject_dir, 'scripts'))
                        )
                       )

    volume_files = OrderedDict((('T1', os.path.join(base['mri'], 'T1.mgz')),
                                ('wm', os.path.join(base['mri'], 'wm.mgz')),
                                ('nu', os.path.join(base['mri'], 'nu.mgz')),
                                ('aseg', os.path.join(base['mri'], 'aseg.mgz')),
                                ('brainmask', os.path.join(base['mri'], 'brainmask.mgz')),
                                ('white_matter', os.path.join(base['mri'], 'wm.mgz')),
                                ('brain.finalsurfs', os.path.join(base['mri'], 'brain.finalsurfs.mgz')),
                                ('brain.finalsurfs.manedit', os.path.join(base['mri'], 'brain.finalsurfs.manedit.mgz')),
                                ('a2009', os.path.join(base['mri'], 'aparc.a2009s+aseg.mgz')),
                                ('wmparc', os.path.join(base['mri'], 'wmparc.mgz'))
                                )
                               )

    surface_lh_files = OrderedDict((('white', os.path.join(base['surf'], 'lh.white')),
                                    ('pial', os.path.join(base['surf'], 'lh.pial')),
                                    ('inflated', os.path.join(base['surf'], 'lh.inflated'))
                                    )
                                   )

    surface_rh_files = OrderedDict((('white', os.path.join(base['surf'], 'rh.white')),
                                    ('pial', os.path.join(base['surf'], 'rh.pial')),
                                    ('inflated', os.path.join(base['surf'], 'rh.inflated'))
                                    )
                                   )

    surface_files = OrderedDict((('lh', surface_lh_files), ('rh', surface_rh_files)))

    output_files = OrderedDict((('volume', volume_files), ('surface', surface_files)))

    log_files = OrderedDict((('status', os.path.join(base['scripts'], 'recon-all-status.log')),
                             ('log', os.path.join(base['scripts'], 'recon-all.log'))
                            ))

    return {'base': base, 'input': input_files, 'output': output_files, 'logs':log_files}

#endregion

# ======================================================================================================================
# region Quality Assurance


def qi(fsinfo, verbose=False):
    input_files = filter(None, fsinfo['input'].values())

    if util.check_files(input_files):

        qi_command = ['freeview', '-v'] + input_files

        if verbose:
            print(' '.join(qi_command))

        DEVNULL = open(os.devnull, 'wb')
        pipe = subprocess.Popen([' '.join(qi_command)], shell=True,
                                stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL, close_fds=True)

    else:
        pass


QA_METHODS = ['pial', 'wm_volume', 'wm_surface', 'wm_norm']

def qa_methods(selected_qa_method, fsinfo, verbose=False):

    logger = logging.getLogger(__name__)
    logger.debug('qa_methods()')

    if 'pial' in selected_qa_method:
        qa_methods_edit_pial(fsinfo, verbose)

    if 'wm_volume' in selected_qa_method:
        qa_methods_edit_wm_segmentation(fsinfo, verbose)

    if 'wm_surface' in selected_qa_method:
        qa_methods_edit_wm_surface(fsinfo, verbose)

    if 'wm_norm' in selected_qa_method:
        qa_methods_edit_wm_norm(fsinfo, verbose)

    return

def qa_freesurfer(qm_command, verbose=False):

    freeview_command = ['freeview', '--viewport', 'coronal' ] + qm_command

    if verbose:
        print
        print(' '.join(freeview_command))
        print


    DEVNULL = open(os.devnull, 'wb')
    pipe = subprocess.Popen([' '.join(freeview_command)], shell=True,
                            stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL, close_fds=True)


def qa_methods_edit_pial(fsinfo, verbose=False):
    # https://surfer.nmr.mgh.harvard.edu/fswiki/FsTutorial/TroubleshootingData
    # https://surfer.nmr.mgh.harvard.edu/fswiki/FsTutorial/PialEdits_freeview
    #
    # recon-all -autorecon-pial -subjid pial_edits_before

    # Volume plots
    #

    # Copy brainmask.mgz before editing it.
    shutil.copyfile(fsinfo['output']['volume']['brainmask'],
                    cp_file_with_timestamp(fsinfo['output']['volume']['brainmask'], 'qm_edit_pial'))

    shutil.copyfile(fsinfo['output']['volume']['brain.finalsurfs'],
                    cp_file_with_timestamp(fsinfo['output']['volume']['brain.finalsurfs'], 'qm_edit_pial'))

    shutil.copyfile(fsinfo['output']['volume']['brain.finalsurfs'],fsinfo['output']['volume']['brain.finalsurfs.manedit'])

    qm_volumes = [fsinfo['output']['volume']['T1']+':visible=0',
                  fsinfo['output']['volume']['brain.finalsurfs.manedit'] + ':visible=0',
                  fsinfo['output']['volume']['brainmask']
                  ]

    qm_surfaces = [fsinfo['output']['surface']['lh']['white'] + ':edgecolor=yellow',
                   fsinfo['output']['surface']['lh']['pial'] + ':edgecolor=red',
                   fsinfo['output']['surface']['rh']['white'] + ':edgecolor=yellow',
                   fsinfo['output']['surface']['rh']['pial'] + ':edgecolor=red'
                   ]

    qm_command = ['-v'] + qm_volumes + ['-f'] + qm_surfaces

    qa_freesurfer(qm_command, verbose)

def qa_methods_edit_wm_segmentation(fsinfo, verbose=False):
    # https://surfer.nmr.mgh.harvard.edu/fswiki/FsTutorial/TroubleshootingData
    # https://surfer.nmr.mgh.harvard.edu/fswiki/FsTutorial/WhiteMatterEdits_freeview
    #
    #

    # Volume plots
    #

    # Copy brainmask.mgz before editing it.
    shutil.copyfile(fsinfo['output']['volume']['brainmask'],
                    cp_file_with_timestamp(fsinfo['output']['volume']['brainmask'], 'qm_edit_pial'))

    qm_volumes = [fsinfo['output']['volume']['T1'],
                  fsinfo['output']['volume']['brainmask'],
                  fsinfo['output']['volume']['white_matter'] + ':colormap=heat:opacity=0.4'
                  ]

    qm_surfaces = [fsinfo['output']['surface']['lh']['white'] + ':edgecolor=blue',
                   fsinfo['output']['surface']['lh']['pial'] + ':edgecolor=red',
                   fsinfo['output']['surface']['rh']['white'] + ':edgecolor=blue',
                   fsinfo['output']['surface']['rh']['pial'] + ':edgecolor=red',
                   fsinfo['output']['surface']['rh']['inflated'] + ':visible=0',
                   fsinfo['output']['surface']['lh']['inflated'] + ':visible=0'
                   ]

    qm_command = [ '-v'] + qm_volumes + ['-f'] + qm_surfaces

    qa_freesurfer(qm_command, verbose)

def qa_methods_edit_wm_surface(fsinfo, verbose=False):
    # https://surfer.nmr.mgh.harvard.edu/fswiki/FsTutorial/TroubleshootingData
    # https://surfer.nmr.mgh.harvard.edu/fswiki/FsTutorial/WhiteMatterEdits_freeview
    #
    #

    # freeview -v topo_defect_before/mri/brainmask.mgz \
    # topo_defect_before/mri/wm.mgz:colormap=heat:opacity=0.4 \
    # -f topo_defect_before/surf/lh.white:edgecolor=yellow \
    # topo_defect_before/surf/lh.pial:edgecolor=red \
    # topo_defect_before/surf/rh.white:edgecolor=yellow \
    # topo_defect_before/surf/rh.pial:edgecolor=red


    # Volume plots
    #

    # Copy brainmask.mgz before editing it.
    shutil.copyfile(fsinfo['output']['volume']['brainmask'],
                    cp_file_with_timestamp(fsinfo['output']['volume']['brainmask'], 'qm_edit_pial'))

    qm_volumes = [fsinfo['output']['volume']['T1'],
                  fsinfo['output']['volume']['brainmask'],
                  fsinfo['output']['volume']['white_matter'] + ':colormap=heat:opacity=0.4'
                  ]

    qm_surfaces = [fsinfo['output']['surface']['lh']['white'] + ':edgecolor=blue',
                   fsinfo['output']['surface']['lh']['pial'] + ':edgecolor=red',
                   fsinfo['output']['surface']['rh']['white'] + ':edgecolor=blue',
                   fsinfo['output']['surface']['rh']['pial'] + ':edgecolor=red',
                   fsinfo['output']['surface']['rh']['inflated'] + ':visible=0',
                   fsinfo['output']['surface']['lh']['inflated'] + ':visible=0'
                   ]

    qm_command = ['-v'] + qm_volumes + ['-f'] + qm_surfaces

    qa_freesurfer(qm_command, verbose)


def qa_methods_edit_wm_norm(fsinfo, verbose=False):
    # https://surfer.nmr.mgh.harvard.edu/fswiki/FsTutorial/TroubleshootingData
    # https://surfer.nmr.mgh.harvard.edu/fswiki/FsTutorial/WhiteMatterEdits_freeview
    #
    #

    # freeview -v cp_before/mri/brainmask.mgz \
    # cp_before/mri/T1.mgz \
    # -f cp_before/surf/lh.white:edgecolor=blue \
    # cp_before/surf/lh.pial:edgecolor=red \
    # cp_before/surf/rh.white:edgecolor=blue \
    # cp_before/surf/rh.pial:edgecolor=red

    # Volume plots
    #

    # Copy brainmask.mgz before editing it.
    shutil.copyfile(fsinfo['output']['volume']['brainmask'],
                    cp_file_with_timestamp(fsinfo['output']['volume']['brainmask'], 'qm_edit_pial'))

    qm_volumes = [fsinfo['output']['volume']['T1'],
                  fsinfo['output']['volume']['brainmask'],
                  fsinfo['output']['volume']['white_matter'] + ':colormap=heat:opacity=0.4'
                  ]

    qm_surfaces = [fsinfo['output']['surface']['lh']['white'] + ':edgecolor=blue',
                   fsinfo['output']['surface']['lh']['pial'] + ':edgecolor=red',
                   fsinfo['output']['surface']['rh']['white'] + ':edgecolor=blue',
                   fsinfo['output']['surface']['rh']['pial'] + ':edgecolor=red',
                   fsinfo['output']['surface']['rh']['inflated'] + ':visible=0',
                   fsinfo['output']['surface']['lh']['inflated'] + ':visible=0'
                   ]

    qm_command = ['-v'] + qm_volumes + ['-f'] + qm_surfaces

    qa_freesurfer(qm_command, verbose)

#endregion

# ======================================================================================================================
# region Methods

METHODS = ['recon-all', 'pial', 'wm_volume', 'wm_surface', 'wm_norm']


def methods(selected_method, fsinfo, verbose=False):

    logger.debug('methods()')

    if 'recon-all' in selected_method:
        methods_recon_all(fsinfo, verbose)

    if 'pial' in selected_method:
        methods_recon_pial(fsinfo, verbose)

    if 'wm_volume' in selected_method:
        methods_recon_wm_volume(fsinfo, verbose)

    if 'wm_surface' in selected_method:
        methods_edit_wm_surface(fsinfo, verbose)

    if 'wm_norm' in selected_method:
        methods_edit_wm_norm(fsinfo, verbose)

    return


def methods_recon_all(fsinfo, verbose=False):
    if verbose:
        print('recon_all')

    fs_command = ['recon-all',
                  '-sd', fsinfo['base']['subjects_dir'],
                  '-subjid', fsinfo['base']['subject_id'],
                  '-all',
                  ]

    if not os.path.isdir(fsinfo['base']['subject_dir']):

        fs_command += ['-i', fsinfo['input']['t1']]

        if fsinfo['input']['t2']:
            fs_command += ['-T2', fsinfo['input']['t2']]

        if fsinfo['input']['flair']:
            fs_command += ['-FLAIR', fsinfo['input']['flair']]

    if verbose:
        print
        print(' '.join(fs_command))
        print

    util.iw_subprocess(fs_command, True, True, True)

    return

def methods_recon_pial(fsinfo, verbose=False):

    logger.debug('methods_recon_pial()')

    fs_command = [ 'recon-all',
                  '-autorecon-pial',
                  '-sd', fsinfo['base']['subjects_dir'],
                  '-subjid', fsinfo['base']['subject_id'],
                  ]

    if verbose:
        print
        print(' '.join(fs_command))
        print

    util.iw_subprocess(fs_command, True, True, True)

    return

def methods_wm_volume(fsinfo, verbose=False):

    logger.debug('methods_wm_volume()')

    fs_command = ['recon-all',
                  '-sd', fsinfo['base']['subjects_dir'],
                  '-subjid', fsinfo['base']['subject_id'],
                  '-autorecon2-wm',
                  '-autorecon3',
                  ]

    if verbose:
        print
        print(' '.join(fs_command))
        print

    util.iw_subprocess(fs_command, True, True, True)

    return

def methods_wm_surface(fsinfo, verbose=False):
    logger.debug('methods_wm_surface() direct call to methods_wm_volume()')
    methods_wm_volume(fsinfo, verbose)

def methods_wm_norm(fsinfo, verbose=False):

    fs_command = ['recon-all',
                  '-sd', fsinfo['base']['subjects_dir'],
                  '-subjid', fsinfo['base']['subject_id'],
                  '-autorecon2-cp'
                  '-autorecon3'
                  ]

    if not os.path.isdir(fsinfo['base']['subject_dir']):

        fs_command += ['-i', fsinfo['input']['t1']]

        if fsinfo['input']['t2']:
            fs_command += ['-T2', fsinfo['input']['t2']]

        if fsinfo['input']['flair']:
            fs_command += ['-FLAIR', fsinfo['input']['flair']]

    if verbose:
        print
        print(' '.join(fs_command))
        print

    util.iw_subprocess(fs_command, True, True, True)

    return


#endregion

def methods_recon_edit_pial(fsinfo, verbose=False):
    if verbose:
        print
        print('methods_recon_edit_pial')
        print

    fs_command = ['recon-all',
                  '-sd', fsinfo['base']['subjects_dir'],
                  '-subjid', fsinfo['base']['subject_id'],
                  '-autorecon-pial'
                  ]

    if verbose:
        print
        print(' '.join(fs_command))
        print

    try:
        util.iw_subprocess(freesurfer_command, True, True, True)
    except:
        pass

    return

# ======================================================================================================================
# region Status

def fslogs(selected_fslogs, fsinfo, verbose=False):

    logger = logging.getLogger(__name__)
    logger.debug('fslogs()')

    with open(fsinfo['logs'][selected_fslogs], 'r') as fin:
        print(fin.read())



def results(input_dir, verbose):
    pass


def status_methods(input_dir, verbose):
    pass


def status_results(input_dir, verbose):
    pass


#endregion

# ======================================================================================================================
# region Main Function
#

def main():
    ## Parsing Arguments
    #
    #

    usage = "usage: %prog [options] arg1 arg2"

    parser = argparse.ArgumentParser(prog='tic_freesurfer')

    parser.add_argument("subject_id", help="Subject ID", default=os.getcwd())
    parser.add_argument("--subjects_dir", help="Subject's Directory (default=$SUBJECTS_DIR)",
                        default=os.getenv('SUBJECTS_DIR'))

    parser.add_argument("--t1", help="T1w image NIFTI filename (default=t1w.nii.gz) ", default=None)    ## Parsing Arguments

    usage = "usage: %prog [options] arg1 arg2"

    parser = argparse.ArgumentParser(prog='imcollective_freesurfer')

    parser.add_argument("subject_id", help="Subject ID", default=os.getcwd())
    parser.add_argument("--subjects_dir", help="Subject's Directory (default=$SUBJECTS_DIR)",
                        default=os.getenv('SUBJECTS_DIR'))

    parser.add_argument("--t1", help="T1w image NIFTI filename (default=t1w.nii.gz) ", default=None)

    parser.add_argument("--t2", help="T2w image NIFTI filename (default=None) ", default=None)
    parser.add_argument("--flair", help="T2w FLAIR NIFTI filename (default=None)", default=None)

    parser.add_argument('-m','--methods', help='Methods (recon-all, pial, wm_norm, wm_volume, wm_surface )',
                        nargs=1, choices=METHODS, default=[None])

    parser.add_argument("--qm", help="QA methods (pial, wm_norm, wm_volume, wm_surface)", nargs='*', choices=QA_METHODS, default=[None])

    parser.add_argument("--status", help="Check Freesurfer status", action="store_true", default=False)
    parser.add_argument("--status_methods", help="Check Freesurfer methods status", action="store_true", default=False)
    parser.add_argument("--status_results", help="Check Freesurfer results status", action="store_true", default=False)

    FS_LOGS = ['log', 'status']

    parser.add_argument('--fslogs', help='FreeSurfer Logs (log, status)',
                         choices=FS_LOGS, default=None)

    parser.add_argument('-v', '--verbose', help="Verbose flag", action="store_true", default=False)

    parser.add_argument('--qi', help="QA inputs", action="store_true", default=False)
    parser.add_argument('--qr', help="QA results", action="store_true", default=False)

    inArgs = parser.parse_args()


    # Select

    fsinfo = get_info(inArgs.subject_id, inArgs.subjects_dir, inArgs.t1, inArgs.t2, inArgs.flair)

    if inArgs.verbose:
        print(json.dumps(fsinfo, indent=4))

    if inArgs.qi:
        qi(fsinfo, inArgs.verbose)


    # Methods
    if inArgs.methods:
        methods( inArgs.methods, fsinfo, inArgs.verbose)

    # Status
    if inArgs.status_methods or inArgs.status:
        status_methods(fsinfo, True)

    if inArgs.status_results or inArgs.status:
        status_results(fsinfo, True)


    # QA of methods
    if inArgs.qm:
        logger.debug('QM logging statement')  # will not print anything
        qa_methods(inArgs.qm, fsinfo, inArgs.verbose)

    if inArgs.fslogs:

        fslogs(inArgs.fslogs, fsinfo, inArgs.verbose)


#endregion

if __name__ == "__main__":
    sys.exit(main())

