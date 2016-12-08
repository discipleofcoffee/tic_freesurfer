#!/usr/bin/env python

"""

"""
import shutil

import sys
import os                                               # system functions
import re
import json

import argparse
import iwUtilities as util
import subprocess

import nipype.interfaces.fsl as fsl
import nipype.interfaces.freesurfer as fs 
from   nipype.pipeline.engine import Workflow, Node

import datetime
import getpass
from collections import OrderedDict

def cp_file_with_timestamp(fname, suffix, user=getpass.getuser(), fmt='{fname}.{suffix}.{user}.d%Y%m%d_%H%M%S'):
    return datetime.datetime.now().strftime(fmt).format(fname=fname, suffix=suffix, user=user)



def get_info( in_freesurfer_id, in_freesurfer_subjects_dir=os.getenv('SUBJECTS_DIR'),  t1=None, t2=None, flair=None ):

     freesurfer_id           = in_freesurfer_id
     freesurfer_subjects_dir = in_freesurfer_subjects_dir
     freesurfer_subject_dir  = os.path.join( freesurfer_subjects_dir, freesurfer_id )

#     if os.path.isdir( freesurfer_subjects_dir ):
#          print('Freesurfer ' + freesurfer_subjects_dir + ' does not exist')
#          sys.exit()

#     if os.path.isdir( freesurfer_subject_dir ):
#          print('Freesurfer ' + freesurfer_subject_dir + 'does not exist')
#          sys.exit()

     input_files = OrderedDict( (( 't1', os.path.abspath(t1) if t1 else None), 
                                 ( 't2', os.path.abspath(t2) if t2 else None), 
                                 ( 'flair', os.path.abspath(flair) if flair else None)
                                 ) 
                                ) 
     
     base = OrderedDict( ( ('subject_id', freesurfer_id), 
                           ('subjects_dir', freesurfer_subjects_dir), 
                           ('subject_dir', freesurfer_subject_dir), 
                           ('mri', util.path_relative_to( freesurfer_subject_dir,'mri')),
                           ('surf', util.path_relative_to( freesurfer_subject_dir,'surf'))
                           )
                         )

     volume_files =  OrderedDict( (( 'T1', os.path.join( base['mri'], 'T1.mgz')),
                                   ( 'wm', os.path.join( base['mri'], 'wm.mgz')),
                                   ( 'nu', os.path.join( base['mri'], 'nu.mgz')),
                                   ( 'aseg' , os.path.join( base['mri'], 'aseg.mgz')),
                                   ( 'brainmask' , os.path.join( base['mri'], 'brainmask.mgz')),
                                   ( 'brain.finalsurfs', os.path.join( base['mri'], 'brain.finalsurfs.mgz')),
                                   ( 'a2009' , os.path.join( base['mri'], 'aparc.a2009s+aseg.mgz')),
                                   ( 'wmparc' , os.path.join( base['mri'], 'wmparc.mgz'))
                                   )
                                  )

     surface_lh_files = OrderedDict( (( 'white', os.path.join( base['surf'], 'lh.white')),
                                      ( 'pial', os.path.join( base['surf'], 'lh.pial')),
                                      ( 'inflated', os.path.join( base['surf'], 'lh.inflated'))
                                      )
                                     )

     surface_rh_files = OrderedDict( (( 'white', os.path.join( base['surf'], 'rh.white')),
                                      ( 'pial', os.path.join( base['surf'], 'rh.pial')),
                                      ( 'inflated', os.path.join( base['surf'], 'rh.inflated'))
                                      )
                                     )

     surface_files = OrderedDict( (( 'lh', surface_lh_files), ('rh', surface_rh_files )) )

     output_files = OrderedDict( (( 'volume', volume_files), ('surface', surface_files)))

     return  { 'base':base, 'input': input_files, 'output': output_files }  
                      


