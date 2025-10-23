"""
HTTP POST request to Lark Webhook API
"""

import json
import datetime
import warnings
import requests

warnings.filterwarnings('ignore')


def _chunk_papers(papers, batch_size):
    """
    Yield (offset, chunk) pairs where `offset` starts from zero.
    """
    for offset in range(0, len(papers), batch_size):
        yield offset, papers[offset:offset + batch_size]


def post_to_lark_webhook(tag: str, papers: list, config: dict):
    headers = {
        'Content-Type': 'application/json'
    }

    if not papers:
        print("No papers to send; skipping Lark webhook call.")
        return

    today_date = datetime.date.today().strftime('%Y-%m-%d')
    batch_size = config.get('lark_batch_size', 10)
    total_batches = (len(papers) + batch_size - 1) // batch_size

    for batch_index, (offset, chunk) in enumerate(_chunk_papers(papers, batch_size), start=1):
        table_rows = []
        for i, paper in enumerate(chunk):
            table_rows.append({
                "index": offset + i + 1,
                "title": paper['title'],
                "published": paper['published'],
                "url": f"[{paper['url']}]({paper['url']})"
            })
        paper_list = [
            {
                "counter": offset + i + 1,
                "title": paper['title'],
                "abstract": paper['abstract'],
                "zh_abstract": paper.get('zh_abstract', None),
                "url": paper['url'],
                "published": paper['published']
            }
            for i, paper in enumerate(chunk)
        ]

        card_data = {
            "type": "template",
            "data": {
                "template_id": config['template_id'],
                "template_version_name": config['template_version_name'],
                "template_variable": {
                    "today_date": today_date,
                    "tag": tag,
                    "total_paper": len(chunk),
                    "table_rows": table_rows,
                    "paper_list": paper_list,
                    "batch_index": batch_index,
                    "batch_total": total_batches
                }
            }
        }

        data = {
            "msg_type": "interactive",
            "card": card_data
        }

        response = requests.post(config['webhook_url'], headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            print("Request successful (batch {}/{})".format(batch_index, total_batches))
            print("Response:\n{}".format(response.json()))
        else:
            print("Request failed for batch {}, status code: {}".format(batch_index, response.status_code))
            print("Response:\n{}".format(response.text))
            break


if __name__ == '__main__':
    papers = [
        {
            'title': 'Title 1',
            'id': '1234567890',
            'abstract': 'Abstract 1',
            'url': 'https://arxiv.org/abs/1234567890',
            'published': '2021-01-01',
            'zh_abstract': None
        },
        {
            'title': 'Title 2',
            'id': '2345678901',
            'abstract': 'Abstract 2',
            'url': 'https://arxiv.org/abs/2345678901',
            'published': '2021-01-02',
            'zh_abstract': '中文摘要 2'
        }
    ]
    from utils import load_config
    config = load_config()
    post_to_lark_webhook('test', papers, config)
