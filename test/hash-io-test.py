import os, sys, getopt
sys.path.append('../include/sptensor/')

import hash

import time

def main(argv):

    file = sys.argv[1]
    #print('file: ', file)

    start_time = time.time()

    t = hash.read(file)
    #hash.write(sys.stdout, t)

    print("--- %s seconds ---" % (time.time() - start_time))
    
if __name__ == "__main__":
   main(sys.argv[1:])
