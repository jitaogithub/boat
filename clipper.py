from clipper_admin import ClipperConnection, DockerContainerManager, exceptions
from clipper_admin.deployers import python as python_deployer

import aiohttp

# Simple model: echo the input
def echo_model(x):
    return x

class Clipper:
    def __init__(self, node_id):
        self.node_id = node_id
        self.clipper_conn = ClipperConnection(DockerContainerManager(
            cluster_name='clipper_cluster_{}'.format(node_id),
            docker_ip_address='localhost',
            clipper_query_port=1337+node_id,
            clipper_management_port=2337+node_id,
            clipper_rpc_port=7000+node_id,
            redis_ip=None,
            redis_port=6379+node_id,
            prometheus_port=9090+node_id,
            docker_network='clipper_network_{}'.format(node_id),
            extra_container_kwargs={}))
    
        self.is_running = False

    def run(self):
        # Start Clipper
        try:
            self.clipper_conn.start_clipper()
            self.clipper_conn.register_application(name="default", input_type="string", default_output="", slo_micros=100000)
            
            python_deployer.deploy_python_closure(self.clipper_conn, name="echo-model", version=1, input_type="string", func=echo_model)
            self.clipper_conn.link_model_to_app(app_name="default", model_name="echo-model")

            self.is_running = True
        except:
            print('Boat {}: Exception thrown during Clipper startup. Cleaning up.'.format(self.node_id))
            self.stop()

    def stop(self):
        try:
            self.clipper_conn.stop_all()
        except:
            pass

    async def predict(self, request):
        session = aiohttp.ClientSession()
        resp = await session.post('http://127.0.0.1:{}/default/predict'.format(1337+self.node_id), 
            headers={'Content-Type': 'application/json'}, data=request.encode())
        print('Boat {}: {} sent to clipper with status {}\n\twith response:{}'.format(
            self.node_id, request, resp.status, await resp.text()))
        resp.close()
