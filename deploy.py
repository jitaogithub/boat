import argparse, multiprocessing, logging, signal, os, datetime, subprocess

from boat import Boat

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%y-%m-%d:%H:%M:%S',
    level=logging.INFO)

logger = logging.getLogger(__name__)
    
# Entry point for every process
def main(num_nodes, node_id, start_time):
    boat = Boat(num_nodes, node_id, start_time)
    boat.run()

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--num_nodes', type=int, default=3)
    args = parser.parse_args()

    # Start Clipper with a separate Python script, or Clipper does not work properly
    logging.info('Main Process: Starting Clipper instances ...')
    clipper_success = 0
    for i in range(args.num_nodes):
        clipper_success += subprocess.call(['python3', 'clipper.py', str(i)])
    if clipper_success == 0:
        logging.info('Main Process: ... Clipper instances started.')
    else:
        logging.fatal('Main Process: Error occurred on Clipper startup. Cleaning up.')
        for i in range(args.num_nodes):
            subprocess.call(['sh', 'reset.sh', str(i)])
        logging.info('Main Process: Cleanup finished. Bye-bye.')
        exit(1)

    # Multiprocessing
    processes = set()
    try:
        start_time = datetime.datetime.now()
        for i in range(args.num_nodes):
            logging.info('Main Process: Creating Boat {} ...'.format(i))
            p = multiprocessing.Process(target=main, args=(args.num_nodes, i, start_time))
            p.start()
            processes.add(p)
            logging.info('Main Process: ... Boat {} created and triggered.'.format(i))
 
        while processes:
            for p in tuple(processes):
                p.join()
                processes.remove(p)

    # For any exception (including KeyboardInterrupt)
    finally:
        # Send SIGTERM to every process
        for p in processes:
            if p.is_alive():
                logging.info('Main Process: Terminating Boat {}. '.format(p))
                p.terminate()
        
        # Wait for processes to finish the cleanup
        while processes:
            for p in tuple(processes):
                p.join()
                processes.remove(p) 

        logging.info('Main Process: All boats terminated. Please wait for cleanup. This may take several minutes.')
        cleanup_success = 0
        for i in range(args.num_nodes):
            cleanup_success += subprocess.call(['sh', 'reset.sh', str(i)])
        if cleanup_success == 0:
            logging.info('Main Process: Cleanup finished. Bye-bye.')
        else:
            logging.error('Main Process: Error occurred on cleanup. Bye-bye anyway.')
        exit(0)
        