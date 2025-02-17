import logging

import requests
from typing import Tuple, Optional, Literal, Union
from collections import defaultdict
from io import BytesIO
from datetime import datetime

from .vault_tools import AnyProject, VaultClient


class LokiLogFetcher:
    available_data_structures = [list, dict]

    @classmethod
    def from_project(cls, project: AnyProject, **kwargs):
        kwargs.pop('url', None)
        url = cls.make_url(project, **kwargs)
        return cls(url=url, **kwargs)

    @staticmethod
    def make_url(project_or_id: AnyProject = None, api_path: str = '/api/v1/query_range', **kwargs) -> str:
        secrets: dict = VaultClient(project=project_or_id).get_all_secrets()
        loki_host: str = secrets['loki_host']
        return f'{loki_host}/loki{api_path}'

    def __init__(self, url: Optional[str] = None, date_format: str = "%Y-%m-%d %H:%M:%S",
                 query_limit: int = 5000, next_chunk_step_ns: int = 1, data_parse_structure: type = list) -> None:
        assert data_parse_structure in self.available_data_structures, f'This data structure is not supported {data_parse_structure}. Use one of these: {self.available_data_structures}'
        if not url:
            url = self.make_url()
            logging.warning('Loki url is not specified. Will generate default one: %s', url)
        self.url = url
        self.date_format = date_format
        self.query_limit = query_limit
        self.next_chunk_step_ns = next_chunk_step_ns
        self.data_parse_structure = data_parse_structure
        if data_parse_structure is list:
            self._logs = []
        elif data_parse_structure is dict:
            self._logs = defaultdict(set)
        self._result = None

    def fetch_logs(self, query: str, start: int = 0, fetch_all: bool = True,
                   direction: Literal['forward', 'backward'] = 'forward') -> None:
        self._result = None
        params = {
            'limit': self.query_limit,
            'direction': direction,
            'start': start,
            'query': query
        }
        # logging.info('QQQWWW %s | %s', self.url, params)
        resp = requests.get(
            self.url,
            params=params
        )
        result = resp.json()
        length, last_item_time_ns = self._unpack_response(result)
        if fetch_all and length == self.query_limit:
            last_log_time_ns = last_item_time_ns + self.next_chunk_step_ns
            self.fetch_logs(query=query, start=last_log_time_ns)

    def _unpack_response(self, response_data: dict) -> Tuple[int, int]:
        length = 0
        time_peak = 0
        for i in response_data['data']['result']:
            for v in i['values']:
                time_ns, message = v
                time_ns = int(time_ns)
                time_peak = max(time_peak, time_ns)
                if isinstance(self._logs, list):
                    self._logs.append((time_ns, message))
                elif isinstance(self._logs, dict):
                    self._logs[time_ns].add(message)
                length += 1
        return length, time_peak

    @property
    def logs(self) -> list:
        if not self._result:
            if isinstance(self._logs, list):
                self._result = list(map(
                    lambda x: (datetime.fromtimestamp(x[0] / 1e9).strftime(self.date_format), x[1]),
                    sorted(self._logs, key=lambda x: x[0])
                ))
            elif isinstance(self._logs, dict):
                self._result = []
                for t, v in sorted(self._logs.items(), key=lambda x: x[0]):
                    t = datetime.fromtimestamp(t / 1e9).strftime(self.date_format)
                    for i in v:
                        self._result.append((t, i))
        return self._result

    def to_file(self, file: Optional[BytesIO] = None, enc: str = 'utf-8', do_seek: bool = True) -> BytesIO:
        if not file:
            file = BytesIO()
        for log in self.logs:
            file.write(
                f'{log[0]}\t{log[1]}\n'.encode(enc)
            )
        if do_seek:
            file.seek(0)
        return file
