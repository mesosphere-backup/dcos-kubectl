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
        raise Exception(
            "Cannot download kubectl meta info from {0}".format(meta_url)
        )

    # get url
    system, node, release, version, machine, processor = platform.uname()
    arch = "amd64"  # we only support amd64 for the moment
    key = system.lower() + "-" + arch
    if key not in meta:
        raise Exception("System type {0} not supported".format(key))
    url = master + "/static/" + meta[key]["file"] + ".bz2"
    sha256 = meta[key]["sha256"]

    # create filename
    data_dir = package_dir("kubectl")
    base = os.path.join(data_dir, "kubectl")
    file_path = base + "-" + sha256
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
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        try:
            # download bz2 file and decompress in time
            print("Download kubectl from " + url)
            from clint.textui import progress

            try:
                # For Python 3.0 and later
                from urllib.request import urlopen
            except ImportError:
                # Fall back to Python 2's urllib2
                from urllib2 import urlopen
            f = urlopen(url)

            import bz2
            decompressor = bz2.BZ2Decompressor()
            total_length = int(f.info()["Content-Length"])
            chunk_num = int(total_length/1024) + 1
            chunks = read_in_chunks(f, chunk_size=1024)
            for chunk in progress.bar(chunks, expected_size=chunk_num):
                if chunk:
                    temp_file.write(decompressor.decompress(chunk))

            # move binary at right spot and make executable
            temp_file.file.close()
            import shutil
            shutil.move(temp_file.name, kubectl_path)
            if not kubectl_path.endswith(".exe"):
                os.chmod(kubectl_path, 0o755)

        except tarfile.TarError as e:
            os.unlink(kubectl_path)
            print("Error while opening kubectl tar file: " + str(e))
            sys.exit(2)

        except Exception as e:
            print("Error while downloading kubectl binary: " + str(e))
            sys.exit(2)

        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)


def main():
    # skip "kubectl" command
    if len(sys.argv) > 1 and sys.argv[1] == "kubectl":
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
    try:
        from urlparse import urljoin  # python 2
    except ImportError:
        from urllib.parse import urljoin  # python 3
    master = urljoin(dcos_url, "service/kubernetes")
    try:
        kubectl_path, kubectl_url = kubectl_binary_path_and_url(master)
    except Exception as e:
        print("Error: " + str(e))
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
