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

# Initialize variables
min_len = 26
max_len = 30
exp = 'WT_control_A'
alias = True
ribo_path = f'/home/reiko/ribopy_analysis/mouse/data/merged.ribo'
output_file = f'/home/reiko/ribopy_analysis/mouse/data/coverage_{exp}.pkl'
ribo_object = Ribo(ribo_path, alias=ribopy.api.alias.apris_human_alias)
cds_range = get_cds_range_lookup(ribo_object)
offset = get_psite_offset(ribo_object, exp, min_len, max_len)
transcript_list = [transcript.split("|")[4] for transcript in ribo_object.transcript_names]

def get_adj_coverage(ribo_object, transcript, exp, min_len, max_len, alias, cds_range, offset):
    start, stop = cds_range[transcript]
    if start < max(offset.values()):
        return None
    
    coverages = [
        ribo_object.get_coverage(experiment=exp, range_lower=i, range_upper=i, alias=alias)
        [transcript][start - offset[i] : stop - offset[i]]
        for i in range(min_len, max_len + 1)
    ]

    coverage = sum(coverages, np.zeros_like(coverages[0]))
    return coverage
    
def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def get_adj_coverage_parallel(transcript_list, num_cores):
    batch_size = math.ceil(len(transcript_list) / num_cores)
    transcript_batches = list(chunks(transcript_list, batch_size))
    with multiprocessing.Pool(processes=num_cores) as pool:
        results = pool.map(process_transcript, transcript_batches)
    return results

# Modify the process_transcript function to handle batches of transcripts
def process_transcript(transcript_batch):
    logging.info(f"Begin processing {len(transcript_batch)} transcripts...")
    start_time = time.time()
    results = {}
    for transcript in transcript_batch:
        try:
            coverage = get_adj_coverage(ribo_object, transcript, exp, min_len, max_len, alias, cds_range, offset)
            results[transcript] = coverage
        except Exception as e:
            logging.error(f"Error processing transcript {transcript}: {e}")
            results[transcript] = None
    end_time = time.time()
    elapsed_time = end_time - start_time
    logging.info(f"Processed {len(transcript_batch)} transcripts in {elapsed_time} seconds")
    return results

if __name__ == '__main__':
    start_time = time.time()
    try:
        logging.info("Starting the program...")

        # Parallelize coverage calculation
        adj_coverage_batches = get_adj_coverage_parallel(transcript_list, num_cores=multiprocessing.cpu_count())

        # Combine results from batches
        adj_coverage_dict = {}
        for batch_results in adj_coverage_batches:
            adj_coverage_dict.update(batch_results)

        # Write results to output file
        with open(output_file, 'wb') as f:
            pickle.dump(adj_coverage_dict, f)

    except Exception as e:
        logging.error(f"An error occurred: {e}")

    finally:
        logging.info("Program finished.")
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Time taken: {elapsed_time} seconds")