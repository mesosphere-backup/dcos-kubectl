import os
import os.path
import platform
import sys

from dcos import constants, util


def kubectl_binary_path_and_url(master, verify=True):
    # get kubectl meta json
    import requests
    meta_url = master + "/static/kubectl-meta.json"
    try:
        meta = requests.get(meta_url, verify=verify).json()
    except:
        raise Exception(
            "Cannot download kubectl meta info from {0}".format(meta_url)
        )

    # get url
    system, _, _, _, _, _ = platform.uname()
    arch = "amd64"  # we only support amd64 for the moment
    key = system.lower() + "-" + arch
    if key not in meta:
        raise Exception("System type {0} not supported".format(key))
    url = master + "/static/" + meta[key]["file"] + ".bz2"
    sha256 = meta[key]["sha256"]

    # create filename
    data_dir = _package_dir("kubectl")
    base = os.path.join(data_dir, "kubectl")
    file_path = base + "-" + sha256
    if system == "Windows":
        file_path += ".exe"

    return file_path, url


def _dcos_dir(path):
    return os.path.expanduser(os.path.join("~", constants.DCOS_DIR, path))


def _subcommand_dir():
    return _dcos_dir(constants.DCOS_SUBCOMMAND_SUBDIR)


def _package_dir(name):
    return os.path.join(_subcommand_dir(), name)


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
            url_file = urlopen(url)

            import bz2
            decompressor = bz2.BZ2Decompressor()
            total_length = int(url_file.info()["Content-Length"])
            chunk_num = int(total_length/1024) + 1
            chunks = read_in_chunks(url_file, chunk_size=1024)
            for chunk in progress.bar(chunks, expected_size=chunk_num):
                if chunk:
                    temp_file.write(decompressor.decompress(chunk))

            # move binary at right spot and make executable
            temp_file.file.close()
            import shutil
            shutil.move(temp_file.name, kubectl_path)
            if not kubectl_path.endswith(".exe"):
                os.chmod(kubectl_path, 0o755)

        except tarfile.TarError as err:
            os.unlink(kubectl_path)
            print("Error while opening kubectl tar file: " + str(err))
            sys.exit(2)

        except Exception as err:
            print("Error while downloading kubectl binary: " + str(err))
            sys.exit(2)

        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "kubectl":
        args = sys.argv[2:]
    else:
        args = sys.argv[1:]

    # special --info case
    if len(args) == 1 and args[0] == "--info":
        print("Deploy and manage pods on Kubernetes")
        sys.exit(0)

    # get api url
    config = util.get_config()
    dcos_url = config.get('core.dcos_url', None)
    if dcos_url is None or dcos_url == "":
        print("Error: dcos core.dcos_url is not set")
        sys.exit(2)

    # check certificates?
    core_verify_ssl = config.get('core.ssl_verify', 'true')
    verify_certs = str(core_verify_ssl).lower() in ['true', 'yes', '1']

    # silence warnings from requests.packages.urllib3.  See DCOS-1007.
    if not verify_certs:
        import requests.packages.urllib3
        requests.packages.urllib3.disable_warnings()

    # check whether kubectl binary exists and download if not
    try:
        from urlparse import urljoin  # python 2
    except ImportError:
        from urllib.parse import urljoin  # python 3
    master = urljoin(dcos_url, "service/kubernetes")
    try:
        kubectl_path, kubectl_url = \
            kubectl_binary_path_and_url(master, verify=verify_certs)
    except Exception as err:
        print("Error: " + str(err))
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

    ret_code = call([
        kubectl_path,
        "--server=" + master,
        "--insecure-skip-tls-verify=" + str(not verify_certs).lower(),
        "--context=dcos-kubectl",  # to nil current context settings
        "--username=dcos-kubectl"  # to avoid username prompt
    ] + args, env=env)
    sys.exit(ret_code)


if __name__ == "__main__":
    cfg = _dcos_dir("dcos.toml")
    os.environ[constants.DCOS_CONFIG_ENV] = cfg
    main()
