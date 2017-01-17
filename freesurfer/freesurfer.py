#!/usr/bin/env python3

"""
tic_freesurfer.py provides a basic interface for Freesurfer recon-all and QA.
"""
import shutil

import sys
import os  # system functions
import re
import json

#import redcap # from PyCap http://sburns.org/2013/07/10/freesurfer-stats-in-redcap.htm
#from recon_stats import Subject
# from redcap import Project

import argparse
import _utilities as util
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

def  check_files(fileList, verboseFlag=False):
    
    qaInputStatus = True
    
    if verboseFlag:
        print
        
    for ii in fileList:

        if os.path.isfile(ii): 
            
            if verboseFlag:
                print(str( ii ) + " exists")
                
        else:                
            qaInputStatus = False
                    
            if verboseFlag:
                strError = str( ii ) + " does not exist"
                print(strError)
            
     
    if verboseFlag:
        print('')
        print("All files exist = " + str(qaInputStatus))
        print('')
        
    return qaInputStatus


def iw_subprocess( callCommand, verboseFlag=False, debugFlag=False,  nohupFlag=False ):

     import datetime

     iiDateTime = datetime.datetime.now()
     timeStamp = iiDateTime.strftime('%Y%m%d%H%M%S')
          
     callCommand = map(str, callCommand)

     if nohupFlag:

          if debugFlag:
               print('Timestamp: %s ' % timeStamp)

          
          callCommand = ["nohup" ] + callCommand

          stdout_log_file   = 'nohup.stdout.' + timeStamp +'.log'
          stderr_log_file   = 'nohup.stderr.' + timeStamp +'.log' 
          
          if verboseFlag or debugFlag:
               print('')
               print(" ".join(callCommand))
               print(stdout_log_file)
               print('')

          # http://stackoverflow.com/questions/6011235/run-a-program-from-python-and-have-it-continue-to-run-after-the-script-is-kille                   

          subprocess.Popen( callCommand,
                            stdout=open(stdout_log_file, 'w'),
                            stderr=open(stderr_log_file, 'w'),
                            preexec_fn=os.setpgrp, 
                            )

          if verboseFlag or debugFlag:
               print('')

     else:

          if debugFlag:
               print(' ')
               print(' '.join(callCommand))
               print(' ')

          pipe   = subprocess.Popen(callCommand, stdout=subprocess.PIPE)
          output = pipe.communicate()[0]

          if debugFlag:
               print(' ')
               print(output)
               print(' ')


def cp_file_with_timestamp(fname, suffix, user=getpass.getuser(), fmt='{fname}.{suffix}.{user}.d%Y%m%d_%H%M%S'):
    return datetime.datetime.now().strftime(fmt).format(fname=fname, suffix=suffix, user=user)


