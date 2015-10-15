import os
import os.path
import platform
import sys

import dcos.constants
import dcos.util
from dcos.subcommand import package_dir

def kubectl_binary_path_and_url(master):
    # get kubectl meta json
    import requests
    meta_url = master + "/static/kubectl-meta.json"
    try:
        meta = requests.get(meta_url).json()
    except:
        raise Exception("Cannot download kubectl meta information from {0}".format(meta_url))

    # get url
    system, node, release, version, machine, processor = platform.uname()
    arch = "amd64" # we only support amd64 for the moment
    key = system.lower() + "-" + arch
    if key not in meta:
        raise Exception("System type {0} not supported".format(key))
    url = master + "/static/" + meta[key]["file"] + ".bz2"
    hash = meta[key]["sha256"]

    # create filename
    data_dir = package_dir("kubernetes")
    base = os.path.join(data_dir, "kubectl")
    file_path = base + "-" + hash
    if system == "Windows":
        file_path += ".exe"

    return file_path, url

def read_in_chunks(file_object, chunk_size=1024):
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data

def download_kubectl(url, kubectl_path):
    import tarfile

    with dcos.util.temptext() as (fd, file_path):
        try:
            # download bz2 file and decompress in time
            print "Download kubectl from " + url
            from clint.textui import progress
            import urllib2, bz2
            f = urllib2.urlopen(url)
            decompressor = bz2.BZ2Decompressor()
            total_length = int(f.info().getheader("Content-Length"))
            chunk_num = int(total_length/1024) + 1
            chunks = read_in_chunks(f, chunk_size=1024)
            for chunk in progress.bar(chunks, expected_size=chunk_num):
                if chunk:
                    os.write(fd, decompressor.decompress(chunk))

            # move binary at right spot and make executable
            os.rename(file_path, kubectl_path)
            if not kubectl_path.endswith(".exe"):
                os.chmod(kubectl_path, 0755)

        except tarfile.TarError, e:
            os.unlink(kubectl_path)
            print "Error while opening kubectl tar file: " + str(e)
            sys.exit(2)

        except Exception, e:
            print "Error while downloading kubectl binary: " + str(e)
            sys.exit(2)


def main():
    # skip "kubernetes" command
    if len(sys.argv) > 1 and sys.argv[1] in ["kubernetes", "kubectl"]:
        args = sys.argv[2:]
    else:
        args = sys.argv[1:]

    # special --info case
    if len(args) == 1 and args[0] == "--info":
        print("Deploy and manage pods on Kubernetes")
        sys.exit(0)

    # get api url
    config = dcos.util.get_config()
    dcos_url = config.get('core.dcos_url', None)
    if dcos_url is None or dcos_url == "":
        print("Error: dcos core.dcos_url is not set")
        sys.exit(2)

    # check whether kubectl binary exists and download if not
    import urlparse
    master = urlparse.urljoin(dcos_url, "service/kubernetes")
    try:
        kubectl_path, kubectl_url = kubectl_binary_path_and_url(master)
    except Exception, e:
        print("Error: " + str(e))
        return 2
    if not os.path.exists(os.path.dirname(kubectl_path)):
        print "create"
        os.makedirs(os.path.dirname(kubectl_path))
    if not os.path.exists(kubectl_path):
        download_kubectl(kubectl_url, kubectl_path)

    # call kubectl with parameters
    from subprocess import call
    env = os.environ.copy()
    if 'KUBERNETES_MASTER' in env:
        del env['KUBERNETES_MASTER']
    rc = call([kubectl_path, "--server=" + master + "/api"] + args, env=env)
    sys.exit(rc)


if __name__ == "__main__":
    cfg = os.path.join(os.getenv("HOME"), dcos.constants.DCOS_DIR, "dcos.toml")
    os.environ[dcos.constants.DCOS_CONFIG_ENV] = cfg
    main()
