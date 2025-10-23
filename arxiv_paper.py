"""
Get arXiv papers
"""

import os
import json
import warnings
import arxiv
from tqdm import tqdm
from llm import is_paper_match, translate_abstract

warnings.filterwarnings('ignore')


def _coerce_total_results(value):
    """
    Safely convert the opensearch_totalresults field to an integer.
    """
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        value = value.strip()
        return int(value) if value else 0
    if isinstance(value, (list, tuple)):
        for item in value:
            try:
                return _coerce_total_results(item)
            except (TypeError, ValueError):
                continue
        raise ValueError('Unable to parse total results from iterable: {}'.format(value))
    if isinstance(value, dict):
        for key in ('#text', 'text', 'value'):
            if key in value:
                return _coerce_total_results(value[key])
        for item in value.values():
            try:
                return _coerce_total_results(item)
            except (TypeError, ValueError):
                continue
        raise ValueError('Unable to parse total results from mapping: {}'.format(value))
    raise TypeError('Unsupported type for total results: {}'.format(type(value)))


def _iter_results_with_fallback(client: arxiv.Client, search: arxiv.Search, max_results: int):
    """
    Iterate search results with a fallback that tolerates malformed feeds.
    """
    offset = 0
    yielded = 0
    total_results = None

    while True:
        page_url = client._format_url(search, offset, client.page_size)
        try:
            feed = client._parse_feed(page_url, first_page=(offset == 0))
        except Exception as exc:
            print('arXiv feed request failed ({}): {}'.format(search.query, exc))
            break
        entries = getattr(feed, 'entries', [])
        if not entries:
            break

        if total_results is None:
            raw_total = getattr(feed.feed, 'opensearch_totalresults', None)
            try:
                total_results = _coerce_total_results(raw_total)
            except Exception as exc:
                print('arXiv feed total result parse error ({}): {}'.format(search.query, exc))
                total_results = None

        for entry in entries:
            try:
                result = arxiv.Result._from_feed_entry(entry)
            except arxiv.Result.MissingFieldError as err:
                print('Skipping partial result ({}): {}'.format(search.query, err))
                continue
            yield result
            yielded += 1
            offset += 1
            if max_results and yielded >= max_results:
                return

        if total_results is not None and offset >= total_results:
            break


def _expand_segment(segment: str):
    """
    Expand a segment that may contain `/` alternatives into full phrase variants.
    """
    tokens = [token for token in segment.strip().split() if token]
    if not tokens:
        return []

    phrases = ['']
    for token in tokens:
        options = [opt.strip().lower() for opt in token.split('/') if opt.strip()]
        if not options:
            options = [token.lower()]
        new_phrases = []
        for base in phrases:
            for option in options:
                if base:
                    new_phrases.append('{} {}'.format(base, option))
                else:
                    new_phrases.append(option)
        phrases = new_phrases

    return [phrase for phrase in phrases if phrase]


