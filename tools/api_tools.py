#     Copyright 2020 getcarrier.io
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
import operator
from json import loads
from typing import Union, Optional, Callable, Tuple

from pylon.core.tools import log
from sqlalchemy import and_, SQLColumnExpression
from flask_restful import Resource, abort

from .minio_client import MinioClient, MinioClientAdmin
from .rpc_tools import RpcMixin
from .constants import DEFAULT_MODE


def prepare_filter(
        project_id: Optional[int], args: dict, data_model,
        additional_filters: Optional[list] = None,
        rpc_manager: Optional[Callable] = None,
        mode: str = DEFAULT_MODE
        ) -> SQLColumnExpression:
    filter_ = []
    try:
        filter_.append(operator.eq(data_model.mode, mode))
    except AttributeError:
        ...

    if mode == 'default':
        if not rpc_manager:
            rpc_manager = RpcMixin().rpc
        project = rpc_manager.call.project_get_or_404(project_id=project_id)
        filter_.append(operator.eq(data_model.project_id, project.id))

    if additional_filters:
        filter_.extend(additional_filters)
        # for key, value in additional_filter.items():
        #     filter_.append(operator.eq(getattr(data_model, key), value))

    if args.get('filter'):
        for key, value in loads(args.get('filter')).items():
            filter_.append(operator.eq(getattr(data_model, key), value))

    filter_ = and_(*filter_)
    return filter_


def get(project_id: Optional[int], args: dict, data_model,
        additional_filters: Optional[list] = None,
        rpc_manager: Optional[Callable] = None,
        mode: str = 'default',
        custom_filter: Optional[SQLColumnExpression] = None
        ) -> Tuple[int, list]:
    def _calculate_limit(limit: Union[str, int], total: int):
        return total if limit == 'All' or limit == 0 else limit

    limit_ = args.get("limit")
    offset_ = args.get("offset")
    if args.get("sort"):
        sort_rule = getattr(getattr(data_model, args["sort"]), args["order"])()
    else:
        sort_rule = data_model.id.desc()

    if custom_filter is None:
        filter_ = prepare_filter(project_id, args, data_model, additional_filters, rpc_manager, mode)
    else:
        filter_ = custom_filter

    total = data_model.query.order_by(sort_rule).filter(filter_).count()
    res = data_model.query.filter(
        filter_
    ).order_by(
        sort_rule
    ).limit(
        _calculate_limit(limit_, total)
    ).offset(
        offset_
    ).all()

    return total, res


def upload_file_base(bucket: str, data: bytes, file_name: str, client, create_if_not_exists: bool = True) -> None:
    if create_if_not_exists:
        if bucket not in client.list_bucket():
            bucket_type = 'system' if bucket in ('tasks', 'tests') else 'local'
            client.create_bucket(bucket=bucket, bucket_type=bucket_type)
    client.upload_file(bucket, data, file_name)


def upload_file(bucket: str, 
                f, 
                project: Union[str, int, 'Project'], 
                integration_id: Optional[int] = None, 
                is_local: bool = True,
                create_if_not_exists: bool = True, 
                **kwargs) -> None:
    if isinstance(project, (str, int)):
        mc = MinioClient.from_project_id(project_id=project, 
                                         integration_id=integration_id, 
                                         is_local=is_local)
    else:
        mc = MinioClient(project=project, 
                         integration_id=integration_id, 
                         is_local=is_local)

    upload_file_base(
        bucket=bucket,
        data=f.read(),
        file_name=f.filename,
        client=mc,
        create_if_not_exists=create_if_not_exists
    )
    try:
        f.remove()
    except:
        pass


def upload_file_admin(bucket: str, 
                      f, 
                      integration_id: Optional[int] = None, 
                      create_if_not_exists: bool = True, 
                      **kwargs) -> None:
    upload_file_base(
        bucket=bucket,
        data=f.read(),
        file_name=f.filename,
        client=MinioClientAdmin(integration_id),
        create_if_not_exists=create_if_not_exists
    )
    try:
        f.remove()
    except:
        pass


class APIBase(Resource):
    mode_handlers = dict()
    url_params = list()

    def proxy_method(self, method: str, mode: str = 'default', **kwargs):
        log.info(
            'Calling proxy method: [%s] mode: [%s] | %s',
            method, mode, kwargs
        )
        try:
            return getattr(self.mode_handlers[mode](self, mode), method)(**kwargs)
        except KeyError:
            abort(404)

    def __init__(self, module):
        self.module = module
        log.info('APIBase INIT %s | %s', self.mode_handlers, self.url_params)

    def get(self, **kwargs):
        return self.proxy_method('get', **kwargs)

    def post(self, **kwargs):
        return self.proxy_method('post', **kwargs)

    def put(self, **kwargs):
        return self.proxy_method('put', **kwargs)

    def delete(self, **kwargs):
        return self.proxy_method('delete', **kwargs)

    def patch(self, **kwargs):
        return self.proxy_method('patch', **kwargs)


class APIModeHandler:
    def __init__(self, api: Resource, mode: str = 'default'):
        self._api = api
        self.mode = mode

    def __getattr__(self, item):
        try:
            return self.__dict__[item]
        except KeyError:
            if item in ['get', 'post', 'put', 'delete', 'head', 'options', 'patch']:
                abort(404)
            return getattr(self._api, item)


def build_api_url(
        plugin: str, file_name: str, mode: str = 'default',
        api_version: int = 1, trailing_slash: bool = False
):
    return f"/api/v{api_version}/{plugin}/{file_name}/{mode}{'/' if trailing_slash else ''}"
