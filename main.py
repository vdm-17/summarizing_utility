from app.params import get_work_mode, get_details_mode
from app.summarizing_agent import (
    get_summarizing_agent_instructions, get_summarizing_agent_output_type, SummarizingAgent
)
from app.utils import get_inout_files_pathes, save_content


def main():
    work_mode = get_work_mode()
    details_mode = get_details_mode()

    input_file_path, output_file_path = get_inout_files_pathes()

    instructions = get_summarizing_agent_instructions(work_mode, details_mode, output_file_path)
    output_type = get_summarizing_agent_output_type(work_mode)

    summarizing_agent = SummarizingAgent('Бот, составляющий конспекты', instructions, output_type)

    print('Программа составляет конспект, ожидайте.')

    summary = summarizing_agent.get_summary(input_file_path)
    
    save_content(output_file_path, summary)

    print(f'\nФайл с конспектом успешно сохранен по пути {output_file_path}')


if __name__ == '__main__':
    main()
