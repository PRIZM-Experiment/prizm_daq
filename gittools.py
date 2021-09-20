import subprocess

def get_hash():
    hash_long = subprocess.check_output(['git', 'rev-parse', 'HEAD']).strip().decode("utf-8")
    dirty = False
    try: 
        out = subprocess.check_output(["git", "diff-index", "--quiet", "HEAD"])
    except subprocess.CalledProcessError:
        dirty = True
    if dirty:
        return hash_long+" (modified)"
    else:
        return hash_long
