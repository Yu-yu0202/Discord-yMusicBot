import os

CACHE_DIR = "./cache"
TARGET_SIZE_GB = 3

def get_directory_size(directory):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

def get_sorted_files(directory):
    files = []
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            files.append({
                'path': filepath,
                'created': os.path.getctime(filepath),
                'size': os.path.getsize(filepath)
            })
    
    return sorted(files, key=lambda x: x['created'])

def manage_cache_size():
    current_size = get_directory_size(CACHE_DIR)
    target_size_bytes = TARGET_SIZE_GB * (1024**3)
    
    print(f"Current cache size: {current_size / (1024**3):.2f} GB")
    print(f"Target cache size: {TARGET_SIZE_GB} GB")
    files = get_sorted_files(CACHE_DIR)

    deleted_files = []
    for file in files:
        if current_size > target_size_bytes:
            try:
                os.remove(file['path'])
                deleted_files.append(file)
                current_size -= file['size']
                print(f"Deleted: {file['path']}, Size: {file['size'] / (1024**2):.2f} MB")
            except Exception as e:
                print(f"Error deleting {file['path']}: {e}")
        else:
            break
    
    print(f"\nDeleted {len(deleted_files)} files")
    return current_size

final_size = manage_cache_size()
print(f"Final cache size: {final_size / (1024**3):.2f} GB")