from dotenv import load_dotenv
from os import getenv
from app.utils import get_config
from app.params import WorkMode, DetailsMode
from pydantic import BaseModel, Field
from agents import Agent, Runner, FileSearchTool, ModelSettings
from agents.model_settings import Reasoning
from agents.run import RunConfig
from openai import OpenAI
import asyncio

load_dotenv()

APP_ENV = getenv('APP_ENV')
OPENAI_API_KEY = getenv('OPENAI_API_KEY')

config = get_config()

SUMMARIZING_AGENT_OPENAI_MODEL = config['DEFAULT']['SUMMARIZING_AGENT_OPENAI_MODEL']
SUMMARIZING_AGENT_REASONING_EFFORT = config['DEFAULT']['SUMMARIZING_AGENT_REASONING_EFFORT']
SUMMARIZING_AGENT_VERBOSITY = config['DEFAULT']['SUMMARIZING_AGENT_VERBOSITY']

SUMMARIZING_AGENT_INSTRUCTIONS = (
    'Ты бот, составляющий конспекты. Твоя задача - формулировать и составлять '
    'конспект по переданному в виде файла материалу в формате {output_format}. '
    'Подробность должна быть {details}. В процессе конспектирования ты должен '
    'разбивать материал на подтемы. {additional_instructions}'
)

LOW_DETAILS_INSTRUCTIONS = 'низкой'
MEDIUM_DETAILS_INSTRUCTIONS = 'средней'
HIGH_DETAILS_INSTRUCTIONS = 'высокой'
XHIGH_DETAILS_INSTRUCTIONS = 'максимальной'

CLASSIC_OUTPUT_FORMAT_INSTRUCTIONS = 'свободного текста'
QUESTIONS_OUTPUT_FORMAT_INSTRUCTIONS = 'вопросов для самопроверки и ответов к ним'

CLASSIC_OUTPUT_FORMAT_ADDITIONAL_INSTRUCTIONS = \
    'В ответ отправляй текст, соответствующий формату файла с расширением {file_extension}.'

QUESTIONS_OUTPUT_FORMAT_ADDITIONAL_INSTRUCTIONS = (
    'Количество вопросов для каждой подтемы должно определяться содержанием '
    'материала, а не простой общей установкой. Вопросы не должны непосредственно '
    'ссылаться на сам материал, с которого те были взяты. В ответ отправляй '
    'последовательный список объектов, где у каждого объекта будут следующие поля: '
    'текст подтемы, с которой был взят вопрос, номер подтемы в тексте, начиная с 1, '
    'сам вопрос, ответ на соответствующий вопрос, список из номеров страниц в '
    'предоставленном материале, с которых был взят ответ на соответсвующий вопрос, '
    'и непосредственный фрагмент в тексте, откуда был взят ответ на вопрос.'
)


class QuestionsSummarizingAgentItemOutputSchema(BaseModel):
    subtheme_text: str = Field(
        description=(
            'Текст подтемы из предоставленного материала, с которой был взят вопрос. '
            'Если подтема отсутствует, вместо нее должна использоваться строка "Главные".'
        )
    )
    subtheme_index: int = Field(
        description=(
            'Номер подтемы, из которой был взят вопрос, в предоставленном материале. '
            'Номер должен быть целым числом, а отсчет должен начинаться с 1.'
        )
    )
    question: str = Field(
        description='Вопрос, составленный по предоставленному материалу и соответсвующий подтеме.'
    )
    answer: str = Field(
        description='Правильный ответ на соответсвующий вопрос, взятый из предоставленного материала и указанной подтемы.'
    )
    answer_source_pages: list[int] = Field(
        description='Список из номеров страниц в предоставленном материале, с которых был взят соответсвующий ответ на вопрос.'
    )
    answer_source_fragment: str = Field(
        description='Фрагмент текста в предоставленном материале, из которого был взят соответсвующий ответ на вопрос.'
    )


QuestionsSummarizingAgentOutput = list[QuestionsSummarizingAgentItemOutputSchema]
ClassicSummarizingAgentOutput = str

