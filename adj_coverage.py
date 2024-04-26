import ribopy
from ribopy import Ribo
from functions import get_cds_range_lookup, get_psite_offset
import numpy as np
import multiprocessing
import time
import pickle
import logging
import math

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to lazily load transcripts one at a time
def transcript_generator(ribo_object):
    for transcript in ribo_object.transcript_names:
        yield transcript.split("|")[4]

# Function to process a single transcript and return coverage
def process_transcript(transcript, exp, min_len, max_len, alias, cds_range, ribo_path):
    try:
        # Initialize a new Ribo object within the worker process
        ribo_object = Ribo(ribo_path, alias=ribopy.api.alias.apris_human_alias)
        
        start, stop = cds_range[transcript]
        if start < offset:
            return transcript, None

        offset = get_psite_offset(ribo_object, exp, min_len, max_len)

        coverages = [
            ribo_object.get_coverage(experiment=exp, range_lower=i, range_upper=i, alias=alias)
            [transcript][start - offset[i] : stop - offset[i]]
            for i in range(min_len, max_len + 1)
        ]
        coverage = sum(coverages, np.zeros_like(coverages[0]))
    
        return transcript, coverage
    except Exception as e:
        logging.error(f"Error processing transcript {transcript}: {e}")
        return transcript, None

# Wrapper function to pass to multiprocessing.Pool.imap_unordered
def process_wrapper(args):
    return process_transcript(*args)

if __name__ == '__main__':
    try:
        # Initialize variables
        ribo_path = input("Ribo file path: ")
        exp = input("Experiment: ")
        min_len = int(input("Minimum read length: "))
        max_len = int(input("Maximum read length: "))
        alias = True
        ribo_object = Ribo(ribo_path, alias=ribopy.api.alias.apris_human_alias)
        cds_range = get_cds_range_lookup(ribo_object)

        # Initialize an empty dictionary to store transcript coverage
        coverage_dict = {}

        # Parallelize transcript processing
        with multiprocessing.Pool() as pool:
            for transcript, coverage in pool.imap_unordered(
                    process_wrapper,
                    [(t, exp, min_len, max_len, alias, cds_range,  ribo_path) for t in transcript_generator(ribo_object)]
                ):
                # Accumulate the coverage for each transcript in the dictionary
                coverage_dict[transcript] = coverage

        # Write the coverage dictionary to the output file
        output_file = f'coverage_{exp}_28.pkl'
        with open(output_file, 'wb') as f:
            pickle.dump(coverage_dict, f)

    except Exception as e:
        logging.error(f"An error occurred: {e}")

    finally:
        logging.info("Program finished.")