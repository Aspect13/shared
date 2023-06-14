#   Copyright 2021 getcarrier.io
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

""" Module """
from pylon.core.tools import module, log  # pylint: disable=E0611,E0401


class Module(module.ModuleModel):
    """ Galloper module """

    def __init__(self, context, descriptor):
        self.context = context
        self.descriptor = descriptor
        self.db = None
        self.mongo = None
        self.job_type_rpcs = set()

    def init(self):
        """ Init module """
        log.info("Initializing module Shared")

        from .tools.rpc_tools import RpcMixin, EventManagerMixin
        RpcMixin.set_rpc_manager(self.context.rpc_manager)
        EventManagerMixin.set_manager(self.context.event_manager)

        from .tools import constants
        self.descriptor.register_tool('constants', constants)

        from .tools.config import Config
        self.descriptor.register_tool('config', Config())

        from .tools import rpc_tools, api_tools
        self.descriptor.register_tool('rpc_tools', rpc_tools)
        self.descriptor.register_tool('api_tools', api_tools)

        from .tools.loki_tools import LokiLogFetcher
        self.descriptor.register_tool('LokiLogFetcher', LokiLogFetcher)

        from .tools import db
        self.db = db
        self.descriptor.register_tool('db', db)

        from .tools import db_tools, db_migrations
        self.descriptor.register_tool('db_tools', db_tools)
        self.descriptor.register_tool('db_migrations', db_migrations)

        # self.context.app.config.from_object(self.config)
        from .init_db import init_db
        init_db()

        @self.context.app.teardown_appcontext
        def shutdown_session(exception=None):
            db.session.remove()

        from .tools.minio_client import MinioClient, MinioClientAdmin
        self.descriptor.register_tool('MinioClient', MinioClient)
        self.descriptor.register_tool('MinioClientAdmin', MinioClientAdmin)

        from .tools.vault_tools import VaultClient
        self.descriptor.register_tool('VaultClient', VaultClient)
        VaultClient.init_vault()  # won't do anything if vault is not available

        from .tools import data_tools
        self.descriptor.register_tool('data_tools', data_tools)

        self.init_filters()

        self.descriptor.register_tool('shared', self)

        self.descriptor.init_api()

    def deinit(self):  # pylint: disable=R0201
        """ De-init module """
        log.info("De-initializing module Shared")

    def init_filters(self):
        # Register custom Jinja filters
        from .filters import tag_format, extract_tags, list_pd_to_json, \
            map_method_call, pretty_json, humanize_timestamp, format_datetime
        self.context.app.template_filter()(tag_format)
        self.context.app.template_filter()(extract_tags)
        self.context.app.template_filter()(list_pd_to_json)
        self.context.app.template_filter()(map_method_call)
        self.context.app.template_filter()(pretty_json)
        self.context.app.template_filter()(humanize_timestamp)
        self.context.app.template_filter()(format_datetime)
