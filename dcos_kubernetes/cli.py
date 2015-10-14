import os
import os.path
import platform
import sys

import dcos.constants
import dcos.util
from dcos.subcommand import package_dir

def kubectl_binary_path_and_url(master):
    # get kubectl meta json
    import requests, json
    meta = requests.get(master + "/static/kubectl-meta.json")
    meta_json = json.loads(meta)

    # get url
    system, node, release, version, machine, processor = platform.uname()
    if system == "Linux":
        os = "linux"
    elif system == "Darwin":
        os = "darwin"
    elif system == "Windows":
        os = "windows"
    arch = "amd64" # we only support amd64 for the moment
    key = os + "-" + arch
    if key not in meta_json:
        raise Exception("System type %1 not supported".format(key))
    url = master + "/static/" + meta_json[key].file
    hash = meta_json[key].sha256

    # create filename
    data_dir = package_dir("kubernetes")
    base = os.path.join(data_dir, "kubectl")
    file = base + "-" + hash
    if system == "Windows":
        file += ".exe"

    return file, url

def read_in_chunks(file_object, chunk_size=1024):
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data


def download_kubectl(url, kubectl_path):
    import tarfile

    with dcos.util.temptext() as (fd, tar_file_path):
        try:
            # download tar.gz
            print "Download kubectl from " + url
            from clint.textui import progress
            import urllib2
            f = urllib2.urlopen(url)
            total_length = int(f.info().getheader("Content-Length"))
            chunk_num = int(total_length/1024) + 1
            chunks = read_in_chunks(f, chunk_size=1024)
            for chunk in progress.bar(chunks, expected_size=chunk_num):
                if chunk:
                    os.write(fd, chunk)

            # unarchive kubectl from tar.gz
            tar_file = tarfile.open(tar_file_path, mode="r:gz")
            tar_file.getmembers()
            kubectl_tar_file = tar_file.extractfile("kubectl")
            kubectl_file = open(kubectl_path, 'wb')
            kubectl_file.write(kubectl_tar_file.read())
            kubectl_tar_file.close()
            tar_file.close()

            # make executable
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
    if len(sys.argv) > 1 and sys.argv[1] == "kubernetes":
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
    kubectl_path, kubectl_url = kubectl_binary_path_and_url(master)
    if kubectl_path is None:
        print("Error: unsupported operating system")
        return 2
    if not os.path.exists(os.path.dirname(kubectl_path)):
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
