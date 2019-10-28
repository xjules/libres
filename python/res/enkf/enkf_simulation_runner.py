from cwrap import BaseCClass
from ecl.util.util import BoolVector
from res import ResPrototype
from res.enkf import EnkfFs
from res.enkf import ErtRunContext
from res.enkf import EnKFState
from res.enkf.enums import EnkfInitModeEnum
from res.enkf.enums.realization_state_enum import RealizationStateEnum
from res.job_queue import RunStatusType, JobQueueManager, JobQueueNode

import time
import threading

class EnkfSimulationRunner(BaseCClass):
    TYPE_NAME = "enkf_simulation_runner"

    _create_run_path = ResPrototype("bool enkf_main_create_run_path(enkf_simulation_runner, ert_run_context)")
    _run_simple_step = ResPrototype("int enkf_main_run_simple_step(enkf_simulation_runner, job_queue, ert_run_context)")

    def __init__(self, enkf_main):
        assert isinstance(enkf_main, BaseCClass)
        # enkf_main should be an EnKFMain, get the _RealEnKFMain object
        real_enkf_main = enkf_main.parent()
        super(EnkfSimulationRunner, self).__init__(
            real_enkf_main.from_param(real_enkf_main).value ,
            parent=real_enkf_main ,
            is_reference=True)

    def _enkf_main(self):
        return self.parent()

    def runSimpleStep(self, job_queue, run_context):
        """ @rtype: int """
        #### run simplestep ####
        self._enkf_main().initRun(run_context)

        if run_context.get_step():
            ecl_config = self._enkf_main().ecl_config.assert_restart()

        #### deselect load and parent failure #####
        iactive = run_context.get_mask()

        run_context.get_sim_fs().getStateMap().deselectMatching( iactive,
            RealizationStateEnum.STATE_LOAD_FAILURE | RealizationStateEnum.STATE_PARENT_FAILURE)
        
        #### start queue ####
        self.start_queue(run_context, job_queue)

        #### deactivate failed realizations ####
        totalOk = 0
        totalFailed = 0
        for i in range(len(run_context)):
            if run_context.is_active(i):
                run_arg = run_context[i]
                if run_arg.run_status == RunStatusType.JOB_LOAD_FAILURE or run_arg.run_status == RunStatusType.JOB_RUN_FAILURE:
                    run_context.deactivate_realization(i)
                    totalFailed += 1
                else:
                    totalOk += 1

        run_context.get_sim_fs().fsync()

        ## Should be converted tp a looger
        if (totalFailed == 0):
             print("All {} active jobs complete and data loaded.".format( totalOk ));
        else:
             print("{} active job(s) failed.".format(totalFailed));

        return totalOk


    def createRunPath(self, run_context):
        """ @rtype: bool """
        return self._create_run_path(run_context)

    def runEnsembleExperiment(self, job_queue, run_context):
        """ @rtype: int """
        return self.runSimpleStep(job_queue, run_context)

    @staticmethod
    def runWorkflows( runtime, ert):
        """:type res.enkf.enum.HookRuntimeEnum"""
        hook_manager = ert.getHookManager()
        hook_manager.runWorkflows(runtime  , ert)


    def add_job(self, run_arg, res_config, job_queue):
        job_name = run_arg.job_name
        run_path = run_arg.runpath
        job_script = res_config.queue_config.job_script
        num_cpu = res_config.queue_config.num_cpu
        if num_cpu == 0:
            num_cpu = res_config.ecl_config.num_cpu
        job = JobQueueNode(job_script=job_script, job_name=job_name, run_path=run_path, num_cpu=num_cpu,
                            status_file=job_queue.status_file, ok_file=job_queue.ok_file, exit_file=job_queue.exit_file,
                            done_callback_function=EnKFState.forward_model_ok_callback,
                            exit_callback_function=EnKFState.forward_model_exit_callback,
                            callback_arguments=[run_arg, res_config])
        
        if job is None:
            return
        run_arg._set_queue_index(job_queue.add_job(job))

    def start_queue(self, run_context, job_queue):
        # submit jobs
        for i in range(len(run_context)):
            if not run_context.is_active(i):
                continue
            run_arg = run_context[i]
            self.add_job(run_arg, self._enkf_main().resConfig(), job_queue)
            

        job_queue.submit_complete()
        max_runtime = self._enkf_main().analysisConfig().get_max_runtime() 
        job_queue.set_max_job_duration(max_runtime)

        jqm = JobQueueManager(job_queue)
        jqm.execute_queue()
