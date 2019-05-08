
import asyncio
from datetime import datetime
import base64
import raftos
import logging

from rest_api import BoatAPI
from atomic_queue import AtomicQueue
from clipper import Clipper

import os, multiprocessing

class Boat:
    def __init__(self, num_nodes, node_id, start_time): 
        # Add member
        self.num_nodes = num_nodes
        self.node_id = node_id
        self.start_time = start_time

        # Submitted requests via Rest API
        # Inside: { 'time': str, 'request': str }
        self.api_queue = AtomicQueue()
        # Requests to send to Clipper
        # Inside: str
        self.clipper_queue = AtomicQueue()

        # Retrieve asyncio loop
        self.loop = asyncio.get_event_loop()

        # Configure raftos

        self.raft_node = '127.0.0.1:{}'.format(8000+self.node_id)
        self.raft_cluster = ['127.0.0.1:{}'.format(8000+i) for i in range(num_nodes) if i != self.node_id]

        timestamp = base64.b64encode(str(self.start_time).encode()).decode()
        
        os.makedirs('./logs', exist_ok=True)
        os.makedirs('./logs/{}'.format(timestamp), exist_ok=True)
        
        raftos.configure({
            'log_path': './logs/{}'.format(timestamp),
            'serializer': raftos.serializers.JSONSerializer,
            'on_receive_append_entries_callback': self.on_receive_append_entries_callback
        })
    
        # Configure Clipper
        self.clipper = Clipper(self.node_id)

        # Configure REST API
        self.rest_api = BoatAPI(self, '127.0.0.1', 8080+self.node_id)


    # Everything about async goes here
    def run(self):
        # Start Clipper
        self.clipper.run()

        # Schedule Rest API
        self.loop.create_task(self.rest_api.run(self.loop))
        
        # Schedule main loop
        self.loop.create_task(self.main_loop())

        # Schedule clipper feeding
        self.loop.create_task(self.clipper_feeder())

        # Blocking call to run the asyncio loop
        logging.info('Boat {}: Running. API listening to {}:{}'.format(
            self.node_id, self.rest_api.addr, self.rest_api.port))
        self.loop.run_forever()

    # As leader
    async def main_loop(self):
        '''Main loop'''
        await raftos.register(self.raft_node, cluster=self.raft_cluster)
        data_list = raftos.ReplicatedList(name='requests')

        while True:
            # Check whether there is something in the request queue
            rs = await self.api_queue.wait_and_dequeue_all()

            # We can also check if raftos.get_leader() == node_id
            await raftos.wait_until_leader(self.raft_node)

            for r in rs:
                # Broadcast the request send to prediction
                try:
                    await data_list.append(r)
                    logging.info('Boat {}: Request from API appended to state: {}'.format(self.node_id, r))
                    await self.clipper_queue.enqueue_and_notify(r['request'])
                except:
                    print('Boat {}: Failed to append to state: {}'.format(self.node_id, r))
        
        await raftos.wait_until_leader(self.raft_node)
    
    # As follower
    def on_receive_append_entries_callback(self, command):
        '''Callback function for updates from Raft

           Request sent to Clipper'''
        
        if ('requests' in command) and command['requests']:
            # Update from leader received
            logging.info('Boat {}: Request received from raft: {}'.format(self.node_id, command['requests'][-1]))
            # Send to Clipper
            self.loop.create_task(self.clipper_queue.enqueue_and_notify(command['requests'][-1]['request']))
        else:
            logging.info('Boat {}: Update from raft received with invalid format'.format(self.node_id))


    async def clipper_feeder(self):
        while True:
            r = await self.clipper_queue.wait_and_dequeue()
            await self.clipper.predict(r)


    # API
    async def post_predict(self, request):
        '''Put the incoming request into the queue with timestamp'''
        data_map = {
            'time': str(datetime.now()),
            'request': request
        }
        await self.api_queue.enqueue_and_notify(data_map)

    # API
    async def get_status(self):
        return { 'is_leader': raftos.get_leader() == self.raft_node }
        
