#!/usr/bin/env python3
"""
Periodic Runner
"""

import argparse
import datetime
import os
import time
import warnings
from typing import Optional

import schedule

from utils import load_config

warnings.filterwarnings('ignore')

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.yaml')


def parse_args():
    parser = argparse.ArgumentParser(description='Run the arXiv fetch task on a daily schedule.')
    parser.add_argument('-c', '--config', default=DEFAULT_CONFIG_PATH, help='Path to configuration YAML file.')
    parser.add_argument('--schedule-time', help='Daily trigger time (HH:MM, 24-hour format). Omit to run immediately and exit.')
    return parser.parse_args()


def validate_schedule_time(schedule_time: str) -> str:
    try:
        datetime.datetime.strptime(schedule_time, '%H:%M')
    except ValueError as exc:
        raise ValueError('Invalid schedule time `{}`; expected HH:MM 24-hour format.'.format(schedule_time)) from exc
    return schedule_time


def run_periodic(config_path: str, schedule_time: Optional[str]) -> None:
    from main import task  # 延迟导入以避免循环依赖

    config = load_config(config_path)
    if not schedule_time:
        print('Running task immediately (no schedule_time provided).')
        task(config)
        return

    validated_time = validate_schedule_time(schedule_time)
    schedule.clear()
    schedule.every().day.at(validated_time).do(task, config=config)
    print('Scheduled daily task at {}'.format(validated_time))

    while True:
        schedule.run_pending()
        time.sleep(1)


def main():
    args = parse_args()
    run_periodic(config_path=args.config, schedule_time=args.schedule_time)


if __name__ == '__main__':
    main()