def path_relative_to(in_directory, in_path):

     if os.path.isabs(in_path):
          out_path = in_path
     else:
          out_path = os.path.abspath(os.path.join(in_directory, in_path )) 

     return out_path


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
                        ('mri', path_relative_to(freesurfer_subject_dir, 'mri')),
                        ('surf', path_relative_to(freesurfer_subject_dir, 'surf')),
                        ('scripts', path_relative_to(freesurfer_subject_dir, 'scripts'))
                        )
                       )

    volume_files = OrderedDict((('T1', os.path.join(base['mri'], 'T1.mgz')),
                                ('flair', os.path.join(base['mri'], 'FLAIR.mgz')),
                                ('t2', os.path.join(base['mri'], 'T2.mgz')),
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
                                    ('pial_woflair', os.path.join(base['surf'], 'lh.woFLAIR.pial')),
                                    ('pial', os.path.join(base['surf'], 'lh.pial')),
                                    ('inflated', os.path.join(base['surf'], 'lh.inflated'))
                                    )
                                   )

    surface_rh_files = OrderedDict((('white', os.path.join(base['surf'], 'rh.white')),
                                    ('pial', os.path.join(base['surf'], 'rh.pial')),
                                    ('pial_woflair', os.path.join(base['surf'], 'rh.woFLAIR.pial')),
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

    if check_files(input_files):

        qi_command = ['freeview', '-v'] + input_files

        if verbose:
            print(' '.join(qi_command))

        DEVNULL = open(os.devnull, 'wb')
        pipe = subprocess.Popen([' '.join(qi_command)], shell=True,
                                stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL, close_fds=True)

    else:
        pass


QA_METHODS = ['mri', 'pial', 'wm_volume', 'wm_surface', 'wm_norm']

def qa_methods(selected_qa_method, fsinfo, verbose=False):

    logger = logging.getLogger(__name__)
    logger.debug('qa_methods()')

    if 'mri' in selected_qa_method:
        qa_methods_mri(fsinfo, verbose)

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
        print(' ')
        print(' '.join(freeview_command))
        print(' ')


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
                  fsinfo['output']['volume']['flair']+':visible=0',
                  fsinfo['output']['volume']['aseg'] + ':visible=0:colormap=lut',
                  fsinfo['output']['volume']['brain.finalsurfs.manedit'] + ':visible=0',
                  fsinfo['output']['volume']['brainmask']
                  ]

    qm_surfaces = [fsinfo['output']['surface']['lh']['white'] + ':edgecolor=yellow',
                   fsinfo['output']['surface']['lh']['pial'] + ':edgecolor=red',
                   fsinfo['output']['surface']['lh']['pial_woflair'] + ':edgecolor=blue',
                   fsinfo['output']['surface']['rh']['white'] + ':edgecolor=yellow',
                   fsinfo['output']['surface']['rh']['pial'] + ':edgecolor=red',
                   fsinfo['output']['surface']['rh']['pial_woflair'] + ':edgecolor=blue',
                   ]

    qm_command = ['-v'] + qm_volumes + ['-f'] + qm_surfaces

    qa_freesurfer(qm_command, verbose)



def qa_methods_mri(fsinfo, verbose=False):
    # https://surfer.nmr.mgh.harvard.edu/fswiki/FsTutorial/TroubleshootingData
    # https://surfer.nmr.mgh.harvard.edu/fswiki/FsTutorial/PialEdits_freeview
    #
    # recon-all -autorecon-pial -subjid pial_edits_before

    # Volume plots
    #

    # Copy brainmask.mgz before editing it.

    qm_volumes = [ fsinfo['output']['volume']['T1']+':visible=0' ] 

    if os.path.isfile( fsinfo['output']['volume']['flair'] ):
        qm_volumes += [ fsinfo['output']['volume']['flair']+':visible=1' ]

    if os.path.isfile( fsinfo['output']['volume']['t2'] ):
        qm_volumes += [ fsinfo['output']['volume']['t2']+':visible=0' ]

    qm_volumes += [ fsinfo['output']['volume']['aseg'] + ':visible=1:colormap=lut:opacity=.8',
                    fsinfo['output']['volume']['brainmask'] + ':visible=0:colormap=jet:opacity=0.8',
                  ]

    qm_command = [ '-v' ] + qm_volumes

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
        methods_wm_volume(fsinfo, verbose)

    if 'wm_surface' in selected_method:
        methods_wm_surface(fsinfo, verbose)

    if 'wm_norm' in selected_method:
        methods_wm_norm(fsinfo, verbose)

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

    iw_subprocess(fs_command, True, True, True)

    return

def methods_recon_pial(fsinfo, verbose=False):

    logger.debug('methods_recon_pial()')

    fs_command = [ 'recon-all',
                  '-autorecon-pial', '-autorecon3',
                  '-sd', fsinfo['base']['subjects_dir'],
                  '-subjid', fsinfo['base']['subject_id'],
                  ]

    if fsinfo['input']['t2']:
        fs_command += ['-T2', fsinfo['input']['t2'], '-T2pial']

    if fsinfo['input']['flair']:
        fs_command += ['-FLAIR', fsinfo['input']['flair'], '-FLAIRpial']


    if verbose:
        print
        print(' '.join(fs_command))
        print

    iw_subprocess(fs_command, True, True, True)

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

    iw_subprocess(fs_command, True, True, True)

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

    if verbose:
        print
        print(' '.join(fs_command))
        print

    iw_subprocess(fs_command, True, True, True)

    return


#endregion


# ======================================================================================================================
# region RedCap UploadStatus

#def redcap_freesurfer_upload(subject_id, redcap_url, redcap_token, verbose):

#    s = Subject(subject_id) # where SUBJECTID is an identifier for a subject living in SUBJECTS_DIR
#    s.get_measures()
#    data = s.upload_dict()

#    if verbose:
#        print(' ')
#        print([subject_id, redcap_url, redcap_token])
#        print(' ')
#        print(data)
#        print(' ')

    # Using my PyCap package, you can then import the data into a REDCap project

#    p = Project(redcap_url, redcap_token)

#    data[p.def_field] = subject_id
#    response = p.import_records([data])



#endregion

# ======================================================================================================================
# region Status

def fslogs(selected_fslogs, fsinfo, verbose=False):

    logger = logging.getLogger(__name__)
    logger.debug('fslogs()')

    with open(fsinfo['logs'][selected_fslogs], 'r') as fin:
        print(fin.read())



def status_run( fsinfo, verbose ):


     result_files = [ fsinfo['output']['volume']['wmparc'] ]
     freesurfer_status_run = util.check_files(result_files, False)

     if verbose:
          print( fsinfo['base']['subject_id'] + ', ' + fsinfo['base']['subject_dir'] + ', run, ' + str(freesurfer_status_run) )

     return freesurfer_status_run


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

    parser.add_argument("--t1", help="T1w image NIFTI filename (default=None) ", default=None)    ## Parsing Arguments

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--t2", help="T2w image NIFTI filename (default=None) ", default=None)
    group.add_argument("--flair", help="T2w FLAIR NIFTI filename (default=None)", default=None)

    parser.add_argument('-m','--methods', help='Methods (recon-all, pial, wm_norm, wm_volume, wm_surface )',
                        nargs=1, choices=METHODS, default=[None])

    parser.add_argument("--qm", help="QA methods (mri, pial, wm_norm, wm_volume, wm_surface)", nargs='*', choices=QA_METHODS, default=[None])

    parser.add_argument("--status", help="Status check. choices=['run', 'results']", nargs='*',
                        choices=['results', 'run', 'all'], default=[None])

    FS_LOGS = ['log', 'status']

    parser.add_argument("--redcap", help="RedCap URL and Token", nargs=2, type=str, default = None)

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
    if 'run' in inArgs.status or 'all' in inArgs.status:
        status_run(fsinfo, True)


    # Upload Results to RedCap
    if inArgs.redcap:
        print(fsinfo['base']['subject_id'])

        redcap_freesurfer_upload(fsinfo['base']['subject_id'], inArgs.redcap[0], inArgs.redcap[1], inArgs.verbose)


    # QA of methods
    if inArgs.qm:
        logger.debug('QM logging statement')  # will not print anything
        qa_methods(inArgs.qm, fsinfo, inArgs.verbose)

    if inArgs.fslogs:

        fslogs(inArgs.fslogs, fsinfo, inArgs.verbose)


#endregion

if __name__ == "__main__":
    sys.exit(main())

