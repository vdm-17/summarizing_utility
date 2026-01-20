from typing import Literal
from app.utils import get_sys_argv_flag_val

WorkMode = Literal['classic', 'questions']
DetailsMode = Literal['low', 'medium', 'high', 'xhigh']

EXPECTED_WORK_MODES = ('classic', 'questions')
EXPECTED_DETAILS_MODES = ('low', 'medium', 'high', 'xhigh')

DEFAULT_WORK_MODE = 'classic'
DEFAULT_DETAILS_MODE = 'medium'


def get_work_mode() -> WorkMode:
    flag_val = get_sys_argv_flag_val('-m', '--mode', EXPECTED_WORK_MODES)

    if flag_val != None:
        return flag_val
    
    return DEFAULT_WORK_MODE


def get_details_mode() -> DetailsMode:
    flag_val = get_sys_argv_flag_val('-d', '--details', EXPECTED_DETAILS_MODES)

    if flag_val != None:
        return flag_val
    
    return DEFAULT_DETAILS_MODE
