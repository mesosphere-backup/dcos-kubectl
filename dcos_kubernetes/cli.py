import sys
import os
import platform
import os.path

import dcos.util
import dcos.constants
from dcos.subcommand import package_dir

BASE_URL="https://github.com/mesosphere/kubernetes-mesos/releases/download/"
KUBECTL_VERSION="v0.5.0"

def kubectl_binary_path_and_url():
    data_dir = package_dir("kubernetes")
    base = os.path.join(data_dir, "kubectl")
    system, node, release, version, machine, processor = platform.uname()

    if system == "Darwin":
        return (base + "_darwin", BASE_URL + KUBECTL_VERSION + "/kubectl-" + KUBECTL_VERSION + "-darwin-amd64.tgz")
    elif system == "Linux":
        return (base + "_linux", BASE_URL + KUBECTL_VERSION + "/kubectl-" + KUBECTL_VERSION + "-linux-amd64.tgz")
    else:
        return (None, None)

def download_kubectl(url, kubectl_path):
    import tarfile

    with dcos.util.temptext() as (fd, tar_file_path):
        try:
            # download tar.gz
            print "Download kubectl from " + url
            from clint.textui import progress
            import requests
            r = requests.get(url, stream=True)
            total_length = int(r.headers.get("content-length"))
            for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1):
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

    # check whether kubectl binary exists and download if not
    kubectl_path, kubectl_url = kubectl_binary_path_and_url()
    if kubectl_path is None:
        print("Error: unsupported operating system")
        return 2
    if not os.path.exists(kubectl_path):
        download_kubectl(kubectl_url, kubectl_path)

    # get api url
    config = dcos.util.get_config()
    docs_url = config.get('core.dcos_url', None)
    if docs_url is None or docs_url == "":
        print("Error: dcos core.dcos_url is not set")
        sys.exit(2)

    # call kubectl with parameters
    from subprocess import call
    import urlparse
    env = os.environ.copy()
    env['KUBERNETES_MASTER'] = urlparse.urljoin(docs_url, "service/kubernetes/api")
    rc = call([kubectl_path] + args, env=env)
    sys.exit(rc)

if __name__ == "__main__":
    os.environ[dcos.constants.DCOS_CONFIG_ENV] = os.path.join(os.getenv("HOME"), dcos.constants.DCOS_DIR, "dcos.toml")
    main()