SummarizingAgentOutput = QuestionsSummarizingAgentOutput | ClassicSummarizingAgentOutput


def get_summarizing_agent_instructions(
    work_mode: WorkMode, 
    details_mode: DetailsMode, 
    output_file_path: str
):
    if details_mode == 'low':
        details_instructions = LOW_DETAILS_INSTRUCTIONS
    elif details_mode == 'medium':
        details_instructions = MEDIUM_DETAILS_INSTRUCTIONS
    elif details_mode == 'high':
        details_instructions = HIGH_DETAILS_INSTRUCTIONS
    else:
        details_instructions = XHIGH_DETAILS_INSTRUCTIONS
    
    if work_mode == 'questions':
        output_format_instructions = QUESTIONS_OUTPUT_FORMAT_INSTRUCTIONS
        additional_instructions = QUESTIONS_OUTPUT_FORMAT_ADDITIONAL_INSTRUCTIONS
    else:
        output_format_instructions = CLASSIC_OUTPUT_FORMAT_INSTRUCTIONS
        additional_instructions = CLASSIC_OUTPUT_FORMAT_ADDITIONAL_INSTRUCTIONS.format(
            file_extension=f'.{output_file_path.split('.')[-1]}'
        )
    
    return SUMMARIZING_AGENT_INSTRUCTIONS.format(
        details=details_instructions,
        output_format=output_format_instructions,
        additional_instructions=additional_instructions
    )


def get_summarizing_agent_output_type(work_mode: WorkMode):
    if work_mode == 'questions':
        return QuestionsSummarizingAgentOutput
    else:
        return ClassicSummarizingAgentOutput


class SummarizingAgent(Agent):
    def __init__(self, name: str, instructions: str, output_type: SummarizingAgentOutput):
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        openai_vector_store = openai_client.vector_stores.create()

        super().__init__(
            name=name, 
            instructions=instructions,
            tools=[FileSearchTool(vector_store_ids=[openai_vector_store.id])],
            model=SUMMARIZING_AGENT_OPENAI_MODEL,
            model_settings=ModelSettings(
                reasoning=Reasoning(effort=SUMMARIZING_AGENT_REASONING_EFFORT),
                verbosity=SUMMARIZING_AGENT_VERBOSITY,
                store=False
            ),
            output_type=output_type
        )

        self.openai_client = openai_client
        self.openai_vector_store = openai_vector_store
    
    def __del__(self):
        self.openai_client.vector_stores.delete(self.openai_vector_store.id) 
    
    def get_summary(self, file_path: str):
        with open(file_path, 'rb') as f:
            openai_file = self.openai_client.files.create(
                file=f,
                purpose='user_data',
            )
        
        self.openai_client.vector_stores.files.create(
            vector_store_id=self.openai_vector_store.id,
            file_id=openai_file.id,
        )

        agent_input = [
            {
                'role': 'user',
                'content': [
                    {'type': 'input_file', 'file_id': openai_file.id},
                ],
            }
        ]

        if APP_ENV == 'development':
            tracing_disabled = False
        else:
            tracing_disabled = True
        
        response = asyncio.run(
            Runner.run(self, agent_input, run_config=RunConfig(tracing_disabled=tracing_disabled))
        )

        agent_output: SummarizingAgentOutput = response.final_output

        if type(agent_output) == str:
            return agent_output
        
        summary = '# Вопросы для самопроверки\n'
        writed_subthemes_indexes = set()
    
        i = 1
        for item in sorted(agent_output, key=lambda i: i.subtheme_index):
            if item.subtheme_index not in writed_subthemes_indexes:
                summary += f'## {item.subtheme_text}\n'
                writed_subthemes_indexes.add(item.subtheme_index)

            link_to_file = f'file:///{file_path}'
            pages = ', '.join([str(i) for i in item.answer_source_pages])

            summary += (
                f'\n{i}. {item.question} ||{item.answer}|| [Источник.]({link_to_file}) '
                f'Страницы: {pages}. Фрагмент в тексте: ||{item.answer_source_fragment}||\n'
            )

            i += 1
    
        return summary
