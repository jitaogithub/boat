import argparse, multiprocessing, logging, signal, os, datetime, functools

from boat import Boat

def sigterm_handler(self, signal, frame):
        logging.info('Boat {}: SIGTERM received. Please wait for the cleanup to finish.'.format(self.node_id))
        self.clipper.stop()
        logging.info('Boat {}: Cleanup finished. Quitting.'.format(self.node_id))
        exit(1)

# Entry point for every process
def main(num_nodes, node_id, start_time):
    boat = Boat(num_nodes, node_id, start_time)
    # Clipper must be explicitly killed or it will be left running
    signal.signal(signal.SIGTERM, functools.partial(sigterm_handler, boat))
    boat.run()

if __name__ == "__main__":
    # signal.signal(signal.SIGINT, sigint_handler)

    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--num_nodes', type=int, default=3)
    args = parser.parse_args()

    # Multiprocessing
    processes = set()
    try:
        start_time = datetime.datetime.now()
        for i in range(args.num_nodes):
            p = multiprocessing.Process(target=main, args=(args.num_nodes, i, start_time))
            logging.info('Main Process: Starting Boat {} ...'.format(i))
            p.start()
            logging.info('Main Process: ... Process started.')
            processes.add(p)
 
        while processes:
            for process in tuple(processes):
                process.join()
                processes.remove(process)
  
    # For any exception (including KeyboardInterrupt)
    finally:
        # Send SIGTERM to every process
        for process in processes:
            if process.is_alive():
                logging.info('Main Process: Terminating Boat {}'.format(process))
                process.terminate()
        
        # Wait for processes to finish the cleanup
        while processes:
            for process in tuple(processes):
                process.join()
                processes.remove(process)