def main():
     ## Parsing Arguments
     #
     #

     usage = "usage: %prog [options] arg1 arg2"

     parser = argparse.ArgumentParser(prog='imcollective_freesurfer')

     parser.add_argument("subject_id",       help="Subject ID", default = os.getcwd() )
     parser.add_argument("--subjects_dir",   help="Subject's Directory (default=$SUBJECTS_DIR)", default = os.getenv('SUBJECTS_DIR') )

     parser.add_argument("--t1",       help="T1w image NIFTI filename (default=t1w.nii.gz) ", default = None)

     parser.add_argument("--t2",       help="T2w image NIFTI filename (default=None) ", default = None)
     parser.add_argument("--flair",   help="T2w FLAIR NIFTI filename (default=None)", default = None)

     parser.add_argument("--methods",             help="Freesurfer recon-all", action="store_true", default=False )
     parser.add_argument("--methods_recon_pial",  help="Freesurfer recon-all", action="store_true", default=False )

     parser.add_argument("--results",          help="Gather Freesurfer results",  action="store_true", default=False )
     parser.add_argument("--results_force",    help="Gather Freesurfer results",  action="store_true", default=False )

     parser.add_argument("--status",           help="Check Freesurfer status",  action="store_true", default=False )
     parser.add_argument("--status_methods",   help="Check Freesurfer methods status",  action="store_true", default=False )
     parser.add_argument("--status_results",   help="Check Freesurfer results status",  action="store_true", default=False )

     parser.add_argument('-v','--verbose', help="Verbose flag",  action="store_true", default=False )

     parser.add_argument('--qi', help="QA inputs",   action="store_true", default=False )
     parser.add_argument('--qm', help="QA methods",  action="store_true", default=False )
     parser.add_argument('--qm_edit_pial', help="QA methods",  action="store_true", default=False )
     parser.add_argument('--qr', help="QA results",  action="store_true", default=False )


     inArgs = parser.parse_args()

     # Select 

     fsinfo = get_info( inArgs.subject_id, inArgs.subjects_dir, inArgs.t1, inArgs.t2, inArgs.flair )
     
     if inArgs.verbose:
          print( json.dumps(fsinfo, indent=4))

     if inArgs.qi:
          qi( fsinfo, inArgs.verbose)

     if inArgs.methods:
          methods_recon_all( fsinfo, inArgs.verbose )

     if inArgs.methods_recon_pial:
          methods_recon_edit_pial( fsinfo, inArgs.verbose )

     if inArgs.results:

          if status_methods( fsinfo, False ):
               if not status_results(fsinfo, False) or inArgs.results_force:
                    results( fsinfo, inArgs.verbose)
               else:
                    print('cenc_freesurfer.py --results has already been methods')
                    sys.exit()
          else:
               print( 'imcollective_freesurfer.py --methods has not completed or still needs to be methods')
               sys.exit()

     if inArgs.status_methods or inArgs.status:
          status_methods(fsinfo, True)

     if inArgs.status_results or inArgs.status:
          status_results(fsinfo, True)

     if inArgs.qm:
          qm(fsinfo, inArgs.verbose)

     if inArgs.qm_edit_pial:
          qm_edit_pial(fsinfo, inArgs.verbose)
               

def qi( fsinfo, verbose=False ):

     input_files = filter( None, fsinfo['input'].values())

     if util.check_files( input_files):

          qi_command = [ 'freeview', '-v' ] + input_files
          
          if verbose:
               print(' '.join(qi_command))

          DEVNULL = open(os.devnull, 'wb')
          pipe = subprocess.Popen( [ ' '.join(qi_command) ], shell=True,
                                  stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL, close_fds=True)

     else:
          pass





def qa_methods_edit_pial( fsinfo, verbose=False):
     
     # https://surfer.nmr.mgh.harvard.edu/fswiki/FsTutorial/TroubleshootingData
     # https://surfer.nmr.mgh.harvard.edu/fswiki/FsTutorial/PialEdits_freeview
     #
     # recon-all -autorecon-pial -subjid pial_edits_before

     # Volume plots
     #

     # Copy brainmask.mgz before editing it. 
     shutil.copyfile(fsinfo['output']['volume']['brainmask'], 
                     cp_file_with_timestamp(fsinfo['output']['volume']['brainmask'], 'qm_edit_pial'))

     qm_volumes   = [ fsinfo['output']['volume']['T1'],
                      fsinfo['output']['volume']['brainmask']
                      ]

     qm_surfaces   = [ fsinfo['output']['surface']['lh']['white'] + ':edgecolor=yellow',
                       fsinfo['output']['surface']['lh']['pial']  + ':edgecolor=red',
                       fsinfo['output']['surface']['rh']['white'] + ':edgecolor=yellow',
                       fsinfo['output']['surface']['rh']['pial']  + ':edgecolor=red'
                       ]
                       

     qm_command   = ['freeview', '-v' ] + qm_volumes + [ '-f' ] + qm_surfaces

     if verbose:
          print
          print(' '.join(qm_command))
          print

     DEVNULL = open(os.devnull, 'wb')
     pipe = subprocess.Popen( [ ' '.join(qm_command) ], shell=True,
                              stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL, close_fds=True)


