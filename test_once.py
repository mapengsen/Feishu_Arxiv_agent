"""
Main Script
"""

import argparse
import datetime
import os
import warnings
from arxiv_paper import get_latest_papers, deduplicate_papers_across_categories, filter_papers_by_keyword, filter_papers_using_llm, deduplicate_papers, prepend_to_json_file, translate_abstracts
from lark_post import post_to_lark_webhook
from utils import load_config

warnings.filterwarnings('ignore')


DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.yaml')


def parse_args():
    parser = argparse.ArgumentParser(description='Fetch latest arXiv papers and post to Lark webhook.')
    parser.add_argument('-c', '--config', default=DEFAULT_CONFIG_PATH, help='Path to configuration YAML file.')
    return parser.parse_args()


def task(config: dict):
    """
    Main task: Fetch Papers & Post to Lark Webhook
    """
    tag = config['tag']
    category_list = config['category_list']
    keyword_list = config['keyword_list']
    use_llm_for_filtering = config['use_llm_for_filtering']
    use_llm_for_translation = config['use_llm_for_translation']

    paper_file = os.path.join(os.path.dirname(__file__), 'papers.json')
    paper_to_hunt = None
    if use_llm_for_filtering:
        with open(os.path.join(os.path.dirname(__file__), 'paper_to_hunt.md'), 'r', encoding='utf-8') as f:
            paper_to_hunt = f.read()

    today_date = datetime.date.today().strftime('%Y-%m-%d')
    print('Task: {}'.format(today_date))

    papers = []
    for category in category_list:
        papers.extend(get_latest_papers(category, max_results=100))
    print('Total papers: {}'.format(len(papers)))

    # Deduplicate papers across categories
    papers = deduplicate_papers_across_categories(papers)
    print('Deduplicated papers across categories: {}'.format(len(papers)))

    if keyword_list:
        papers = filter_papers_by_keyword(papers, keyword_list)
    print('Filtered papers by Keyword: {}'.format(len(papers)))

    if use_llm_for_filtering:
        papers = filter_papers_using_llm(papers, paper_to_hunt, config)
        print('Filtered papers by LLM: {}'.format(len(papers)))

    papers = deduplicate_papers(papers, paper_file)
    print('Deduplicated papers: {}'.format(len(papers)))

    if use_llm_for_translation:
        papers = translate_abstracts(papers, config)
        print('Translated Abstracts into Chinese')

    prepend_to_json_file(paper_file, papers)

    # Post to Lark Webhook
    post_to_lark_webhook(tag, papers, config)


def main():
    args = parse_args()
    config = load_config(args.config)
    task(config)


if __name__ == '__main__':
    # Run the task immediately
    main()