def get_latest_papers(category, max_results=100):
    """
    Get the latest papers from arXiv
    :param category: the category of papers
    :param max_results: the maximum number of papers to get
    :return: a list of papers
    """
    papers = []
    client = arxiv.Client()
    search_query = f'cat:{category}'
    search = arxiv.Search(
        query=search_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    def _append_result(result_obj):
        paper_id = result_obj.get_short_id()
        version_pos = paper_id.find('v')
        if version_pos != -1:
            paper_id = paper_id[:version_pos]
        papers.append({
            'title': result_obj.title,
            'id': paper_id,
            'abstract': result_obj.summary.replace('\n', ' '),
            'url': result_obj.entry_id,
            'published': result_obj.published.date().isoformat()
        })

    try:
        for result in client.results(search):
            _append_result(result)
    except TypeError as exc:
        print('arXiv feed parse error for {}: {}. Retrying with fallback parser.'.format(category, exc))
        papers.clear()
        for result in _iter_results_with_fallback(client, search, max_results):
            _append_result(result)
    except ValueError as exc:
        print('arXiv feed value error for {}: {}. Retrying with fallback parser.'.format(category, exc))
        papers.clear()
        for result in _iter_results_with_fallback(client, search, max_results):
            _append_result(result)

    return papers


def deduplicate_papers_across_categories(papers):
    """
    Deduplicate papers across multiple categories
    :param papers: a list of papers
    :return: the deduplicated papers
    """
    # Deduplicate papers while maintaining the order
    # **Note**: Used in the case where multiple categories are involved
    papers_id = set()
    deduplicated_papers = []
    for paper in papers:
        if paper['id'] not in papers_id:
            papers_id.add(paper['id'])
            deduplicated_papers.append(paper)
    return deduplicated_papers


def filter_papers_by_keyword(papers, keyword_list):
    """
    Filter papers by keywords
    :param papers: a list of papers
    :param keyword_list: a list of keywords
    :return: a list of filtered papers
    """
    results = []
    normalized_keywords = []

    for keyword in keyword_list:
        if not keyword:
            continue
        groups = []
        segments = [segment.strip() for segment in keyword.split('+') if segment.strip()]
        if not segments:
            variants = _expand_segment(keyword)
            if variants:
                groups.append(variants)
        else:
            for segment in segments:
                variants = _expand_segment(segment)
                if variants:
                    groups.append(variants)
        if groups:
            normalized_keywords.append(groups)

    for paper in papers:
        searchable_text = '{} {}'.format(paper['title'], paper['abstract']).lower()
        if any(all(any(alt in searchable_text for alt in group) for group in keyword_groups) for keyword_groups in normalized_keywords):
            results.append(paper)
    return results


def filter_papers_using_llm(papers, paper_to_hunt, config: dict):
    """
    Filter papers using LLM
    :param papers: a list of papers
    :param paper_to_hunt: the prompt describing the paper to hunt for
    :param config: the configuration of LLM Server
    :return: a list of filtered papers
    """
    results = []
    for paper in papers:
        if is_paper_match(paper, paper_to_hunt, config):
            results.append(paper)
    return results


def deduplicate_papers(papers, file_path):
    """
    Deduplicate papers according to the previous records
    :param papers: a list of papers
    :param file_path: the file path of the previous records
    :return: the deduplicated papers
    """
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if content:
            content = json.loads(content)
            # Filter out the duplicated papers by id
            content_id = set(d['id'] for d in content)
            papers = [d for d in papers if d['id'] not in content_id]
    # if len(set(d['id'] for d in papers)) == len(papers):
    #     return papers
    return papers


def prepend_to_json_file(file_path, data):
    """
    Prepend data to a JSON file
    :param file_path: the file path
    :param data: the data to prepend
    """
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if content:
            content = json.loads(content)
        else:
            content = []
    else:
        content = []

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data + content, f, indent=4, ensure_ascii=False)


def translate_abstracts(papers: list, config: dict):
    """
    Translate the abstracts using the specified translation service
    :param papers: a list of papers
    :param config: the configuration of LLM Server
    :return: the translated papers
    """
    for paper in tqdm(papers, desc='Translating Abstracts'):
        abstract = paper["abstract"]
        zh_abstract = translate_abstract(abstract, config)
        paper["zh_abstract"] = None
        if zh_abstract:
            paper["zh_abstract"] = zh_abstract
    return papers


if __name__ == '__main__':
    papers = get_latest_papers('cs.CL', max_results=50)
    print(json.dumps(papers, indent=4))
    print()
    keyword_list = ['safety', 'security', 'adversarial', 'jailbreak', 'backdoor', 'hallucination', 'victim']
    results = filter_papers_by_keyword(papers, keyword_list)
    print(json.dumps(results, indent=4))
    print()
    results = deduplicate_papers(results, 'papers.json')
    print(json.dumps(results, indent=4))
    print()
    prepend_to_json_file('papers.json', results)