def qa_methods_recon( fsinfo, verbose=False):


     #
     # Volume plots
     #

     qm_volumes   = [ fsinfo['output']['volume']['T1'],
                      fsinfo['output']['volume']['wm'],
                      fsinfo['output']['volume']['brainmask'],
                      fsinfo['output']['volume']['aseg'] + ':colormap=lut:opacity=0.2' 
                      ]

     qm_surfaces   = [ fsinfo['output']['surface']['lh']['white'] + ':edgecolor=blue',
                       fsinfo['output']['surface']['lh']['pial']  + ':edgecolor=red',
                       fsinfo['output']['surface']['rh']['white'] + ':edgecolor=blue',
                       fsinfo['output']['surface']['rh']['pial']  + ':edgecolor=red'
                       ]
                       

     qm_command   = ['freeview', '-v' ] + qm_volumes + [ '-f' ] + qm_surfaces

     if verbose:
          print
          print(' '.join(qm_command))
          print

     DEVNULL = open(os.devnull, 'wb')
     pipe = subprocess.Popen( [ ' '.join(qm_command) ], shell=True,
                              stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL, close_fds=True)


     #
     # Surface plots
     #

     for ii in ['lh', 'rh']:
          qm_surfaces   = [ fsinfo['output']['surface'][ii]['white']     + ':annot=aparc.annot:name=pial_aparc:visible=0',
                            fsinfo['output']['surface'][ii]['inflated']  + ':overlay=lh.thickness:overlay_threshold=0.1,3::name=inflated_thickness:visible=0',
                            fsinfo['output']['surface'][ii]['inflated']  + ':visible=0',
                            fsinfo['output']['surface'][ii]['pial']      + ':edgecolor=red'
                            ]
     
          qm_command   = ['freeview', '-f' ] + qm_surfaces + [ '--viewport 3d' ]

          if verbose:
               print
               print(' '.join(qm_command))
               print

     DEVNULL = open(os.devnull, 'wb')
     pipe = subprocess.Popen( [ ' '.join(qm_command) ], shell=True,
     stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL, close_fds=True)




def methods_recon_all( fsinfo, verbose=False ):

     if verbose:
          print('recon_all')

     fs_command = [ 'recon-all', 
                    '-sd', fsinfo['base']['subjects_dir'],
                    '-subjid', fsinfo['base']['subject_id'],
                    '-all', 
                    '-qcache',
                    '-measure', 'thickness',
                    '-measure', 'curv',
                    '-measure', 'sulc',
                    '-measure', 'area',
                    '-measure', 'jacobian_white'
                    ]


     if not os.path.isdir(fsinfo['base']['subject_dir']):
          
          fs_command += [ '-i', fsinfo['input']['t1'] ]

          if fsinfo['input']['t2']:
               fs_command += [ '-T2', fsinfo['input']['t2'] ]

          if fsinfo['input']['flair']:
               fs_command += [ '-FLAIR', fsinfo['input']['flair'] ]

     if verbose:
          print
          print(' '.join(fs_command))
          print

     util.iw_subprocess( fs_command, True, True, True)

     return


def methods_recon_edit_pial( fsinfo, verbose=False ):

     if verbose:
          print
          print('methods_recon_edit_pial')
          print


     fs_command = [ 'recon-all', 
                    '-sd', fsinfo['base']['subjects_dir'],
                    '-subjid', fsinfo['base']['subject_id'],
                    '-autorecon-pial' 
                    ]

     if verbose:
          print
          print(' '.join(fs_command))
          print

     try:
          util.iw_subprocess( freesurfer_command, True, True, True)
     except:
          pass

     return


def qa_methods_recon_edit_pial( fsinfo, verbose=False ):

     if verbose:
          print
          print('methods_recon_edit_pial')
          print


     fs_command = [ 'recon-all', 
                    '-sd', fsinfo['base']['subjects_dir'],
                    '-subjid', fsinfo['base']['subject_id'],
                    '-autorecon-pial' 
                    ]

     if verbose:
          print
          print(' '.join(fs_command))
          print

     try:
          util.iw_subprocess( freesurfer_command, True, True, True)
     except:
          pass

     return


def results( input_dir, verbose):
     pass


def status_methods( input_dir, verbose ):
     pass


def status_results( input_dir, verbose ):
     pass


#
# Main Function
#

if __name__ == "__main__":
    sys.exit(main())

