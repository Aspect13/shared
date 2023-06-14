from queue import Empty
from pylon.core.tools import log
from ...tools.api_tools import APIBase, APIModeHandler


class ProjectApi(APIModeHandler):
    def get(self, project_id: int):
        resp = {
            'public_regions': [],
            'project_regions': [],
            'cloud_regions': []
        }
        try:
            resp['public_regions'] = self.module.context.rpc_manager.timeout(
                3
            ).get_rabbit_queues("carrier", True)
        except Empty:
            log.warning('Cannot get %s for project [%s]', 'public_regions', project_id)
        try:
            resp['project_regions'] = self.module.context.rpc_manager.timeout(
                3
            ).get_rabbit_queues(f"project_{project_id}_vhost")
        except Empty:
            log.warning('Cannot get %s for project [%s]', 'project_regions', project_id)
        try:
            resp['cloud_regions'] = self.module.context.rpc_manager.timeout(
                3
            ).integrations_get_cloud_integrations(
                project_id
            )
        except Empty:
            log.warning('Cannot get %s for project [%s]', 'cloud_regions', project_id)
            # return resp, 400
        return resp, 200


class AdminApi(APIModeHandler):
    def get(self, **kwargs):
        try:
            public_regions = self.module.context.rpc_manager.timeout(3).get_rabbit_queues("carrier", True)
        except Empty:
            log.warning('Cannot get %s for administration', 'public_regions')
            public_regions = []
        return {
            'public_regions': public_regions,
            'project_regions': [],
            'cloud_regions': []
        }, 200


class API(APIBase):
    url_params = [
        '<int:project_id>',
        '<string:mode>/<string:project_id>',
    ]

    mode_handlers = {
        'default': ProjectApi,
        'administration': AdminApi,
    }
