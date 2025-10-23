"""
Utility Functions
"""

import os
import warnings
from typing import Optional

import yaml
from openai import OpenAI

warnings.filterwarnings('ignore')


def load_config(config_path: Optional[str] = None):
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    if not os.path.isabs(config_path):
        config_path = os.path.abspath(config_path)
    if not os.path.exists(config_path):
        raise FileNotFoundError('Configuration file not found at {}'.format(config_path))
    with open(config_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)


def validate_llm_server_config(config: dict) -> dict:
    """
    Validate the configuration of LLM Server
    """
    fields = ['model', 'base_url', 'api_key']
    for field in fields:
        if field not in config:
            raise ValueError('Missing field `{}` in the configuration'.format(field))
    llm_server_config = {
        'model': config['model'],
        'base_url': config['base_url'],
        'api_key': config['api_key']
    }
    if not llm_server_config['api_key']:
        llm_server_config['api_key'] = 'ollama'  # Default for ollama service (any non-empty string)
    return llm_server_config


def get_llm_response(prompt: str, config: dict):
    """
    Get LLM response
    :param prompt: user prompt
    :param config: LLM Server configuration, fields include `model`, `base_url`, `api_key` etc.
    :return: the response content or None if failed
    """
    llm_server_config = validate_llm_server_config(config)
    model = llm_server_config['model']
    base_url = llm_server_config['base_url']
    api_key = llm_server_config['api_key']

    generation_config = {
        # 'temperature': 0.0,
        # 'top_p': 1.0,
        'stream': False,
    }

    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    messages = [
        {
            'role': 'user',
            'content': prompt
        },
    ]
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            **generation_config
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print('LLM Server Error: {}'.format(e))
        return None


if __name__ == '__main__':
    config = load_config()
    print(config)
