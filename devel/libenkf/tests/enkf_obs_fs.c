/*
   Copyright (C) 2014  Statoil ASA, Norway. 
    
   The file 'enkf_obs_fs.c' is part of ERT - Ensemble based Reservoir Tool. 
    
   ERT is free software: you can redistribute it and/or modify 
   it under the terms of the GNU General Public License as published by 
   the Free Software Foundation, either version 3 of the License, or 
   (at your option) any later version. 
    
   ERT is distributed in the hope that it will be useful, but WITHOUT ANY 
   WARRANTY; without even the implied warranty of MERCHANTABILITY or 
   FITNESS FOR A PARTICULAR PURPOSE.   
    
   See the GNU General Public License at <http://www.gnu.org/licenses/gpl.html> 
   for more details. 
*/
#include <stdlib.h>
#include <stdio.h>

#include <ert/enkf/enkf_obs.h>
#include <ert/enkf/ert_test_context.h>
#include <ert/enkf/meas_data.h>
#include <ert/enkf/obs_data.h>
#include <ert/enkf/local_obsset.h>

#include <ert/util/test_util.h>


void testS(const char * config_file ) {
  const char * site_config = NULL;
  ert_test_context_type * test_context = ert_test_context_alloc( "ENKF_OBS_FS" , config_file , site_config );
  {
    enkf_main_type * enkf_main = ert_test_context_get_main( test_context );
    enkf_obs_type * enkf_obs = enkf_main_get_obs( enkf_main );
    enkf_fs_type * fs = enkf_main_get_fs( enkf_main );
    int_vector_type * step_list = int_vector_alloc(0,0);
    int_vector_type * active_list = int_vector_alloc(0,0);
    obs_data_type * obs_data = obs_data_alloc( );
    local_obsset_type * obs_set = local_obsset_alloc( "OBSNAME" );
    meas_data_type * meas_data;
    int active_size = 0;
    

    {
      for (int i= 0; i < enkf_main_get_ensemble_size( enkf_main); i++)
        int_vector_append( active_list , i );
      active_size = int_vector_size( active_list );
    }
    {
      for (int s = 0; s < enkf_main_get_history_length( enkf_main ); s++)
        int_vector_append( step_list , s );
    }

    meas_data = meas_data_alloc( active_list );
    obs_data = obs_data_alloc( );

    enkf_obs_get_obs_and_measure( enkf_obs , fs , step_list , FORECAST , active_list , enkf_main_get_ensemble_const( enkf_main ) , meas_data , obs_data , obs_set);
    {
      FILE * stream = util_fopen("analysis/Smatrix" , "r");
      matrix_type * S = meas_data_allocS( meas_data , active_size );
      matrix_type * S0 = matrix_fread_alloc( stream );

      test_assert_true( matrix_equal( S0 , S ));

      matrix_free( S );
      matrix_free( S0 );
      fclose( stream );
    }
    int_vector_free( step_list );
    int_vector_free( active_list );
    meas_data_free( meas_data );
    obs_data_free( obs_data );
    local_obsset_free( obs_set );
  }


  ert_test_context_free( test_context );
}



int main(int argc , char ** argv) {
  const char * config_file = argv[1];

  testS( config_file );

  exit(0);
}
