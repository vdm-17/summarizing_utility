from configparser import ConfigParser
import sys


class InvalidInputFileException(Exception):
    def __init__(self, message: str):
        super().__init__()
        self.message = message


class InvalidOutputFileException(Exception):
    def __init__(self, message: str):
        super().__init__()
        self.message = message


def get_config():
    config = ConfigParser()
    config.read('config.ini', 'utf-8')

    return config


def get_sys_argv_flag_val(short_flag: str, long_flag: str, expected_values: tuple):
    for i in range(1, len(sys.argv)):
        if sys.argv[i] == short_flag or sys.argv[i] == long_flag:
            if i+1 >= len(sys.argv):
                return None
            
            if sys.argv[i+1] in expected_values:
                return sys.argv[i+1]
            
            return None

        if sys.argv[i].startswith(short_flag + '='):
            val = sys.argv[i][len(short_flag)+1:]

            if val in expected_values:
                return val
            
            return None
        
        if sys.argv[i].startswith(long_flag + '='):
            val = sys.argv[i][len(long_flag)+1:]

            if val in expected_values:
                return val
            
            return None

    return None


def get_inout_files_pathes():
    input_file_path: str | None = None
    output_file_path: str | None = None

    is_last_argv_flag = False

    for i in range(1, len(sys.argv)):
        if is_last_argv_flag:
            if not sys.argv[i].startswith('-'):
                is_last_argv_flag = False
            
            continue

        if sys.argv[i].startswith('-'):
            is_last_argv_flag = True
            continue
        else:
            is_last_argv_flag = False

        if input_file_path == None:
            input_file_path = sys.argv[i]
            continue

        output_file_path = sys.argv[i]

        return (input_file_path, output_file_path)
    
    if input_file_path == None:
        raise InvalidInputFileException('Input file is not specified.')
    
    raise InvalidOutputFileException('Output file is not specified.')


def save_content(file_path: str, content: str):
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
