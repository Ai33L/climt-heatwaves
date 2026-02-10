import os
from minio import Minio
from concurrent.futures import ProcessPoolExecutor

def upload(runs):
    
    # --- MinIO connection ---
    client = Minio(
        "192.168.1.237:9000",
        access_key="d0d250b2541ac33f4660",
        secret_key="2fb32d964768bc94a3c0",
        secure=False
    )

    # --- Configuration ---
    bucket = "climt-long-runs"
    
    for run in runs:

        # local base directory
        local_base = f"/scratch/steveleonpadua/aqua-planet/regrid-data/run{run}/"

        # remote prefix inside MinIO
        remote_base = f"aqua-planet/regrid-data/run{run}/"

        # --- Walk through everything under local_base ---
        for root, dirs, files in os.walk(local_base):
            for filename in files:
                local_file = os.path.join(root, filename)

                # keep relative path the same
                rel_path = os.path.relpath(local_file, local_base)
                object_name = os.path.join(remote_base, rel_path).replace("\\", "/")

                # upload file
                client.fput_object(bucket, object_name, local_file)
                print(f"Uploaded {local_file} -> {bucket}/{object_name}", flush=True)


if __name__ == "__main__":
    runs = [list(range(i, i+5)) for i in range(1, 51, 5)]
    with ProcessPoolExecutor(max_workers=10) as executor:
        executor.map(upload, runs)
